

from ..osm.elements import Route, Schedule, Stop, StopTime, Trip

from .exceptions import SkipEntryError

class StmAgency(object):

    id = "STM"
    name = "Société de transport de Montréal"

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


    def get_name(self, lang='fr'):
        if lang == 'fr':
            return "Bus {} : {}".format(self.code, self.name)
        elif lang == 'en':
            return "Bus {}: {}".format(self.code, self.name)



class StmTrip(Trip):

    directions = {
        'fr': {
            'N': "Nord",
            'S': "Sud",
            'E': "Est",
            'O': "Ouest"
        },
        'en': {
            'N': "North",
            'S': "South",
            'E': "East",
            'O': "West"
        }
    }

    def __init__(self, row):
        trip_id = row["trip_id"]
        route_id = row["route_id"]
        headsign = row["trip_headsign"]

        shape_id = row["shape_id"]

        super().__init__(trip_id, route_id, headsign, None, None, shape_id)


    def get_direction(self, lang='fr'):
        if self.headsign[-2] == "-":
            direction = self.headsign[-1]
            return self.directions[lang][direction]

    def get_name(self, lang='fr'):
        return "{} {}".format(
                self.route.get_name(lang),
                self.get_direction(lang))


class StmStopTime(StopTime):

    def __init__(self, row):
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        stop_sequence = int(row["stop_sequence"])
        
        super().__init__(trip_id, stop_id, stop_sequence)

