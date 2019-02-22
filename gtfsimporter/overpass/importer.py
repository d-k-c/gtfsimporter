

from pprint import pprint

from ..osm.elements import Route, Schedule, Stop, StopTime, Trip
from ..validator.issue import *


import overpy
import requests

class OsmImporter():

    PLATFORM_QUERY = """
    [out:xml][timeout:30][bbox:{},{},{},{}];
    (
        node["public_transport"="platform"]["ref"];
    );
    out body;
    """

    def __init__(self, area):
        self.area = area
        self._stops_dict = {}
        self.routes = []

    @property
    def stops(self):
        return self._stops_dict.values()

    def check_tag(self, schedule, stop, tag_name, expected_value=None):
        value = getattr(stop, tag_name)

        if not value:
            issue = AttributeMissingIssue(stop, tag_name, expected_value)
            schedule.issues.append(issue)
        elif expected_value and value != expected_value:
            issue = InvalidAttributeValueIssue(stop, tag_name, value, expected_value)
            schedule.issues.append(issue)

    def generate_cache(self, cache_path):
        """
        Generate a cache file containing bus platforms

        In order to minimize requests to the Overpass API, a cache file can be
        used. For now, it caches the result of the query that is used by the
        load_stops function.
        """
        query = self.PLATFORM_QUERY.format(*self.area)
        r = requests.post("http://overpass-api.de/api/interpreter", data=query)
        if r.status_code != 200:
            print(f"Something went wrong when generating cache ({r.status_code}), aborting.")
            return False

        with open(cache_path, 'w') as cache_file:
            cache_file.write(r.text)


    def load_stops(self, schedule, xml=None):

        if xml:
            response = overpy.Result.from_xml(xml, parser=overpy.XML_PARSER_DOM)
        else:
            query = self.PLATFORM_QUERY.format(*self.area)
            api = overpy.Overpass()
            response = api.query(query)
        for node in response.nodes:
            id, lat, lon = node.id, node.lat, node.lon
            tags = node.tags
            refs = tags.get("ref")
            public_transport = tags.get("public_transport")

            name = tags.get("name", None)
            highway = tags.get("highway", None)
            bus = tags.get("bus", None)

            stop = Stop(name, refs, lon, lat, id, highway, bus, public_transport)
            schedule.add_stop(stop)

            self.check_tag(schedule, stop, "highway", "bus_stop")
            self.check_tag(schedule, stop, "bus", "yes")
            self.check_tag(schedule, stop, "name")

    def _build_master_route(self, schedule, master_relation):
        id = master_relation.id
        name = master_relation.tags.get("name", None)
        code = master_relation.tags.get("ref", None)
        network = master_relation.tags.get("network", None)
        operator = master_relation.tags.get("operator", None)

        master = Route(id, code, name, network, operator)
        schedule.add_route(master)

        for relation_member in master_relation.members:
            relation = relation_member.resolve()
            self._build_trip(schedule, relation, master)

    def _build_trip(self, schedule, relation, route):
        id = relation.id
        headsign = relation.tags.get("ref", None)
        network = relation.tags.get("network", None)
        operator = relation.tags.get("operator", None)
        # TODO: load additional tags: name, name:en, to, from, type,
        # public_transport:version

        trip = Trip(id, route, headsign, network, operator)
        schedule.add_trip(trip)

        sequence = 1
        for member in relation.members:
            if not isinstance(member, overpy.RelationNode) or \
                not member.role.startswith("platform"):
                continue

            stop = schedule.get_stop(member.ref, None)

            # TODO: assert stop is not None

            stop_time = StopTime(stop, sequence)
            schedule.add_stop_time(trip, stop_time)
            sequence += 1

    def load_routes(self, schedule, xml=None):
        #   self.query = """
        #       rel(45.3664,-74.0856,45.775,-73.326)[route=bus]->.bus_routes;
        #       rel[route_master=bus](br.bus_routes)->.master_routes;
        #       node(r.bus_routes)->.bus_stops;

        #       (.master_routes; .bus_routes; .bus_stops;)->._;
        #       out body;
        #       """
#       #    self.query = "rel(45.3664,-74.0856,45.775,-73.326)[route=bus]; out body;"

        if xml:
            response = overpy.Result.from_xml(xml, parser=overpy.XML_PARSER_DOM)

        for relation in response.relations:
            if relation.tags.get("route_master", None) == "bus":
                self._build_master_route(schedule, relation)

        # TODO: reiterate over the list to see if all route=bus
        # relations have beeen created, or if there are some orphan
        # routes

    def load(self, xml=None):
        schedule = Schedule()
        self.load_stops(schedule, xml)
        #self.load_routes(schedule, xml)

        return schedule
