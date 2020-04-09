

from .elements import GtfsRoute, Schedule, GtfsStop, GtfsStopTime, GtfsTrip

from .exceptions import SkipEntryError

class StmAgency(object):

    id = "STM"
    name = "Société de transport de Montréal"

    def make_stop(self, row):
        return make_stm_stop(row)

    def make_route(self, row):
        return make_stm_route(row)

    def make_trip(self, row):
        return make_stm_trip(row)

    def make_stop_time(self, row):
        return StmStopTime(row)

def make_stm_stop(row):
    if row["stop_id"].startswith("STATION_M"):
        raise SkipEntryError("This stop is for a metro station")
    if "STATION_M" in row["parent_station"]:
        raise SkipEntryError("This stop is for a metro line")

    stop_id = row["stop_id"]
    name = row["stop_name"]
    ref = row["stop_code"]
    lat = row["stop_lat"]
    lon = row["stop_lon"]

        
    return GtfsStop(stop_id, lat, lon, name, ref)


class StmGtfsRoute(GtfsRoute):

    extra_locales = ['en']

    @property
    def name(self):
        return self.get_name()

    def get_name(self, lang='fr'):
        if lang == 'fr':
            return "Bus {} : {}".format(self.code, self._name)
        elif lang == 'en':
            return "Bus {}: {}".format(self.code, self._name)


def make_stm_route(row):
    if "metro" in row["route_url"]:
        raise SkipEntryError("This stop is for a metro line")

    route_id = row["route_id"]
    route_code = row["route_short_name"]
    route_name = row["route_long_name"]
    agency = row["agency_id"]

    return StmGtfsRoute(route_id, route_code, route_name, agency, agency)




class StmGtfsTrip(GtfsTrip):

    extra_locales = ['en']

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

    def get_direction(self, lang='fr'):
        if self.headsign[-2] == "-":
            direction = self.headsign[-1]
            return self.directions[lang][direction]

    @property
    def name(self):
        return self.get_name()

    def get_name(self, lang='fr'):
        return "{} {}".format(
                self.route.get_name(lang),
                self.get_direction(lang))

def make_stm_trip(row):
    trip_id = row["trip_id"]
    route_id = row["route_id"]
    headsign = row["trip_headsign"]

    shape_id = row["shape_id"]

    return StmGtfsTrip(trip_id, route_id, headsign, shape_id=shape_id)



class StmStopTime(GtfsStopTime):

    def __init__(self, row):
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        stop_sequence = int(row["stop_sequence"])
        
        super().__init__(trip_id, stop_id, stop_sequence)

