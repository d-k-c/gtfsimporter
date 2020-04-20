
import sys

from .loader import GtfsLoader, SchedulesLoader

from ..conflation.routes import RouteConflator
from ..osm.elements import OsmRoute, OsmStop, RefMissingInOsmError
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

        cls.__export_gtfs_routes(selected_routes, osm, None, args.output_file)


    @classmethod
    def generate_missing_routes(cls, args):
        gtfs, osm = SchedulesLoader.load_from_args(args)

        missing_routes = []
        conflator = RouteConflator(gtfs, osm)

        for route in gtfs.routes:
            try:
                osm_route = cls.get_osm_route(conflator, route)
                if not osm_route:
                    missing_routes.append(route)
            except Exception as e:
                print(f"Error when looking for OSM route {route.ref}: {e}")
                continue

        for route in missing_routes:
            print(f"Exporting route '{route.ref}'")
        cls.__export_gtfs_routes(missing_routes, osm, None, args.output_file)

    @classmethod
    def create_stop_by_ref(cls, gtfs_schedule, ref):
        gtfs_stop = gtfs_schedule.get_stop_by_ref(ref)
        if not gtfs_stop:
            raise AttributeError(f"GTFS Schedule doesn't have stop with ref='{ref}'")

        if len(gtfs_stop.refs) != 1:
            raise AttributeError("GTFS stop has too many refs: {gtfs_stop.refs}")

        return OsmStop.fromGtfs(gtfs_stop)


    @classmethod
    def create_or_merge_gtfs_route(cls, gtfs_route, osm_schedule,
                                   osm_route=None, gtfs_schedule=None):
        """
        Create or merge a GTFS route, looking for OSM stops in the given
        osm_schedule.

        If osm_route is None, a new route will be created.
        If gtfs_schedule is None, route creation will fail if stops don't
        already exist in OSM schedule. If it is not None, attempt to create
        stop.
        """

        create_new_route = osm_route is None
        new_stops = []

        while True:
            try:
                if create_new_route:
                    osm_route = OsmRoute.fromGtfs(gtfs_route, osm_schedule)
                else:
                    osm_route.merge_gtfs(gtfs_route, osm_schedule)

                return osm_route, new_stops
            except RefMissingInOsmError as e:
                if not gtfs_schedule:
                    raise e

                new_osm_stop = cls.create_stop_by_ref(gtfs_schedule, e.ref)
                osm_schedule.add_stop(new_osm_stop)
                new_stops.append(new_osm_stop)

    @classmethod
    def create_gtfs_route(cls, gtfs_route, osm_schedule, gtfs_schedule=None):
        return cls.create_or_merge_gtfs_route(
                    gtfs_route, osm_schedule, None, gtfs_schedule)

    @classmethod
    def merge_gtfs_route(cls, gtfs_route, osm_route, osm_schedule, gtfs_schedule=None):
        _, new_stops = cls.create_or_merge_gtfs_route(
                    gtfs_route, osm_schedule, osm_route, gtfs_schedule)

        return new_stops

    @classmethod
    def __export_gtfs_routes(cls, gtfs_routes, osm_schedule, gtfs_schedule, out_file):
        osm_routes = []
        new_osm_stops = []

        for route in gtfs_routes:
            try:
                osm_route, route_stops = cls.create_gtfs_route(
                        route, osm_schedule, gtfs_schedule)
                osm_routes.append(osm_route)
                new_osm_stops.extend(route_stops)
            except Exception as e:
                print(f"Unable to generate route {route.ref}: {e}")

        doc = JosmDocument()
        doc.export_stops(new_osm_stops)
        doc.export_routes(osm_routes)
        with open(out_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)


    @classmethod
    def get_osm_route(cls, conflator, gtfs_route):
            matches = conflator.find_matching_osm_routes(gtfs_route)

            assert len(matches) <= 1, \
                f"Too many matching routes with same ref, network, operator " \
                f"in OSM for ref '{gtfs_route.ref}'"

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

            try:
                osm_route = cls.get_osm_route(conflator, gtfs_route)
                if not osm_route:
                    print(f"Route with '{gtfs_route.ref}' not found in OSM")
                    continue
            except Exception as e:
                print(f"Error when looking for OSM route {gtfs_route.ref}: {e}")
                continue

            try:
                cls.merge_gtfs_route(gtfs_route, osm_route, osm)
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
