
import os
import csv

from ..osm.elements import Route, Schedule, Stop, StopTime, Trip


class GTFSImporter():

    _STOPS_FILE = "stops.txt"
    _ROUTES_FILE = "routes.txt"
    _TRIPS_FILE = "trips.txt"
    _STOP_TIMES_FILE = "stop_times.txt"
    _SHAPES_FILE = "shapes.txt"

    def __init__(self, path):
        self.path = path

    def load_stops(self, schedule=None):
        if schedule is None:
            schedule = Schedule()

        path = os.path.join(self.path, self._STOPS_FILE)
        with open(path) as stopsfile:
            stopsreader = csv.DictReader(stopsfile)
            for row in stopsreader:
                if "metro" in row["stop_url"]:
                    continue

                stop_id = row["stop_id"]
                name = row["stop_name"]
                ref = row["stop_code"]
                lat = row["stop_lat"]
                lon = row["stop_lon"]

                stop = Stop(name, ref, lon, lat, stop_id, None, None, None)
                schedule.add_stop(stop)

        return schedule

    def load_routes(self, schedule, routes_of_interest):
        path = os.path.join(self.path, self._ROUTES_FILE)
        with open(path) as routesfile:
            routesreader = csv.DictReader(routesfile)
            for row in routesreader:
                if "metro" in row["route_url"]:
                    continue

                route_id = row["route_id"]
                route_code = row["route_short_name"]
                route_name = row["route_long_name"]
                agency = row["agency_id"]

                if (routes_of_interest is not None and route_id in routes_of_interest) or \
                    routes_of_interest is None:
                    route = Route(route_id, route_code, route_name, agency, agency)
                    schedule.add_route(route)

    def load_trips(self, schedule):
        path = os.path.join(self.path, self._TRIPS_FILE)
        with open(path) as tripsfile:
            tripsreader = csv.DictReader(tripsfile)
            for row in tripsreader:
                trip_id = row["trip_id"]
                route_id = row["route_id"]
                headsign = row["trip_headsign"]

                shape_id = row["shape_id"]

                route = schedule.get_route(route_id, None)
                if route:
                    network = route.network if route.network else None
                    operator = route.operator if route.operator else None
                    trip = Trip(trip_id, route, headsign, network, operator)
                    schedule.add_trip(trip, shape_id)

    def load_stop_times(self, schedule):
        path = os.path.join(self.path, self._STOP_TIMES_FILE)

        with open(path) as timefile:
            timereader = csv.reader(timefile)
            row = next(timereader)

            for row in timereader:
                trip_id, stop_id, stop_sequence = row[0], row[3], row[4]
                stop_sequence = int(stop_sequence)

                trip = schedule.get_trip(trip_id, None)
                if trip is not None:
                    stop = schedule.get_stop(stop_id)
                    stop_time = StopTime(stop, stop_sequence)

                    schedule.add_stop_time(trip, stop_time)

    def load_shapes(self, schedule):
        path = os.path.join(self.path, self._SHAPES_FILE)

        with open(path) as shapefile:
            shapereader = csv.DictReader(shapefile)
            for row in shapereader:
                shape_id = row["shape_id"]
                lat = row["shape_pt_lat"]
                lon = row["shape_pt_lon"]
                seq = int(row["shape_pt_sequence"])

                schedule.add_shape_point(shape_id, lat, lon, seq)


    def load(self, route_ids_of_interest=None, unique_trips=False):
        schedule = Schedule()
        self.load_stops(schedule)
        self.load_routes(schedule, route_ids_of_interest)
        self.load_trips(schedule)
        self.load_stop_times(schedule)

        if unique_trips:
            schedule.remove_duplicated_trips()

        #self.load_shapes(schedule)

        return schedule
