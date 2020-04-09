
from .loader import GtfsLoader

from ..osm.elements import OsmStop
from ..osm.josm import JosmDocument

class StopParser(object):

    @classmethod
    def generate_stops(cls, args):
        gtfs_schedule = GtfsLoader.load_from_args(args)

        osm_stops = [OsmStop.fromGtfs(s) for s in gtfs_schedule.stops]

        doc = JosmDocument()
        doc.export_stops(osm_stops, False)
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
            help="List of stop references to export, semicolon-separated "
                 ", eg. --stop-ref=1234;5789")
        stop_export_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store generated stop list")

        GtfsLoader.setup_arguments(stop_export_parser, subparsers)
        stop_export_parser.set_defaults(func=StopParser.generate_stops)
