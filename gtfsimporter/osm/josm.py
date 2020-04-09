
import xml.etree.ElementTree as ET


def IdFactory():
    i = 0
    while True:
        i -= 1
        yield i

id_factory = IdFactory()

def GetIdFactory():
    return id_factory


class OsmObject:

    # picked from Overpy, to revert these modifications on attributes
    GLOBAL_ATTRIBUTE_MODIFIERS = {
        "changeset": str,
        "timestamp": lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uid": str,
        "version": str,
    }

    def __init__(self, id, tags=None, attrs=None):
        if id is None:
            id = next(GetIdFactory())
        self.osm_id = str(id)
        if tags is None:
            tags = {}
        self.tags = tags
        self.attrs = attrs
        self.modified = False


    def add_tag(self, key, value):
        self.tags[key] = value

    def export_tags(self, container):
        for key in self.tags:
            subelement = ET.SubElement(container, "tag")
            subelement.set("k", key)
            subelement.set("v", self.tags[key])

    def create_element(self, container, typ):
        element = ET.SubElement(container, typ)
        element.set("id", self.osm_id)
        if self.attrs:
            for key, val in self.attrs.items():
                if key in OsmObject.GLOBAL_ATTRIBUTE_MODIFIERS:
                    modifier = OsmObject.GLOBAL_ATTRIBUTE_MODIFIERS[key]
                    val = modifier(val)
                element.set(key, val)
        if int(self.osm_id) < 0 or self.modified:
            element.set("action", "modify")
            element.set("visible", "true")
        return element

class Node(OsmObject):

    def __init__(self, osm_id, lat, lon, tags=None, attrs=None):
        super().__init__(osm_id, tags, attrs)
        self.lat = float(lat)
        self.lon = float(lon)

    def export(self, container):
        node = self.create_element(container, "node")
        node.set("lat", "{:.7f}".format(self.lat))
        node.set("lon", "{:.7f}".format(self.lon))
        super().export_tags(node)

class Way(OsmObject):

    def __init__(self, way):
        super().__init__()
        self.nodes = []
        for coords in way.get_ordered_nodes():
            self.nodes.append(Node(*coords))

    def export(self, container):
        way = self.create_element(container, "way")
        for node in self.nodes:
            node.export(container)

            nd = ET.SubElement(way, "nd")
            nd.set("ref", node.id)
        self.export_tags(way)

class RelationMember:

    def __init__(self, type, ref, role):
        self.type = type
        self.ref = str(ref)
        self.role = role

    def export(self, container):
        subelement = ET.SubElement(container, "member")
        subelement.set("type", self.type)
        subelement.set("ref", self.ref)
        subelement.set("role", self.role)


class StopRelationMember(RelationMember):

    def __init__(self, ref, role="platform"):
        super().__init__("node", ref, role)


class WayRelationMember(RelationMember):

    def __init__(self, ref):
        super().__init__("way", ref, "")


class Relation(OsmObject):

    def __init__(self, osm_id, tags, attributes, members=None):
        super().__init__(osm_id, tags, attributes)
        if members is None:
            members = []
        self.members = members

    def add_member(self, relation_member):
        self.members.append(relation_member)

    def export_members(self, container):
        for member in self.members:
            member.export(container)

    def export(self, container):
        relation = self.create_element(container, "relation")
        self.export_members(relation)
        self.export_tags(relation)


class RouteRelation(Relation):

    def __init__(self, trip, stops_by_ref):
        super().__init__(trip.id, trip.tags, trip.attributes)
        self.trip = trip
        self.stops_by_ref = stops_by_ref

        for stop in self.trip.stops:
            ref = stop.refs[0]

            assert ref in stops_by_ref, f"missing ref {ref}"
            osm_stop = stops_by_ref[ref]

            stop_pos = trip.get_stop_position(stop)
            if stop_pos:
                stop_pos_member = StopRelationMember(stop_pos, "stop")
                self.add_member(stop_member)

            stop_role = trip.get_stop_role(stop)
            if not stop_role:
                stop_role = "platform"

            stop_member = StopRelationMember(osm_stop.id, stop_role)
            self.add_member(stop_member)

        for way in trip.ways:
            way_member = WayRelationMember(way)
            self.add_member(way_member)

        assert self.trip.from_stop, f"from_stop is None for {self.trip.name}"
        assert self.trip.to_stop, f"to_stop is None for {self.trip.name}"
        self.add_tag("from", self.trip.from_stop)
        self.add_tag("to", self.trip.to_stop)

        if trip.modified:
            self.modified = True

    def export(self, container):
        #if self.way:
        #    self.way.export(container)
        super().export(container)


class RouteMasterRelation(Relation):

    def __init__(self, route, stops_by_ref):
        super().__init__(route.id, route.tags, route.attributes)
        self.route = route
        self.stops_by_ref = stops_by_ref

        self.route_relations = []
        for trip in self.route.trips:
            route_rel = RouteRelation(trip, self.stops_by_ref)
            self.add_member(RelationMember("relation", route_rel.osm_id, ""))
            self.route_relations.append(route_rel)

        self.modified = route.modified

    def export(self, container, export_subrelations=True):
        if export_subrelations:
            for route_relation in self.route_relations:
                route_relation.export(container)
        super().export(container)


class JosmDocument(object):

    def __init__(self):
        self.container = ET.Element("osm")
        self.container.set("version", "0.6")
        self.container.set("generator", "GTFS Importer")

        self.tree = ET.ElementTree(self.container)

    def export_stops(self, stop_list, keep_attributes=False):
        for stop in stop_list:
            assert stop.name

            node = Node(stop.id, stop.lat, stop.lon, stop.tags, stop.attributes)
            if stop.is_modified():
                node.modified = True

            node.export(self.container)

    def export_route(self, route, stop_list):
        routes = (route, )
        return self.export_routes(routes, stop_list)

    def export_routes(self, routes, stop_list):
        stops_by_ref = dict()
        for stop in stop_list:
            #possible that we encounter a stop mapped without ref in OSM
            if stop.refs is None:
                continue

            for ref in stop.refs:
                stops_by_ref[ref] = stop

        successfully_exported_routes = 0
        for route in routes:
            try:
                route_master = RouteMasterRelation(route, stops_by_ref)
                route_master.export(self.container)
                successfully_exported_routes += 1
            except Exception as e:
                print("Failed to generate route: \"{}\"".format(route.name))
                print("Following exception occured: {}".format(e))
                #import traceback
                #traceback.print_tb(e.__traceback__)

        return successfully_exported_routes

    def write(self, fil):
        
        self.tree.write(fil, encoding="unicode", xml_declaration=True)
