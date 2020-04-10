

from pprint import pprint

from .elements import OsmRoute, Schedule, OsmStop, OsmTrip
from ..validator.issue import *


import overpy
import requests

class OverpassImporter():

    PLATFORM_QUERY = """
    [out:xml][timeout:30][bbox:{},{},{},{}];
    node["public_transport"="platform"]["ref"]->.all_ref_platforms;
    rel["route"="bus"](bn.all_ref_platforms)->.containing_routes;
    rel["route_master"="bus"](br.containing_routes)->.master_routes;
    rel(r.master_routes)->.bus_routes;
    node(r.bus_routes)->.stops_within_routes;

    (.stops_within_routes; .all_ref_platforms;)->._;

    //(.master_routes;)->._;

    out meta;
    """

    ROUTES_QUERY = """
    [out:xml][timeout:30][bbox:{},{},{},{}];
    node["public_transport"="platform"]->.all_platforms;
    rel["route"="bus"](bn.all_platforms)->.containing_routes;
    rel(br.containing_routes)->.master_routes;
    rel(r.master_routes)->.bus_routes;

    node(r.bus_routes)->.stops_within_routes;
    
    (.all_platforms; .stops_within_routes; .bus_routes; .master_routes;)->._;
    
    out meta;
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

    def generate_cache(self, overpass_query, path):
        query = overpass_query.format(*self.area)
        print(query)
        r = requests.post("http://overpass-api.de/api/interpreter", data=query)
        if r.status_code != 200:
            print(f"Something went wrong when generating cache ({r.status_code}), aborting.")
            print(r.text)
            return False

        with open(path, 'w') as cache_file:
            cache_file.write(r.text)

    def generate_cache_stops(self, cache_path):
        """
        Generate a cache file containing bus platforms

        In order to minimize requests to the Overpass API, a cache file can be
        used. For now, it caches the result of the query that is used by the
        load_stops function.
        """
        self.generate_cache(self.PLATFORM_QUERY, cache_path)

    def generate_cache_routes(self, cache_path):
        self.generate_cache(self.ROUTES_QUERY, cache_path)

    def load_stops(self, schedule, xml=None):

        if xml:
            response = overpy.Result.from_xml(xml, parser=overpy.XML_PARSER_DOM)
        else:
            query = self.PLATFORM_QUERY.format(*self.area)
            api = overpy.Overpass()
            response = api.query(query)
        for node in response.nodes:
            id, lat, lon = node.id, node.lat, node.lon

            stop = OsmStop(id, lon, lat, node.tags, node.attributes)
            schedule.add_stop(stop)

            #self.check_tag(schedule, stop, "highway", "bus_stop")
            #self.check_tag(schedule, stop, "bus", "yes")
            #self.check_tag(schedule, stop, "name")

    def _build_master_route(self, schedule, master_relation):
        id = master_relation.id

        master = OsmRoute(id, master_relation.tags, master_relation.attributes)
        schedule.add_route(master)

        for relation_member in master_relation.members:
            relation = relation_member.resolve()
            try:
                trip = self._build_trip(schedule, relation)
                master.add_trip(trip)
            except Exception as e:
                print(e)


    def _build_trip(self, schedule, relation):

        trip = OsmTrip(relation.id, relation.tags, relation.attributes)

        stop_position = None
        for member in relation.members:
            if isinstance(member, overpy.RelationNode):
                if member.role == "stop":
                    stop_position = member.ref
                elif member.role.startswith("platform"):
                    stop = schedule.get_stop(member.ref, None)

                    if stop is None:
                        trip.set_import_error(
                           f"stop with id <{member.ref}> missing in OSM dataset")
                        break

                    trip.append_stop(stop, member.role, stop_position)
                    stop_position = None
                else:
                    trip.set_import_error(
                        f"Unexpected node role '{member.role}' found in {trip.name}")
                    break
            elif isinstance(member, overpy.RelationWay):
                if stop_position is not None:
                    trip.set_import_error(
                       f"unexpected stop position in {trip.name}")
                    break

                if member.role != "":
                    trip.set_import_error(
                       f"way with role in {trip.name}")
                    break

                trip.append_way(member.ref)

        return trip


    def load_routes(self, schedule, xml=None):
        self.load_stops(schedule, xml)

        if not xml:
            raise NotImplementedError("Can only use XML to load routes")

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
