
from haversine import haversine

class StopConflator(object):

    def __init__(self, gtfs_stops, osm_stops):
        self.gtfs_stops = gtfs_stops
        self.osm_stops  = osm_stops

    def only_in_gtfs(self):
        osm_refs = self.get_all_refs(self.osm_stops)

        missing_stops = []
        for gtfs_stop in self.gtfs_stops:
            for ref in gtfs_stop.refs:
                if ref not in osm_refs:
                    missing_stops.append(gtfs_stop)

        return missing_stops

    def get_all_refs(self, stop_list):
        refs = []
        for stop in stop_list:
            refs.extend(stop.refs)

        return refs

    def conflate(self, gtfs_stops, osm_stops):
        modified_stops = self.compare_names_by_ref(self.gtfs_by_ref, self.osm_by_ref)

        return modified_stops

    def missing_stops_in_osm(self):
        gtfs = set(self.gtfs_by_ref.keys())
        osm = set(self.osm_by_ref.keys())

        missing_stops = gtfs - osm
        return [self.gtfs_by_ref[ref] for ref in missing_stops]

    def compare_names_by_ref(self, gtfs_by_ref, osm_by_ref):
        modified_stops = []

        # iterate over all items in GTFS stops
        for ref, gtfs_stop in gtfs_by_ref.items():

            # if this ref exists in existing OSM dataset
            # check both name are the same, otherwise do an update
            if ref in osm_by_ref:
                osm_stop = osm_by_ref[ref]
                if gtfs_stop.name != osm_stop.name:
                    osm_stop.name = gtfs_stop.name
                    modified_stops.append(osm_stop)

        return modified_stops

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

        #for stop_ref in osm - gtfs:
        #    issue = OsmStopWithUnknownRefIssue(self.osm_by_ref[stop_ref])
        #    self.issues.append(issue)
