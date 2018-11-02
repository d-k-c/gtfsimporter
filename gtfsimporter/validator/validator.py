
from haversine import haversine

from .issue import *

class StopValidator(object):

    def __init__(self, issues, gtfs_stops, osm_stops):
        self.issues = issues
        self.gtfs_by_ref = {}
        self.osm_by_ref = {}
        self.osm_without_ref = []

        self.populate_by_ref(self.gtfs_by_ref, gtfs_stops)
        self.populate_by_ref(self.osm_by_ref,
                             osm_stops,
                             self.osm_without_ref)

    def populate_by_ref(self, dic, stop_list, lst=None):
        for stop in stop_list:
            if not stop.refs and lst:
                lst.append(stop)

            for ref in stop.refs:
                dic[ref] = stop

    def get_common_refs(self):
        osm_refs = set(self.osm_by_ref.keys())
        gtfs_refs = set(self.gtfs_by_ref.keys())

        return osm_refs & gtfs_refs

    def validate(self):
        self.find_inconsistent_refs()
        self.check_distance()

    def check_distance(self, max_distance=50):
        max_distance = max_distance / 1000
        for ref in self.get_common_refs():
            osm_stop = self.osm_by_ref[ref]
            gtfs_stop = self.gtfs_by_ref[ref]

            dist = haversine((osm_stop.lat, osm_stop.lon),
                             (gtfs_stop.lat, gtfs_stop.lon))

            if dist >= max_distance:
                issue = NodesTooFarIssue(osm_stop, gtfs_stop, dist * 1000)
                self.issues.append(issue)

    def find_inconsistent_refs(self):
        gtfs = set(self.gtfs_by_ref.keys())
        osm = set(self.osm_by_ref.keys())

        missing_stops = gtfs - osm
        for stop_ref in missing_stops:
            issue = OsmStopMissingIssue(self.gtfs_by_ref[stop_ref])
            self.issues.append(issue)

        for stop_ref in osm - gtfs:
            issue = OsmStopWithUnknownRefIssue(self.osm_by_ref[stop_ref])
            self.issues.append(issue)
