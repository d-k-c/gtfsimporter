
from collections import defaultdict

from math import cos, pi

class Schedule(object):

    def __init__(self):
        self.issues = []
        self._stops_by_id = {}
        self._stops = []
        self._routes_dict = {}
        self._trips_dict = {}
        self._shapes_dict = defaultdict(list)

    @property
    def routes(self):
        return self._routes_dict.values()

    @property
    def stops(self):
        return self._stops

    @property
    def trips(self):
        return self._trips_dict.values()

    def get_bounding_box(self, margin=None):
        bbox = (min(self.stops, key=lambda s: s.lat).lat,
                min(self.stops, key=lambda s: s.lon).lon,
                max(self.stops, key=lambda s: s.lat).lat,
                max(self.stops, key=lambda s: s.lon).lon)

        if margin is not None:
            margin_lat = margin * (360 / 40075000)
            len_longitude = cos(bbox[0] * pi / 180) * 40075000
            margin_lon = margin * (360 / len_longitude)
            bbox = (float("{0:.6f}".format(bbox[0] - margin_lat)),
                    float("{0:.6f}".format(bbox[1] - margin_lon)),
                    float("{0:.6f}".format(bbox[2] + margin_lat)),
                    float("{0:.6f}".format(bbox[3] + margin_lon)))

        return bbox

    def add_route(self, route):
        self._routes_dict[route.id] = route

    def find_duplicate_stop(self, stop):
        """
        Return stop if it already exists

        Search for a stop with the same property in the already-found stop list.
        Some dataset providers duplicate the stops for each line they are served
        by.
        """
        for s in self.stops:
            if s.lat == stop.lat and s.lon == stop.lon:
                if s.name != stop.name:
                    print("WARNING: These stops have the same coordinates "
                          "but not the same name. Name of the first one will be used.")
                    print(f"\tid={s.id}, refs={s.refs}, name={s.name}")
                    print(f"\tid={stop.id}, refs={stop.refs}, name={stop.name}")
                    print("")

                return s

    def add_stop(self, stop, deduplicate=False):
        existing_stop = None
        if deduplicate:
            existing_stop = self.find_duplicate_stop(stop)

        if existing_stop:
            self._stops_by_id[stop.id] = existing_stop
            if stop.ref not in existing_stop.refs:
                existing_stop.add_ref(stop.ref)
                #print(existing_stop.refs)
        else:
            self._stops.append(stop)
            self._stops_by_id[stop.id] = stop

    def add_trip(self, trip):
        self._trips_dict[trip.id] = trip
        self._shapes_dict[trip.shape_id].append(trip.id)

    def add_shape_point(self, shape_id, lat, lon, seq):
        for trip_id in self._shapes_dict[shape_id]:
            trip = self.get_trip(trip_id)
            trip.way.add_node(lat, lon, seq)

    def get_stop_by_ref(self, stop_ref):
        for stop in self.stops:
            if stop_ref in stop.refs:
                return stop

    def get_route(self, route_id, *args):
        if args:
            default = args[0]
            return self._routes_dict.get(route_id, default)
        else:
            return self._routes_dict[route_id]

    def get_stop(self, stop_id, *args):
        if args:
            default = args[0]
            return self._stops_by_id.get(stop_id, default)
        else:
            return self._stops_by_id[stop_id]


    def get_trip(self, trip_id, *args):
        if args:
            default = args[0]
            return self._trips_dict.get(trip_id, default)
        else:
            return self._trips_dict[trip_id]

    def drop_trips(self, trip_ids):
        for trip_id in trip_ids:
            del self._trips_dict[trip_id]

        for shape_id in self._shapes_dict:
            lst = self._shapes_dict[shape_id]
            lst = [trip_id for trip_id in lst if trip_id not in trip_ids]
            self._shapes_dict[shape_id] = lst

    def remove_duplicated_trips(self):
        removed = 0
        total = len(self.routes)
        print(f"Removing duplicated trips of {total} routes")

        for i, route in enumerate(self.routes, start=1):
            trip_ids = route.remove_duplicated_trips()
            removed += len(trip_ids)
            self.drop_trips(trip_ids)

            print(f"Removing... {i}/{total}")

        return removed

    def remove_truncated_trips(self):
        removed = 0
        for route in self.routes:
            trip_ids = route.remove_truncated_trips()
            removed += len(trip_ids)
            self.drop_trips(trip_ids)

        return removed

    def add_stop_time(self, trip, stop_time):
        trip.add_stop_time(stop_time)
