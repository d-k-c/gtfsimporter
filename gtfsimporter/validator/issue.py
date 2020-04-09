
from collections import defaultdict

class IssueMetaclass(type):
    """
    This metaclass will add attributes "header" and "line_fmt"
    based on the "fields" attributes. That allows some pretty printing
    in an array-like fashion.
    """

    def __new__(cls, clsname, bases, dct):

        obj = super().__new__(cls, clsname, bases, dct)
        if not 'fields' in dct:
            return obj

        fields = dct['fields']

        pretty_fields = []
        max_len = 0
        for name, length in fields:
            optimal_length = len(name) + 2
            if length:
                optimal_length = max(optimal_length, length)
            pretty_field = "{{:^{}.{}}}".format(
                    optimal_length, optimal_length - 2)
            pretty_fields.append(pretty_field)
            max_len += optimal_length

        line_format = "|".join(pretty_fields)
        setattr(obj, "line_fmt", line_format)

        max_len += len(pretty_fields) - 1

        names = [name for name, _ in fields]
        header = line_format.format(*names) + "\n" + "-" * max_len
        setattr(obj, "header", header)

        return obj

class Issue(object, metaclass=IssueMetaclass):

    def format_line(self, *args):
        args = [str(arg) for arg in args]
        return self.line_fmt.format(*args)


class OsmStopMissingIssue(Issue):
    """
    Represent a stop present in the GTFS dataset but missing in OSM
    """

    description = "GTFS Stops Missing In OSM"
    fields = (
        ("GTFS Stop Code", None),
        ("Stop Name", 30),
        ("Lat/Lon", 22)
    )

    def __init__(self, gtfs_stop):
        self.stop = gtfs_stop
        #assert len(self.stop.refs) == 1

    def line(self):
        ref = self.stop.refs[0]
        name = self.stop.name
        position = "{}/{}".format(self.stop.lat, self.stop.lon)
        return self.format_line(ref, name, position)

    def report(self):
        ref = self.stop.refs[0]
        return "GTFS Stop with stop_code '{}' missing in OSM".format(ref)

class OsmStopWithUnknownRefIssue(Issue):
    """
    Represent a stop present in OSM but whose "ref" tag is not
    present in the GTFS dataset
    """

    description = "OSM Stops With Unknown 'ref' Tag"
    fields = (
        ("OSM Stop ID", None),
        ("Unkown ref", None)
    )

    def __init__(self, osm_stop):
        self.stop = osm_stop
        #assert len(self.stop.refs) == 1

    def line(self):
        return self.format_line(self.stop.id, self.stop.refs[0])

    def report(self):
        ref = self.stop.refs[0]
        return "OSM Stop with ref '{}' not present in GTFS".format(ref)


class AttributeMissingIssue(Issue):

    description = "OSM Stops Missing Expected Tag"
    fields = (
        ("OSM Stop ID", None),
        ("Tag Name", 15),
        ("Tag Expected Value", None)
    )

    def __init__(self, osm_stop, attr_name, attr_expected_value=None):
        self.stop = osm_stop
        self.attribute = attr_name
        self.value = attr_expected_value

    def line(self):
        value = "-" if self.value is None else self.value
        return self.format_line(self.stop.id, self.attribute, value)

    def report(self):
        rep = "OSM Stop with id '{}' is missing attribute '{}'.".format(
                self.stop.id, self.attribute)
        if self.value:
            rep += " Should be '{}'.".format(self.value)
        return rep

class InvalidAttributeValueIssue(Issue):

    description = "OSM Stops With Unexpected Tag Value"
    fields = (
        ("OSM Stop ID", None),
        ("Tag Name", 15),
        ("Current Tag Value", None),
        ("Expected Tag Value", None)
    )

    def __init__(self, osm_stop, attr_name, current_value, expected_value):
        self.stop = osm_stop
        self.attribute = attr_name
        self.current_val = current_value
        self.expected_val = expected_value

    def line(self):
        return self.format_line(
            self.stop.id, self.attribute,
            self.current_val, self.expected_val)

    def report(self):
        rep = "OSM Stop with id '{}' has attribute with unexpected value. '{}' is " \
              "'{}' but should be '{}'".format(
                      self.stop.id, self.attribute, self.current_val, self.expected_val)
        return rep


class NodesTooFarIssue(Issue):

    description = "Nodes with common ref in GTFS and OSM that are too far apart"
    fields = (
        ("OSM Stop ID", 12),
        ("GTFS Stop ID", 12),
        ("Reference", 7),
        ("Distance", None)
    )

    def line(self):
        distance = "{:.1f}".format(self.distance)
        return self.format_line(
            self.osm_stop.id, self.gtfs_stop.id, self.gtfs_stop.refs[0],
            distance)

    def __init__(self, osm_stop, gtfs_stop, distance):
        self.osm_stop = osm_stop
        self.gtfs_stop = gtfs_stop
        self.distance = distance

    def report(self):
        rep = "OSM Stop '{}' and GTFS Stop '{}' are too far apart {:.1f}"
        return rep.format(self.osm_stop.id, self.gtfs_stop.id, self.distance)


class IssueList:

    def __init__(self):
        self.issues = []

    def append(self, issue):
        self.issues.append(issue)

    def extend(self, issues):
        self.issues.extend(issues)

    def print_report(self):
        issues_by_type = defaultdict(list)
        for issue in self.issues:
            issues_by_type[type(issue)].append(issue)

        for issue_cls, issues in issues_by_type.items():
            print("\n")
            print("**", issue_cls.description, "**")

            print(issue_cls.header)
            for issue in issues:
                print(issue.line())
