
import os
import sys
import argparse

from .osm.elements import Schedule

from .osm.josm import JosmDocument
from .gtfs.importer import GTFSImporter
from .overpass.importer import OsmImporter
from .validator.validator import StopValidator
from .validator.issue import IssueList

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
    loader = OsmImporter(bbox)
    xml = None
    if osm_cache:
        xml = osm_cache.read()

    schedule = loader.load(xml)

    return schedule

def test_osm(args):
    schedule = load_osm(args.osm_cache, ())

    for route in schedule.routes:
        print(route.name)
        for trip in route.trips:
            none_stops = [stop for stop in trip.stops.values() if stop.stop is None]
            print("\t", trip.headsign, "Stops:", len(trip), len(none_stops))

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
    doc.export_route(route, osm.stops)
    doc.write(args.dest)

def export_stops(args):
    if args.gtfs_datadir is None:
        print("Directory with GTFS files must be specified")
        return

    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    if args.only_missing:
        bbox = gtfs.get_bounding_box(1000)
        loader = OsmImporter(bbox)
        xml = None
        if args.osm_cache:
            xml = args.osm_cache.read()

        osm = Schedule()
        loader.load_stops(osm, xml)

        osm_refs = []
        for stop in osm.stops:
            osm_refs.extend(stop.refs)

        export_stops = []
        for stop in gtfs.stops:
            assert len(stop.refs) == 1
            ref = stop.refs[0]

            if ref not in osm_refs:
                export_stops.append(stop)
    else:
        export_stops = gtfs.stops

    doc = JosmDocument()
    doc.export_stops(export_stops)
    doc.write(args.dest)

def inspect_stops(args):
    if args.gtfs_datadir is None:
        print("Directory with GTFS files must be specified")
        return

    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    bbox = gtfs.get_bounding_box(1000)
    loader = OsmImporter(bbox)
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

def generate_cache(args):
    gtfs = Schedule()
    loader = GTFSImporter(args.gtfs_datadir)
    loader.load_stops(gtfs)

    bbox = gtfs.get_bounding_box(1000)
    loader = OsmImporter(bbox)
    loader.generate_cache(args.output_file)


def parse_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gtfs-datadir",
        help="directory containing GTFS files")
    parser.add_argument(
        "--osm-cache",
        help="XML file containing query result. If omitted, an overpass " \
             "query will be issued to fetch results",
        type=argparse.FileType())
    subparsers = parser.add_subparsers(dest="command")

    export_route_parser = subparsers.add_parser(
        "export-route",
        help="export compete route in JOSM format")
    export_route_parser.add_argument(
        "--with-shapes",
        action="store_true",
        help="export route shapes")
    export_route_parser.add_argument(
        "--dest",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="Output file")
    export_route_parser.add_argument(
        "route_id",
        metavar="route-id",
        help="identifier of the route in the GTFS routes.txt file")
    export_route_parser.set_defaults(func=export_route)

    export_stops_parser = subparsers.add_parser(
        "export-stops",
        help="export all stops from GTFS in JOSM format")
    export_stops_parser.add_argument(
        "--only-missing",
        action="store_true",
        help="export only nodes missing in OSM")
    export_stops_parser.add_argument(
        "--dest",
        type=argparse.FileType('w'),
        default=sys.stdout,
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

    generate_cache_parser = subparsers.add_parser(
        "generate-cache",
        help="generate stops cache to minimize requests to overpass API")
    generate_cache_parser.add_argument(
        "output_file",
        metavar="output-file",
        help="Cache file")
    generate_cache_parser.set_defaults(func=generate_cache)

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

