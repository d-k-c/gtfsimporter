
import sys

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

        missing_routes = []
        conflator = RouteConflator(gtfs, osm)

        for route in gtfs.routes:
            osm_route = cls.get_osm_route(conflator, route)
            if not osm_route:
                missing_routes.append(route)

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
    def get_osm_route(cls, conflator, gtfs_route):
            matches = conflator.find_matching_osm_routes(gtfs_route)

            if len(matches) > 1:
                print(f"Too many matching routes with same ref, network, operator "
                      f"for ref '{gtfs_route.ref}'")
                return None

            # we've found an exact match, nothing to do
            if len(matches) == 1:
                return matches[0]

            matches = conflator.find_matching_osm_routes(gtfs_route, False, False)
            if matches:
                return cls.prompt_disambiguate_routes(gtfs_route.name, matches)
            else:
                return None


    @classmethod
    def prompt_disambiguate_routes(cls, route_name, osm_routes):
        print("")
        print(f"Several matching routes have been found that could match '{route_name}': ")

        while True:
            for i, r in enumerate(osm_routes, start=1):
                print(f"{i}) ref: {r.ref}, name: {r.name}, "
                      f"operator: {r.operator}, network: {r.network}")
            i += 1
            print(f"{i}) None of the above")

            try:
                index = int(input("Enter route number: "))
                index -= 1
                if index == len(osm_routes):
                    return None
                else:
                    route = osm_routes[index - 1]
                    return route
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
            except:
                pass


    @classmethod
    def update_routes(cls, args):
        gtfs, osm = SchedulesLoader.load_from_args(args)

        conflator = RouteConflator(gtfs, osm)

        modified_routes = []
        refs = args.route_ref.split(",")

        for gtfs_route in gtfs.routes:
            if gtfs_route.ref not in refs:
                continue

            refs.remove(gtfs_route.ref)

            osm_route = cls.get_osm_route(conflator, gtfs_route)
            if not osm_route:
                print(f"Route with '{gtfs_route.ref}' not found in OSM")
                continue

            try:
                osm_route.merge_gtfs(gtfs_route, osm)
            except Exception as e:
                print(f"Route '{gtfs_route.ref}' update failed: {e}")
                continue

            # check if the route or trips were modified
            if osm_route.modified or any([t.modified for t in osm_route.trips]):
                modified_routes.append(osm_route)
                print(f"Route '{gtfs_route.ref}' updated")
            else:
                print(f"Route '{gtfs_route.ref} was not modified', skipping update")

        for ref in refs:
            print(f"Route '{ref}' does not match any route in GTFS dataset")

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
