
from itertools import zip_longest

class RouteConflator(object):

    def __init__(self, gtfs_schedule, osm_schedule):
        self.gtfs = gtfs_schedule
        self.osm = osm_schedule


    def only_in_gtfs(self):
        """
        Return routes that exist only in the GTFS schedule. Route match is
        based on "ref", "operator", and "network" tags.
        """
        route_details = {}
        for route in self.gtfs.routes:
            route_details[(route.ref, route.network, route.operator)] = route

        for route in self.osm.routes:
            route_details.pop((route.ref, route.network, route.operator), None)

        return route_details.values()


    def get_routes_by_ref(self, ref, match_network=True, match_operator=True):

        gtfs_route = osm_route = None

        for route in self.gtfs.routes:
            if route.ref == ref:
                gtfs_route = route
                break
        else:
            return gtfs_route, osm_route

        for route in self.osm.routes:
            if route.ref != ref:
                continue
            if match_network and route.network != gtfs_route.network:
                continue
            if match_operator and route.operator != gtfs_route.operator:
                continue

            osm_route = route

        return gtfs_route, osm_route


    def find_matching_osm_routes(self, gtfs_route,
                                 match_network=True, match_operator=True):
        matches = []
        for route in self.osm.routes:
            if route.ref != gtfs_route.ref:
                continue
            if match_network and route.network != gtfs_route.network:
                continue
            if match_operator and route.operator != gtfs_route.operator:
                continue

            matches.append(route)

        return matches

    def get_route_in_schedule(self, schedule, route_code):
        # FIXME: should be a schedule.get_route_by_code() function
        for route in schedule.routes:
            if route.code == route_code:
                return route

    def compare_trip_stops(self, gtfs_trip, osm_trip):
        gtfs_stop_refs = [stop.ref for stop in gtfs_trip.stops]
        osm_stop_refs  = [stop.ref for stop in osm_trip.stops]

        if gtfs_stop_refs == osm_stop_refs:
            print("Identical")
        else:
            print(f"Updating trip {osm_trip.name}")
            try:
                osm_trip.merge_gtfs(gtfs_trip, self.osm)
                print("Trip updated")
            except Exception as e:
                print(e)



    def compare_route_trips(self, gtfs_route, osm_route):
        for osm_trip in osm_route.trips:
            gtfs_trip = gtfs_route.get_trip_by_name(osm_trip.ref)
            if gtfs_trip is None:
                print("Could not find matching trip for", osm_trip.ref)
            else:
                print("Found matching trip for", osm_trip.ref)
                self.compare_trip_stops(gtfs_trip, osm_trip)


    def conflate_existing_routes(self):
        osm_routes_code  = set([route.code for route in self.osm.routes])
        gtfs_routes_code = set([route.code for route in self.gtfs.routes])

        for code in osm_routes_code & gtfs_routes_code:
            osm_route  = self.get_route_in_schedule(self.osm, code)
            gtfs_route = self.get_route_in_schedule(self.gtfs, code)

            if not osm_route.operator == gtfs_route.operator:
                continue

            if osm_route.name != gtfs_route.name:
                print(osm_route.name, "====", gtfs_route.get_name())
                osm_route.merge_tags(gtfs_route)
            #    self.compare_route_trips(gtfs_route, osm_route)
            #else:
            #    print("Identical names found for", osm_route.name)
            #    self.compare_route_trips(gtfs_route, osm_route)

    def conflate(self, gtfs_schedule, osm_schedule):
        self.gtfs_by_ref = {}
        self.osm_by_ref = {}
        self.osm_without_ref = []

        self.populate_by_ref(self.gtfs_by_ref, gtfs_stops)
        self.populate_by_ref(self.osm_by_ref,
                             osm_stops,
                             self.osm_without_ref)

        modified_stops = self.compare_names_by_ref(self.gtfs_by_ref, self.osm_by_ref)

        return modified_stops

    def compare_names_by_ref(self, gtfs_by_ref, osm_by_ref):
        modified_stops = []

        # iterate over all items in GTFS stops
        for ref, gtfs_stop in gtfs_by_ref.items():

            # if this ref exists in existing OSM dataset
            # check both name are the same, otherwise do an update
            if ref in osm_by_ref:
                osm_stop = osm_by_ref[ref]
                if gtfs_stop.name != osm_stop.name:
                    osm_stop.name = gtfs_stop.name
                    modified_stops.append(osm_stop)

        return modified_stops

    def populate_by_ref(self, dic, stop_list, lst=None):
        for stop in stop_list:
            if not stop.refs and lst:
                lst.append(stop)

            for ref in stop.refs:
                dic[ref] = stop

    def get_common_refs(self):
        osm_refs = set(self.osm_by_ref.keys())
        gtfs_refs = set(self.gtfs_by_ref.keys())

        return osm_refs & gtfs_refs

    def validate(self):
        self.find_inconsistent_refs()
        self.check_distance()

    def check_distance(self, max_distance=50):
        max_distance = max_distance / 1000
        for ref in self.get_common_refs():
            osm_stop = self.osm_by_ref[ref]
            gtfs_stop = self.gtfs_by_ref[ref]

            dist = haversine((osm_stop.lat, osm_stop.lon),
                             (gtfs_stop.lat, gtfs_stop.lon))

            if dist >= max_distance:
                issue = NodesTooFarIssue(osm_stop, gtfs_stop, dist * 1000)
                self.issues.append(issue)

    def find_inconsistent_refs(self):
        gtfs = set(self.gtfs_by_ref.keys())
        osm = set(self.osm_by_ref.keys())

        missing_stops = gtfs - osm
        for stop_ref in missing_stops:
            issue = OsmStopMissingIssue(self.gtfs_by_ref[stop_ref])
            self.issues.append(issue)

        #for stop_ref in osm - gtfs:
        #    issue = OsmStopWithUnknownRefIssue(self.osm_by_ref[stop_ref])
        #    self.issues.append(issue)
