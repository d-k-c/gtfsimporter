
import xml.etree.ElementTree as ET


def IdFactory():
    i = 0
    while True:
        i -= 1
        yield str(i)

id_factory = IdFactory()

def GetIdFactory():
    return id_factory


class OsmObject:

    def __init__(self, id=None, tags=None):
        if id is None:
            id = next(GetIdFactory())
        self.id = id
        if tags is None:
            tags = {}
        self.tags = tags


    def add_tag(self, key, value):
        self.tags[key] = value

    def export_tags(self, container):
        for key in self.tags:
            subelement = ET.SubElement(container, "tag")
            subelement.set("k", key)
            subelement.set("v", self.tags[key])

    def create_element(self, container, typ):
        element = ET.SubElement(container, typ)
        element.set("id", self.id)
        if int(self.id) < 0:
            element.set("action", "modify")
            element.set("visible", "true")
        return element

class Node(OsmObject):

    def __init__(self, lat, lon, id=None):
        super().__init__(id)
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

    def __init__(self, ref):
        super().__init__("node", ref, "platform")


class WayRelationMember(RelationMember):

    def __init__(self, ref):
        super().__init__("way", ref, "")


class Relation(OsmObject):

    def __init__(self, members=None):
        super().__init__()
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

    def __init__(self, trip, stops):
        super().__init__()
        self.trip = trip
        self.stops = stops

        self.add_tag("route", "bus")
        self.add_tag("type", "route")
        self.add_tag("public_transport:version", "2")
        self.add_tag("ref", trip.headsign)
        self.add_tag("name", trip.get_name())

        # handle extra locales for multilingual agencies
        if hasattr(trip, "extra_locales"):
            for locale in trip.extra_locales:
                tag_name = f'name:{locale}'
                trip_name = trip.get_name(locale)
                self.add_tag(tag_name, trip_name)

        self.add_tag("network", trip.network)
        self.add_tag("operator", trip.operator)

        from_stop = to_stop = None
        for stop in self.trip.get_ordered_stops():
            ref = stop.refs[0]

            assert ref in stops, f"missing ref {ref}"
            osm_stop = stops[ref]

            to_stop = osm_stop.name
            if from_stop is None:
                from_stop = osm_stop.name

            stop_member = StopRelationMember(osm_stop.id)
            self.add_member(stop_member)

        self.way = None
        if len(self.trip.way):
            self.way = Way(self.trip.way)
            way_member = WayRelationMember(self.way.id)
            self.add_member(way_member)

        assert from_stop is not None
        assert to_stop is not None
        self.add_tag("from", from_stop)
        self.add_tag("to", to_stop)

    def export(self, container):
        if self.way:
            self.way.export(container)
        super().export(container)


class RouteMasterRelation(Relation):

    def __init__(self, route, stops):
        super().__init__()
        self.route = route
        self.stops = stops

        self.add_tag("name", route.get_name())

        # handle extra locales for multilingual agencies
        if hasattr(route, "extra_locales"):
            for locale in route.extra_locales:
                tag_name = f'name:{locale}'
                route_name = route.get_name(locale)
                self.add_tag(tag_name, route_name)

        self.add_tag("ref", route.code)
        self.add_tag("network", route.network)
        self.add_tag("operator", route.operator)

        self.add_tag("type", "route_master")
        self.add_tag("route_master", "bus")
        self.add_tag("public_transport:version", "2")

        self.route_relations = []
        for trip in self.route.trips:
            route_rel = RouteRelation(trip, self.stops)
            self.add_member(RelationMember("relation", route_rel.id, ""))
            self.route_relations.append(route_rel)

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

    def export_stops(self, stop_list):
        for stop in stop_list:
            assert stop.name
            node = Node(stop.lat, stop.lon)
            node.add_tag("bus", "yes")
            node.add_tag("highway", "bus_stop")
            node.add_tag("name", stop.name)
            node.add_tag("public_transport", "platform")
            node.add_tag("ref", ";".join(stop.refs))
            node.export(self.container)

    def export_route(self, route, stop_list):
        routes = (route, )
        return self.export_routes(routes, stop_list)

    def export_routes(self, routes, stop_list):
        stops_by_ref = dict()
        for stop in stop_list:
            for ref in stop.refs:
                stops_by_ref[ref] = stop

        successfully_exported_routes = 0
        for route in routes:
            try:
                route_master = RouteMasterRelation(route, stops_by_ref)
                route_master.export(self.container)
                successfully_exported_routes += 1
            except Exception as e:
                print("Failed to generate route: \"{}\"".format(route.get_name()))
                print("Following exception occured: {}".format(e))

        return successfully_exported_routes

    def write(self, fil):
        self.tree.write(fil, encoding="unicode", xml_declaration=True)
