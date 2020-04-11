
from .loader import GtfsLoader, SchedulesLoader

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
