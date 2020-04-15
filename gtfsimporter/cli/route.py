
from .loader import GtfsLoader, SchedulesLoader

from ..conflation.routes import RouteConflator
from ..osm.elements import OsmRoute
from ..osm.josm import JosmDocument

class RouteParser(object):

    @classmethod
    def generate_routes(cls, args):
        gtfs, osm = SchedulesLoader.load_from_args(args)

        if args.route_ref is None:
            selected_routes = gtfs.routes
        else:
            wanted_refs = args.route_ref.split(",")
            selected_routes = [r for r in gtfs.routes if r.ref in wanted_refs]

        cls.__export_gtfs_routes(selected_routes, osm, args.output_file)


    @classmethod
    def generate_missing_routes(cls, args):
        gtfs, osm = SchedulesLoader.load_from_args(args)

        conflator = RouteConflator(gtfs, osm)
        missing_routes = conflator.only_in_gtfs()

        cls.__export_gtfs_routes(missing_routes, osm, args.output_file)


    @classmethod
    def __export_gtfs_routes(cls, gtfs_routes, osm_schedule, out_file):
        osm_routes = []

        for route in gtfs_routes:
            try:
                osm_route = OsmRoute.fromGtfs(route, osm_schedule)
                osm_routes.append(osm_route)
            except Exception as e:
                print(f"Unable to generate route {route.ref}: {e}")

        doc = JosmDocument()
        doc.export_routes(osm_routes)
        with open(out_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)


    @classmethod
    def update_routes(cls, args):
        gtfs, osm = SchedulesLoader.load_from_args(args)

        conflator = RouteConflator(gtfs, osm)

        modified_routes = []
        refs = args.route_ref.split(",")
        for ref in refs:
            g_route, o_route = conflator.get_routes_by_ref(ref)
            if not g_route or not o_route:
                print(f"Route '{ref}' could not be found")
                continue

            try:
                o_route.merge_gtfs(g_route, osm)
            except Exception as e:
                print(f"Route '{ref}' update failed: {e}")
                continue

            # check if the route or trips were modified
            if o_route.modified or any([t.modified for t in o_route.trips]):
                modified_routes.append(o_route)
                print(f"Route '{ref}' updated")
            else:
                print(f"Route '{ref} was not modified', skipping update")

        # avoid creating an empty file
        if not modified_routes:
            return

        doc = JosmDocument()
        doc.export_routes(modified_routes)
        with open(args.output_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)

    @classmethod
    def setup_arguments(cls, parser, subparsers):

        route_parser = subparsers.add_parser(
            "routes",
            help="route-related submenu")

        route_subparsers = route_parser.add_subparsers()

        # COMMAND: route export
        route_export_parser = route_subparsers.add_parser(
            "export",
            help="Export routes from the GTFS dataset. Stops must already be in OSM")
        route_export_parser.add_argument(
            "--route-ref",
            help="List of route references to export, comma-separated "
                 ", eg. --route-ref 1234,5789")
        route_export_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated routes")

        SchedulesLoader.setup_arguments(route_export_parser, subparsers)
        route_export_parser.set_defaults(func=RouteParser.generate_routes)

        # COMMAND: route export-missing
        route_missing_parser = route_subparsers.add_parser(
            "export-missing",
            help="Export routes missing in OSM")
        route_missing_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated routes")

        SchedulesLoader.setup_arguments(route_missing_parser, subparsers)
        route_missing_parser.set_defaults(func=RouteParser.generate_missing_routes)

        # COMMAND: route update
        route_update_parser = route_subparsers.add_parser(
            "update",
            help="Update existing OSM route")
        route_update_parser.add_argument(
            "--route-ref",
            required=True,
            help="List of route references to update, comma-separated "
                 ", eg. --route-ref 1234,5789")
        route_update_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated routes")

        SchedulesLoader.setup_arguments(route_update_parser, subparsers)
        route_update_parser.set_defaults(func=RouteParser.update_routes)
