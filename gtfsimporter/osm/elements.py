
from collections import defaultdict

from math import cos, pi

class Node(object):

    def __init__(self, id, lat, lon):
        self.id = id
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

class StopTime(object):

#    def __init__(self, stop, sequence):
#        self.stop = stop
#        self.sequence = sequence
#
    def __init__(self, trip_id, stop_id, sequence):
        self.trip_id = trip_id
        self.stop_id = stop_id
        self.sequence = sequence

    def set_stop(self, stop):
        self.stop = stop

    def __eq__(self, other):
        return self.stop == other.stop and \
               self.sequence == other.sequence

class Stop(Node):

    def __init__(self, name, refs, lon, lat, id, highway, bus, public_transport):
        self.name = name
        if refs is not None:
            self.refs = refs.split(";")
        else:
            self.refs = None
        super().__init__(id, lat, lon)
        self.highway = highway
        self.bus = bus
        self.public_transport = public_transport

    @property
    def ref(self):
        assert len(self.refs) == 1
        return self.refs[0]

    def __repr__(self):
        return "<Stop id={}, refs={}, name={}, coord=[{}, {}]>".format(
                self.id, self.refs, self.name, self.lon, self.lat)

#    def export(self, format="csv", *args):
#        if format == "csv":
#            self.export_csv(*args)
#
#    def export_csv(self, path):
#        with open(path, 'w') as csvfile:
#            fieldnames = ['ref', 'name', 'longitude', 'latitude', 'public_transport',
#                          'highway', 'bus']
#            writer = csv.writer(csvfile, delimiter=",")
#            writer.writerow(fieldnames)
#
#            for stop in self.stops:
#                refs = ";".join(stop.refs)
#                writer.writerow([refs, stop.name, stop.lon, stop.lat,
#                                 stop.public_transport, stop.highway, stop.bus])


class Trip(object):

    def __init__(self, trip_id, route_id, headsign, network=None, operator=None, shape_id=None):
        self.id = trip_id
        self.route_id = route_id
        self.headsign = headsign
        self.stops = {}
        self.network = network
        self.operator = operator
        self.shape_id = shape_id
        self.way = WayUnordered()

    def __len__(self):
        return len(self.stops)

    def add_route(self, route):
        self.route = route
        if not self.network:
            self.network = route.network
        if not self.operator:
            self.operator = route.operator

    def add_stop_time(self, stop_time):
        self.stops[stop_time.sequence] = stop_time

    def get_ordered_stops(self):
        for sequence in sorted(self.stops.keys()):
            yield self.stops[sequence].stop

    def is_similar(self, other):
        if self.route != other.route or self.headsign != other.headsign:
            return False
        if len(self.stops) != len(other.stops):
            return False

        for stop_time_seq, stop_time in self.stops.items():
            if other.stops[stop_time_seq] != stop_time:
                return False
        else:
            return True

    def __repr__(self):
        return "<Trip id={}, name={}, {} stops>".format(self.id, self.headsign, len(self.stops))


class Route(object):

    def __init__(self, id, code, name, network=None, operator=None):
        self.id = id
        self.code = code
        self.name = name
        self.trips = []
        self.network = network
        self.operator = operator

    def add_trip(self, trip):
        self.trips.append(trip)

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
            if trip.headsign in dups:
                if len(dups[trip.headsign].stops) < len(trip.stops):
                    truncated_trip_ids.append(dups[trip.headsign].id)
                    dups[trip.headsign] = trip
                else:
                    truncated_trip_ids.append(trip.id)
            else:
                dups[trip.headsign] = trip

        self.trips = list(dups.values())

        return truncated_trip_ids


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
            if s.name == stop.name and s.ref == stop.ref and \
               s.lat == stop.lat and s.lon == stop.lon:
                return s

    def add_stop(self, stop, deduplicate=False):
        existing_stop = None
        if deduplicate:
            existing_stop = self.find_duplicate_stop(stop)

        if existing_stop:
            self._stops_by_id[stop.id] = existing_stop
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
            return self._stops_dict.get(stop_id, default)
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
        for route in self.routes:
            trip_ids = route.remove_duplicated_trips()
            removed += len(trip_ids)
            self.drop_trips(trip_ids)

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

