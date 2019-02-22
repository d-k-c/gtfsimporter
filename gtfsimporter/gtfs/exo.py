

from ..osm.elements import Route, Schedule, Stop, StopTime, Trip

from .exceptions import SkipEntryError

class ExoBaseAgency(object):

    def make_stop(self, row):
        return ExoStop(row)

    def make_route(self, row):
        return ExoRoute(row)

    def make_trip(self, row):
        return ExoTrip(row)

    def make_stop_time(self, row):
        return ExoStopTime(row)

class ExoChamblyAgency(ExoBaseAgency):
    id = "CITCRC"
    name = "exo-Chambly-Richelieu-Carignan"

class ExoHautSaintLaurentAgency(ExoBaseAgency):
    id = "CITHSL"
    name = "exo-Haut-Saint-Laurent"

class ExoLaurentidesAgency(ExoBaseAgency):
    id = "CITLA"
    name = "exo-Laurentides"

class ExoPresquIleAgency(ExoBaseAgency):
    id = "CITPI"
    name = "exo-La Presqu'île"

class ExoRichelainAgency(ExoBaseAgency):
    id = "CITLR"
    name = "exo-Le Richelain"

class ExoRoussillonAgency(ExoBaseAgency):
    id = "CITROUS"
    name = "exo-Roussillon"

class ExoSorelAgency(ExoBaseAgency):
    id = "CITSV"
    name = "exo-Sorel-Varennes"

class ExoSudOuestAgency(ExoBaseAgency):
    id = "CITSO"
    name = "exo-Sud-Ouest"

class ExoValleeRichelieuAgency(ExoBaseAgency):
    id = "CITVR"
    name = "exo-Vallée du Richelieu"

class ExoAssomptionAgency(ExoBaseAgency):
    id = "MRCLASSO"
    name = "exo-L'Assomption"

class ExoTerrebonneAgency(ExoBaseAgency):
    id = "MRCLM"
    name = "exo-Terrebonne-Mascouche"

class ExoSteJulieAgency(ExoBaseAgency):
    id = "OMITSJU"
    name = "exo-Sainte-Julie"


class ExoStop(Stop):

    def __init__(self, row):
        stop_id = row["stop_id"]
        name = row["stop_name"]
        ref = row["stop_code"]
        lat = row["stop_lat"]
        lon = row["stop_lon"]

        super().__init__(name, ref, lon, lat, stop_id, None, None, None)


class ExoRoute(Route):

    def __init__(self, row):
        try:
            route_id = row["route_id"]
            route_code = row["route_short_name"]
            route_name = row["route_long_name"]
            agency = row["agency_id"]
        except:
            print(row)

        super().__init__(route_id, route_code, route_name, agency, agency)


    def get_name(self):
        return "Bus {} : {}".format(self.code, self.name)



class ExoTrip(Trip):

    def __init__(self, row):
        trip_id = row["trip_id"]
        route_id = row["route_id"]
        headsign = row["trip_headsign"]

        shape_id = row["shape_id"]

        super().__init__(trip_id, route_id, headsign, None, None, shape_id)


    def get_name(self, lang='fr'):
        return "Bus {} : {}".format(
                self.route.id, self.headsign)


class ExoStopTime(StopTime):

    def __init__(self, row):
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        stop_sequence = int(row["stop_sequence"])

        super().__init__(trip_id, stop_id, stop_sequence)
