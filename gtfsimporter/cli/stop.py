
from .loader import GtfsLoader, SchedulesLoader

from ..conflation.stops import StopConflator
from ..osm.elements import OsmStop
from ..osm.josm import JosmDocument

class StopParser(object):

    @classmethod
    def generate_stops(cls, args):
        gtfs_schedule = GtfsLoader.load_only_stops(args)

        if args.stop_ref is None:
            osm_stops = [OsmStop.fromGtfs(s) for s in gtfs_schedule.stops]
            wanted_refs = None
        else:
            wanted_refs = args.stop_ref.split(",")
            osm_stops = []
            for stop in gtfs_schedule.stops:
                for ref in stop.refs:
                    if ref in wanted_refs:
                        osm_stop = OsmStop.fromGtfs(stop)
                        wanted_refs.remove(ref)
                        osm_stops.append(osm_stop)

        doc = JosmDocument()
        doc.export_stops(osm_stops)
        with open(args.output_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)

        if wanted_refs:
            print("The following refs have not been found and were not exported:")
            print("\t", " ".join(wanted_refs))

    @classmethod
    def generate_missing_stops(cls, args):
        gtfs, osm = SchedulesLoader.load_only_stops(args)

        conflator = StopConflator(gtfs.stops, osm.stops)
        missing_stops = conflator.stops_with_refs_only_in_gtfs()

        missing_osm_stops = []
        partial_ref_stops = {}

        for stop in missing_stops:
            if len(stop.refs) > 1:
                matching_stops = conflator.find_matching_osm_stops(stop)
                if matching_stops:
                    partial_ref_stops[stop] = matching_stops
                    continue

            osm_stop = OsmStop.fromGtfs(stop)
            missing_osm_stops.append(osm_stop)

        if partial_ref_stops:
            print("Following GTFS stops have multiple refs and some exist in OSM. "
                  "OSM stops must be updated manually:")
        for g_stop, osm_stops in partial_ref_stops.items():
            print(f"\tGTFS Stop: refs={g_stop.refs}, name={g_stop.name}")
            print("\tOSM Stops:")
            for osm_stop in osm_stops:
                print(f"\t           refs={osm_stop.refs}, name={osm_stop.name}")

        doc = JosmDocument()
        doc.export_stops(missing_osm_stops)
        with open(args.output_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)



    @classmethod
    def setup_arguments(cls, parser, subparsers):

        stop_parser = subparsers.add_parser(
            "stops",
            help="stop-related submenu")

        stop_subparsers = stop_parser.add_subparsers()

        # COMMAND: stop export
        stop_export_parser = stop_subparsers.add_parser(
            "export",
            help="Export stops from the GTFS dataset")
        stop_export_parser.add_argument(
            "--stop-ref",
            help="List of stop references to export, comma-separated "
                 ", eg. --stop-ref 1234,5789")
        stop_export_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated stop list")

        GtfsLoader.setup_arguments(stop_export_parser, subparsers)
        stop_export_parser.set_defaults(func=StopParser.generate_stops)

        # COMMAND: stop export-missing
        stop_missing_parser = stop_subparsers.add_parser(
            "export-missing",
            help="Export stops missing in OSM")
        stop_missing_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated stop list")

        SchedulesLoader.setup_arguments(stop_missing_parser, subparsers)
        stop_missing_parser.set_defaults(func=StopParser.generate_missing_stops)
