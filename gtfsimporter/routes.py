

from .overpass.importer import OverpassRouteImporter

import overpy

route_import = OverpassRouteImporter()
response = route_import.fetch()

for element in response.relations:
    if element.tags.get("type") == "route" and element.tags.get("public_transport:version") == "2":
        print(element.tags.get("name"), element.tags.get("ref"))
        for part in element.members:
            if isinstance(part, overpy.RelationNode) and part.role == "platform":
                node = response.get_node(part.ref)
                ref, name = node.tags.get("ref"), node.tags.get("name")
                print("\t", ref, name)

