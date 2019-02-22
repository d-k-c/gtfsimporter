
import os
import csv

from . import agencies
from .exceptions import SkipEntryError
from ..osm.elements import Schedule

class GTFSImporter():

    _AGENCY_FILE = "agency.txt"
    _STOPS_FILE = "stops.txt"
    _ROUTES_FILE = "routes.txt"
    _TRIPS_FILE = "trips.txt"
    _STOP_TIMES_FILE = "stop_times.txt"
    _SHAPES_FILE = "shapes.txt"

    def __init__(self, path):
        self.path = path

        agency = self.find_agency()
        self.agency = agency()


    def find_agency(self):
        """
        Find agency class capable of handling the targeted GTFS dataset.

        This function reads the first entry of agency.txt and will try to find
        the corresponding agency class capable of handling this dataset. Agency
        classes are listed in the `agencies` variable of gtfs/__init__.py.
        """
        path = os.path.join(self.path, self._AGENCY_FILE)
        with open(path, encoding="utf-8-sig") as agencyfile:
            agencyreader = csv.DictReader(agencyfile)
            row = next(agencyreader)

        agency_id = row["agency_id"]
        agency_name = row["agency_name"]
        for agency in agencies:
            if agency.id == agency_id and agency.name == agency_name:
                return agency
        else:
            raise NotImplementedError(f"Agency '{agency_name}' is not supported yet")


    def load_stops(self, schedule=None):
        if schedule is None:
            schedule = Schedule()

        path = os.path.join(self.path, self._STOPS_FILE)
        with open(path, encoding="utf-8-sig") as stopsfile:
            stopsreader = csv.DictReader(stopsfile)
            for row in stopsreader:
                try:
                    stop = self.agency.make_stop(row)
                    schedule.add_stop(stop, deduplicate=True)
                except SkipEntryError:
                    continue

        return schedule

    def load_routes(self, schedule, routes_of_interest):
        path = os.path.join(self.path, self._ROUTES_FILE)
        with open(path, encoding="utf-8-sig") as routesfile:
            routesreader = csv.DictReader(routesfile)
            for row in routesreader:
                try:
                    route = self.agency.make_route(row)
                except SkipEntryError:
                    continue

                # We keep only routes if we are specifically interested in them,
                # or all the routes if no specific routes have been specified
                if (routes_of_interest is not None and route.id in routes_of_interest) or \
                    routes_of_interest is None:
                    schedule.add_route(route)

    def load_trips(self, schedule):
        path = os.path.join(self.path, self._TRIPS_FILE)
        with open(path, encoding="utf-8-sig") as tripsfile:
            tripsreader = csv.DictReader(tripsfile)
            for row in tripsreader:
                try:
                    trip = self.agency.make_trip(row)
                except SkipEntryError:
                    continue

                # route will exist only if it was deemed of interest by load_routes
                route = schedule.get_route(trip.route_id, None)
                if route:
                    trip.add_route(route)
                    route.add_trip(trip)
                    schedule.add_trip(trip)

    def load_stop_times(self, schedule):
        path = os.path.join(self.path, self._STOP_TIMES_FILE)

        with open(path, encoding="utf-8-sig") as timefile:
            timereader = csv.DictReader(timefile)
            row = next(timereader)

            for row in timereader:
                try:
                    stop_time = self.agency.make_stop_time(row)
                except SkipEntryError:
                    continue

                # get_trip will return an entry only if this trip belongs to a route
                # we are interested in in the first place
                trip = schedule.get_trip(stop_time.trip_id, None)
                if trip is not None:
                    stop = schedule.get_stop(stop_time.stop_id)
                    stop_time.set_stop(stop)

                    schedule.add_stop_time(trip, stop_time)

    def load_shapes(self, schedule):
        path = os.path.join(self.path, self._SHAPES_FILE)

        with open(path, encoding="utf-8-sig") as shapefile:
            shapereader = csv.DictReader(shapefile)
            for row in shapereader:
                shape_id = row["shape_id"]
                lat = row["shape_pt_lat"]
                lon = row["shape_pt_lon"]
                seq = int(row["shape_pt_sequence"])

                schedule.add_shape_point(shape_id, lat, lon, seq)


    def load(self, route_ids_of_interest=None, unique_trips=False,
             shapes=False):
        schedule = Schedule()
        self.load_stops(schedule)
        self.load_routes(schedule, route_ids_of_interest)
        self.load_trips(schedule)
        self.load_stop_times(schedule)

        if unique_trips:
            schedule.remove_duplicated_trips()

        if shapes:
            self.load_shapes(schedule)

        return schedule
