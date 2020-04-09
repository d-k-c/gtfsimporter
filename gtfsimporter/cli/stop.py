
from .loader import GtfsLoader

from ..osm.elements import OsmStop
from ..osm.josm import JosmDocument

class StopParser(object):

    @classmethod
    def generate_stops(cls, args):
        gtfs_schedule = GtfsLoader.load_from_args(args)

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
        doc.export_stops(osm_stops, False)
        with open(args.output_file, 'w', encoding="utf-8") as output_file:
            doc.write(output_file)

        if wanted_refs:
            print("The following refs have not been found and were not exported:")
            print("\t", " ".join(wanted_refs))


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
