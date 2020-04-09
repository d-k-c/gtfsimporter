
from collections import defaultdict

from math import cos, pi

class GtfsElement(object):

    extra_tags = []

    def __init__(self, element_id):
        self.id = element_id

class GtfsNode(GtfsElement):

    def __init__(self, node_id, lat, lon):
        super().__init__(node_id)
        self.lat = float(lat)
        self.lon = float(lon)


class WayUnordered(object):

    def __init__(self):
        self.nodes = {}

    def add_node(self, lat, lon, seq):
        self.nodes[seq] = (lat, lon)

    def get_ordered_nodes(self):
        for seq in sorted(self.nodes.keys()):
            yield self.nodes[seq]

    def __len__(self):
        return len(self.nodes)


class GtfsStopTime(object):

    def __init__(self, trip_id, stop_id, sequence):
        self.trip_id = trip_id
        self.stop_id = stop_id
        self.sequence = sequence

    def set_stop(self, stop):
        self.stop = stop

    def __eq__(self, other):
        return self.stop == other.stop and \
               self.sequence == other.sequence

class GtfsStop(GtfsNode):

    extra_locales = []

    def __init__(self, stop_id, lat, lon, name, ref):
        super().__init__(stop_id, lat, lon)
        self.name = name
        self.ref = ref
        self.refs = [ref, ]
    
    def add_ref(self, ref):
        self.refs.append(ref)

    def __repr__(self):
        return "<Stop id={}, refs={}, name={}, coord=[{}, {}]>".format(
                self.id, self.refs, self.name, self.lon, self.lat)


class GtfsTrip(GtfsElement):

    def __init__(self, trip_id, route_id, headsign, network=None, operator=None, shape_id=None):
        super().__init__(trip_id)
        self.headsign = headsign
        self.route_id = route_id
        self.network = network
        self.operator = operator

        self.from_stop = None
        self.to_stop = None

        self._stops_dict = {}

        # _stops is generated on demand when the 'stops' property is accessed,
        # based on the content of _stops_dict
        self._stops = []
        self._stops_list_generated = False

        self.way = WayUnordered()
        self.shape_id = shape_id

    @property
    def name(self):
        raise NotImplementedError("GtfsTrip-subclass must implement this")

    @property
    def ref(self):
        return self.headsign

    @property
    def stops(self):
        if not self._stops_list_generated:
            self._stops = [self._stops_dict[seq] for seq in sorted(self._stops_dict.keys())]
            self._stops_list_generated = True

        return self._stops

    def __len__(self):
        return len(self._stops_dict)

    def set_route(self, route):
        self.route = route
        if not self.network:
            self.network = route.network
        if not self.operator:
            self.operator = route.operator

    def add_stop(self, sequence, stop):
        self._stops_dict[sequence] = stop
        self._stops_list_generated = False

    def is_similar(self, other):
        if self.route != other.route or self.ref != other.ref:
            return False
        if len(self.stops) != len(other.stops):
            return False

        for self_stop, other_stop in zip(self.stops, other.stops):
            if self_stop != other_stop:
                return False
        else:
            return True

    def __repr__(self):
        return "<Trip id={}, name={}, {} stops>".format(self.id, self.ref, len(self._stops))


class GtfsRoute(GtfsElement):

    def __init__(self, route_id, code, name, network=None, operator=None):
        super().__init__(route_id)
        self.ref = code
        self._name = name
        self.network = network
        self.operator = operator
        self.trips = []

    @property
    def name(self):
        raise NotImplementedError("GtfsTrip-subclass must implement this")

    @property
    def code(self):
        return self.ref

    def add_trip(self, trip):
        self.trips.append(trip)
        trip.set_route(self)

    def has_similar_trip(self, trip, trip_collection):
        for t in trip_collection:
            if trip.is_similar(t):
                return True

        return False

    def remove_duplicated_trips(self):
        unique_trips = []
        duplicate_trip_ids = []
        for trip in self.trips:
            if not self.has_similar_trip(trip, unique_trips):
                unique_trips.append(trip)
            else:
                duplicate_trip_ids.append(trip.id)

        self.trips = unique_trips

        return duplicate_trip_ids

    def remove_truncated_trips(self):
        """
        For each headsign, this function keeps only the longest trip. The point
        is to keep only one trip for each direction.
        """
        dups = {}
        truncated_trip_ids = []
        for trip in self.trips:
            if trip.ref in dups:
                if len(dups[trip.ref].stops) < len(trip.stops):
                    truncated_trip_ids.append(dups[trip.ref].id)
                    dups[trip.ref] = trip
                else:
                    truncated_trip_ids.append(trip.id)
            else:
                dups[trip.ref] = trip

        self.trips = list(dups.values())

        return truncated_trip_ids


    def get_trip_by_name(self, name):
        for trip in self.trips:
            if trip.ref == name:
                return trip



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
            if s.name == stop.name and \
               s.lat == stop.lat and s.lon == stop.lon:
                return s

    def add_stop(self, stop, deduplicate=False):
        existing_stop = None
        if deduplicate:
            existing_stop = self.find_duplicate_stop(stop)

        if existing_stop:
            self._stops_by_id[stop.id] = existing_stop
            if stop.ref not in existing_stop.refs:
                existing_stop.add_ref(stop.ref)
                print(existing_stop.refs)
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


if __name__ == "__main__":

    stop = Stop.fromGTFS(1234, 0.1, 0.2, "toto", "5678")
    print(stop.name)
