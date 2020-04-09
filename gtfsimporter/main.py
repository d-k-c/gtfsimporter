
import os
import sys
import argparse
import pickle

from .elements import Schedule

from .osm.elements import OsmStop
from .osm.josm import JosmDocument
from .gtfs.importer import GTFSImporter
from .osm.overpass import OverpassImporter
from .conflation.routes import RouteConflator
from .conflation.stops import StopConflator
from .validator.validator import StopValidator
from .validator.issue import IssueList

from .cli.cache import CacheParser
from .cli.stop import StopParser

def load_gtfs(datadir, route_ids, unique_trips=True, shapes=False):
    if datadir is None:
        print("Directory with GTFS files must be specified")
        return

    loader = GTFSImporter(datadir)
    schedule = loader.load(route_ids, unique_trips=unique_trips,
                           shapes=shapes)
    schedule.remove_truncated_trips()

    return schedule

def load_osm(osm_cache, bbox):
    loader = OverpassImporter(bbox)
    xml = None
    if osm_cache:
        xml = osm_cache.read()

    osm = Schedule()
    loader.load_routes(osm, xml)

    return osm

def test_osm(args):
    schedule = load_osm(args.osm_cache, ())

    for route in schedule.routes:
        if route.code != "747":
            continue

        print(len(route.trips), route.name)
        for trip in route.trips:
            print("\t", trip.headsign, "Stops:", len(trip))
            for stop in trip.stops:
                print("\t\t", stop.name)

def export_route(args):
    route_ids = (args.route_id, )
    gtfs = load_gtfs(args.gtfs_datadir, route_ids,
                     shapes=args.with_shapes)

    # Get the bounding box. This is used only if an actual
    # query to Overpass is made
    bbox = gtfs.get_bounding_box(1000)

    osm = load_osm(args.osm_cache, bbox)

    route = gtfs.get_route(args.route_id)

    doc = JosmDocument()
    if doc.export_route(route, osm.stops):
        with open(args.dest, 'w') as output_file:
            doc.write(output_file)

def export_routes(args):
    gtfs = load_gtfs(args.gtfs_datadir, None,
                     shapes=args.with_shapes)

    # Get the bounding box. This is used only if an actual
    # query to Overpass is made
    bbox = gtfs.get_bounding_box(1000)

    osm = load_osm(args.osm_cache, bbox)

    doc = JosmDocument()
    if doc.export_routes(gtfs.routes, osm.stops):
        with open(args.dest, 'wb') as output_file:
            doc.write(output_file)

def export_stops(args):
    if args.gtfs_datadir is None:
        print("Directory with GTFS files must be specified")
        return

    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    if args.only_missing:
        bbox = gtfs.get_bounding_box(1000)
        loader = OverpassImporter(bbox)
        xml = None
        if args.osm_cache:
            xml = args.osm_cache.read()

        osm = Schedule()
        loader.load_stops(osm, xml)

        conflator = StopConflator(gtfs.stops, osm.stops) 
        #export_stops = conflator.conflate(gtfs.stops, osm.stops)
        #keep_attributes = True

        gtfs_only_stops = conflator.missing_stops_in_osm()
        if any([len(stop.refs) > 1 for stop in gtfs_only_stops]):
            print("Ouaile")
        export_stops = [OsmStop.fromGtfs(s) for s in gtfs_only_stops]
        keep_attributes = None


        #osm_refs = []
        #for stop in osm.stops:
        #    osm_refs.extend(stop.refs)

        #export_stops = []
        #for stop in gtfs.stops:
        #    assert len(stop.refs) == 1
        #    ref = stop.refs[0]

        #    if ref not in osm_refs:
        #        export_stops.append(stop)
    else:
        keep_attributes = False
        export_stops = gtfs.stops

    doc = JosmDocument()
    doc.export_stops(export_stops, keep_attributes)
    with open(args.dest, 'w', encoding="utf-8") as output_file:
        doc.write(output_file)

def inspect_stops(args):
    if args.gtfs_datadir is None:
        print("Directory with GTFS files must be specified")
        return

    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    bbox = gtfs.get_bounding_box(1000)
    loader = OverpassImporter(bbox)
    xml = None
    if args.osm_cache:
        xml = args.osm_cache.read()

    osm = Schedule()
    loader.load_stops(osm, xml)

    issues = IssueList()
    validator = StopValidator(issues, gtfs.stops, osm.stops)
    validator.validate()

    issues.extend(gtfs.issues)
    issues.extend(osm.issues)

    issues.print_report()

def generate_cache_stops(args):
    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    bbox = gtfs.get_bounding_box(1000)
    loader = OverpassImporter(bbox)
    loader.generate_cache_stops(args.output_file)


def generate_cache_routes(args):

    gtfs_schedule = load_gtfs(args.gtfs_datadir, None, shapes=False)

    with open(args.gtfs_cache, 'wb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        pickle.dump(gtfs_schedule, f, pickle.HIGHEST_PROTOCOL)

    bbox = gtfs_schedule.get_bounding_box(1000)
    loader = OverpassImporter(bbox)
    loader.generate_cache_routes(args.osm_cache)

def route_export(args):
    with open(args.gtfs_cache, 'rb') as f:
        gtfs_schedule = pickle.load(f)

    osm_schedule = load_osm(args.osm_cache, ())

    conflator = RouteConflator(gtfs_schedule, osm_schedule)
    conflator.conflate_existing_routes()

    modified_routes = []

    for route in osm_schedule.routes:
        if route.modified:
            modified_routes.append(route)
            continue

        for trip in route.trips:
            if trip.modified:
                modified_routes.append(route)

    output = JosmDocument() 
    output.export_routes(modified_routes, osm_schedule.stops)

    with open("/tmp/foobar.osm", "w") as fil:
        output.write(fil)

def conflate_routes(args):
    successfully_unpickled = False
    if args.pickled_gtfs is not None:
        try:
            print("Unpickling stored data in", args.pickled_gtfs)
            with open(args.pickled_gtfs, 'rb') as f:
                gtfs = pickle.load(f)
                successfully_unpickled = True
        except FileNotFoundError as e:
            pass
        except Exception as e:
            print(e)
            import traceback
            traceback.print_tb(e.__traceback__)

    print("Successfully unpickled?", successfully_unpickled)

    if not successfully_unpickled:
        gtfs = load_gtfs(args.gtfs_datadir, None, shapes=False)

        if args.pickled_gtfs is not None:
            with open(args.pickled_gtfs, 'wb') as f:
                # Pickle the 'data' dictionary using the highest protocol available.
                pickle.dump(gtfs, f, pickle.HIGHEST_PROTOCOL)


    for route in gtfs.routes:
        if route.code != "747":
            continue

        print(len(route.trips), route.name)

        for trip in route.trips:
            print("\t", trip.headsign, "Stops:", len(trip))
            for stop in trip.stops:
                print("\t\t", stop.name)

    #bbox = gtfs.get_bounding_box(1000)
    #loader = OverpassImporter(bbox)
    #loader.load_routes(args.output_file)


def parse_command_line():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    CacheParser.setup_arguments(parser, subparsers)
    StopParser.setup_arguments(parser, subparsers)

    # --gtfs-datadir common option
    #gtfs_datadir_parser = argparse.ArgumentParser(add_help=False)
    #gtfs_datadir_parser.add_argument(
    #        "--gtfs-datadir",
    #        help="Directory containing extracted GTFS files")

    export_route_parser = subparsers.add_parser(
        "export-route",
        help="export compete route in JOSM format")
    export_route_parser.add_argument(
        "--with-shapes",
        action="store_true",
        help="export route shapes")
    export_route_parser.add_argument(
        "--dest",
        help="Output file")
    export_route_parser.add_argument(
        "route_id",
        metavar="route-id",
        help="identifier of the route in the GTFS routes.txt file")
    export_route_parser.set_defaults(func=export_route)

    export_routes_parser = subparsers.add_parser(
        "export-routes",
        help="export all routes in JOSM format")
    export_routes_parser.add_argument(
        "--with-shapes",
        action="store_true",
        help="export route shapes")
    export_routes_parser.add_argument(
        "--dest",
        help="Output file")
    export_routes_parser.set_defaults(func=export_routes)

    export_stops_parser = subparsers.add_parser(
        "export-stops",
        help="export all stops from GTFS in JOSM format")
    export_stops_parser.add_argument(
        "--only-missing",
        action="store_true",
        help="export only nodes missing in OSM")
    export_stops_parser.add_argument(
        "--dest",
        help="Output file")
    export_stops_parser.set_defaults(func=export_stops)

    inspect_stops_parser = subparsers.add_parser(
        "inspect-stops",
        help="inspect stops to find incoherences between GTFS and OSM")
    inspect_stops_parser.set_defaults(func=inspect_stops)

    test_osm_parser = subparsers.add_parser(
        "load-osm",
        help="Just load OSM")
    test_osm_parser.set_defaults(func=test_osm)

    #generate_cache_parser = subparsers.add_parser(
    #    "generate-cache",
    #    help="generate stops cache to minimize requests to overpass API")
    #generate_cache_parser.add_argument(
    #    "output_file",
    #    metavar="output-file",
    #    help="Cache file")
    #generate_cache_parser.set_defaults(func=generate_cache_stops)

    generate_cache_route_parser = subparsers.add_parser(
        "generate-cache-routes",
        help="generate routes cache to minimize requests to overpass API")
    generate_cache_route_parser.add_argument(
        "output_file",
        metavar="output-file",
        help="Cache file")
    generate_cache_route_parser.set_defaults(func=generate_cache_routes)

    conflate_routes_parser = subparsers.add_parser(
        "conflate-routes",
        help="placeholder to test route laoding")
    conflate_routes_parser.add_argument(
        "--pickled-gtfs",
        help="Pickled GTFS schedule file to fasten the process")
    conflate_routes_parser.set_defaults(func=conflate_routes)

    # routes
    routes_parser = subparsers.add_parser(
        "routes",
        help="submenu for route-related commands")
    routes_subparsers = routes_parser.add_subparsers(dest="subcommand")

    # route generate-cache
    generate_cache_parser = routes_subparsers.add_parser(
        "generate-cache",
        help="Generate cache for GTFS and OSM data, to accelerate next runs")
    generate_cache_parser.add_argument(
        "gtfs_cache", metavar="gtfs-cache",
        help="file to store GTFS cache (pickle)")
    generate_cache_parser.add_argument(
        "osm_cache", metavar="osm-cache",
        help="file to store OSM cache (XML file)")
    generate_cache_parser.set_defaults(func=generate_cache_routes)

    # route export
    route_export_parser = routes_subparsers.add_parser(
        "export",
        help="Export routes")
    route_export_parser.add_argument(
        "--gtfs-cache",
        help="Path to GTFS cache file",
        required=True)
    group = route_export_parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        help="Export all routes from GTFS dataset",
        action='store_true')
    group.add_argument(
        "--missing",
        help="Compare OSM and GTFS dataset to export only missing routes",
        action='store_true')
    group.set_defaults(func=route_export)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

parse_command_line()
sys.exit(0)

#for issue in issues:
#    print(issue.report())
#pprint(validator.find_nodes_with_missing_attributes())

#for route in schedule.routes:
#    if len(route.trips) != 2:
#        for trip in route.trips:
#            print(route.name, trip.headsign, len(trip.stops))
#
#        print(route.name, trip.headsign, len(trip.stops))
#        for stop in trip.get_ordered_stops():
#            print("\t", stop.name)
#

