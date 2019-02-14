

from ..osm.elements import Route, Schedule, Stop, StopTime, Trip

class SkipEntryError(Exception):
    pass

class StmAgency(object):

    agency_id = "STM"
    agency_name = "Société de transport de Montréal"

    def make_stop(self, row):
        return StmStop(row)

    def make_route(self, row):
        return StmRoute(row)

    def make_trip(self, row):
        return StmTrip(row)

    def make_stop_time(self, row):
        return StmStopTime(row)

class StmStop(Stop):

    def __init__(self, row):
        if "metro" in row["stop_url"]:
            raise SkipEntryError("This stop is for a metro line")

        stop_id = row["stop_id"]
        name = row["stop_name"]
        ref = row["stop_code"]
        lat = row["stop_lat"]
        lon = row["stop_lon"]

        super().__init__(name, ref, lon, lat, stop_id, None, None, None)


class StmRoute(Route):

    def __init__(self, row):
        if "metro" in row["route_url"]:
            raise SkipEntryError("This stop is for a metro line")

        route_id = row["route_id"]
        route_code = row["route_short_name"]
        route_name = row["route_long_name"]
        agency = row["agency_id"]

        super().__init__(route_id, route_code, route_name, agency, agency)


class StmTrip(Trip):

    def __init__(self, row):
        trip_id = row["trip_id"]
        route_id = row["route_id"]
        headsign = row["trip_headsign"]

        shape_id = row["shape_id"]

        super().__init__(trip_id, route_id, headsign, None, None, shape_id)

class StmStopTime(StopTime):

    def __init__(self, row):
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        stop_sequence = int(row["stop_sequence"])
        
        super().__init__(trip_id, stop_id, stop_sequence)

