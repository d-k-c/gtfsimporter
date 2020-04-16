
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
                self.id, self.refs, self.name, self.lat, self.lon)


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
