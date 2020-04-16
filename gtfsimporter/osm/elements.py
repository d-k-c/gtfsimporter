
from collections import defaultdict
from math import cos, pi

from functools import partialmethod, partial


class SupportTagMetaclass(type):

    def __new__(cls, clsname, bases, attrs):

        obj = super(SupportTagMetaclass, cls).__new__(cls, clsname, bases, attrs)

        supported_tags = attrs.get("element_tags", None)
        if supported_tags is None:
            return obj

        for t in supported_tags:
            if len(t) == 2:
                t, property_name = t
            else:
                property_name = t
            fget = lambda self, name=t: self.get_tag(name)
            fset = lambda self, value, name=t: self.set_tag(name, value)
            setattr(obj, property_name, property(fget=fget, fset=fset))

        return obj


class OsmElement(object, metaclass=SupportTagMetaclass):

    def __init__(self, osm_id, tags, attributes):
        self.id = osm_id
        if tags is None:
            tags = {}
        if attributes is None:
            attributes = {}

        self.tags = tags
        self.attributes = attributes
        self.modified = False

    def get_tag(self, name):
        return self.tags.get(name, None)

    def set_tag(self, name, value):
        old_value = self.get_tag(name)
        if old_value != value:
            self.tags[name] = value
            self.modified = True

    def is_modified(self):
        return self.modified

    def add_extra_tags(self, gtfs_element):
        for extra_tag in gtfs_element.extra_tags:
            self.set_tag(extra_tag, gtfs_element.get_extra_tag(extra_tag))



class OsmNode(OsmElement):

    def __init__(self, node_id, lat, lon, tags, attributes):
        super().__init__(node_id, tags, attributes)
        self.lat = lat
        self.lon = lon


class OsmStop(OsmNode):

    element_tags = [ "name", "ref" ]

    def __init__(self, osm_id, lat, lon, tags, attributes):
        super().__init__(osm_id, lat, lon, tags, attributes)

    @classmethod
    def fromGtfs(cls, gtfs_stop):
        stop = cls(None, gtfs_stop.lat, gtfs_stop.lon, None, None)
        stop.merge_gtfs(gtfs_stop)

        return stop

    def merge_gtfs(self, gtfs_stop):
        self.name = gtfs_stop.name
        self.ref = ";".join(gtfs_stop.refs)

        self.set_tag("highway", "bus_stop")
        self.set_tag("bus", "yes")
        self.set_tag("public_transport", "platform")

        self.add_extra_tags(gtfs_stop)

    @property
    def refs(self):
        if self.ref is not None:
            return self.ref.split(";")
        else:
            return list()

    def __repr__(self):
        return "<Stop id={}, refs={}, name={}, coord=[{}, {}]>".format(
                self.id, self.refs, self.name, self.lat, self.lon)


class OsmTrip(OsmElement):

    element_tags = [
        ("from", "from_stop"), "name", "network", "operator",
        "ref", ("to", "to_stop")
    ]

    def __init__(self, trip_id, tags, attributes):
        super().__init__(trip_id, tags, attributes)

        self.stops_data = {}
        self.stops = []
        self.ways = []
        self.error = None

    @classmethod
    def fromGtfs(cls, gtfs_trip, osm_schedule):
        trip = cls(None, None, None)
        trip.merge_gtfs(gtfs_trip, osm_schedule)

        return trip

    def merge_gtfs(self, gtfs_trip, osm_schedule):
        self.name = gtfs_trip.name
        self.ref = gtfs_trip.ref
        self.network = gtfs_trip.network
        self.operator = gtfs_trip.operator

        self.set_tag("route", "bus")
        self.set_tag("type", "route")
        self.set_tag("public_transport:version", "2")
        
        self.update_stops(osm_schedule, gtfs_trip)
        assert self.stops, f"Empty list stop for trip {self.name}"
        
        gtfs_from = gtfs_trip.from_stop
        if gtfs_from is None:
            gtfs_from = self.stops[0].name
        self.from_stop = gtfs_from

        gtfs_to = gtfs_trip.to_stop
        if gtfs_to is None:
            gtfs_to = self.stops[-1].name
        self.to_stop = gtfs_to

        self.add_extra_tags(gtfs_trip)

    def update_stops(self, osm_schedule, gtfs_trip):
        new_stops = []
        gtfs_stop_refs = [stop.ref for stop in gtfs_trip.stops]

        for ref in gtfs_stop_refs:
            new_stop = osm_schedule.get_stop_by_ref(ref)
            assert new_stop is not None, f"Stop with ref {ref} missing in OSM dataset"

            new_stops.append(new_stop)

        if new_stops != self.stops:
            self.modified = True
            self.stops = new_stops


    def __len__(self):
        return len(self.stops)

    def set_tag_error(self, name, value):
        raise AttributeError(f"object is read-only because import failed: {self.error}")

    def set_import_error(self, error):
        self.error = error
        self.modified = False
        self.set_tag = self.set_tag_error

    def import_failed(self):
        return self.error is not None

    def set_route(self, route):
        self.parent_route = route

    def append_stop(self, stop, role, stop_position=None):
        self.stops.append(stop)
        self.stops_data[stop] = (role, stop_position)

    def append_way(self, way_ref):
        self.ways.append(way_ref)

    def get_tags(self):
        return self.tags.items()

    def get_stop_position(self, stop):
        _, stop_pos = self.stops_data.get(stop, (None, None))
        return stop_pos

    def get_stop_role(self, stop):
        role, _ = self.stops_data.get(stop, ("platform", None))
        return role

    def __repr__(self):
        return "<Trip id={}, name={}, {} stops>".format(self.id, self.ref, len(self.stops))


class OsmTripsNotUpdatedError(Exception):
    pass


class OsmRoute(OsmElement):

    element_tags = ["name", "network", "operator", "ref"]

    def __init__(self, id, tags, attributes):
        super().__init__(id, tags, attributes)
        self.trips = []

    @classmethod
    def fromGtfs(cls, gtfs_route, osm_schedule):
        route = cls(None, None, None)
        route.merge_gtfs(gtfs_route, osm_schedule)

        return route

    def merge_gtfs(self, gtfs_route, osm_schedule):
        self.merge_tags(gtfs_route)
        self.merge_trips(gtfs_route, osm_schedule)

    def merge_tags(self, gtfs_route):
        self.name = gtfs_route.name
        self.ref = gtfs_route.ref
        self.network = gtfs_route.network
        self.operator = gtfs_route.operator

        self.set_tag("route_master", "bus")
        self.set_tag("type", "route_master")


    def merge_trips(self, gtfs_route, osm_schedule):
        unupdated_trips = self.trips.copy()

        for trip in gtfs_route.trips:
            osm_trip = self.get_trip_by_ref(trip.ref)
            if osm_trip is None:
                osm_trip = OsmTrip.fromGtfs(trip, osm_schedule)
                self.add_trip(osm_trip)
            else:
                osm_trip.merge_gtfs(trip, osm_schedule)
                unupdated_trips.remove(osm_trip)

        # the idea is to have a one-to-one relation between GTFS trips and OSM
        # trips. If some trips were updated but not some others, it might mean
        # that they were removed in the GTFS dataset for instance. Anyway, it
        # requires manual intervention
        if unupdated_trips:
            refs = ",".join([t.ref for t in unupdated_trips])
            raise OsmTripsNotUpdatedError(f"Trips '{refs}' not updated")
        
        self.add_extra_tags(gtfs_route)

    @property
    def code(self):
        return self.get_tag("ref")

    def add_trip(self, trip):
        self.trips.append(trip)
        trip.set_route(self)

    def get_trip_by_ref(self, ref):
        for trip in self.trips:
            if trip.ref == ref:
                return trip
