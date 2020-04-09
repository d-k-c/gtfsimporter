

from ..gtfs.elements import GtfsRoute, GtfsStop, GtfsStopTime, GtfsTrip

from .exceptions import SkipEntryError

class StlAgency(object):

    id = "STL"
    name = "Societe de transport de Laval"

    def make_stop(self, row):
        return StlStop(row)

    def make_route(self, row):
        raise NotImplementedError("Only export-stops currently is supported")

    def make_trip(self, row):
        raise NotImplementedError("Only export-stops currently is supported")

    def make_stop_time(self, row):
        raise NotImplementedError("Only export-stops currently is supported")

class StlStop(GtfsStop):

    def __init__(self, row):
        stop_id = row["stop_id"]
        name = row["stop_name"]
        ref = row["stop_code"]
        lat = row["stop_lat"]
        lon = row["stop_lon"]

        # names are suffixed by the stop reference in bracket, eliminate that
        idx = name.rfind(" [")
        if idx != -1:
            name = name[:idx]

        # some entries have multiple consecutive whitespaces
        name = name.replace("  ", " ")

        super().__init__(name, ref, lon, lat, stop_id, None, None, None)

