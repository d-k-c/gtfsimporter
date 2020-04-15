
import pickle

from .loader import DatadirGtfsLoader, GtfsLoader, XmlOsmLoader
from ..osm.overpass import OverpassImporter

class CacheParser(object):

    @classmethod
    def generate_gtfs_pickle(cls, args):
        if args.gtfs_datadir is None:
            print("--gtfs-datadir must be specified")
            return

        gtfs_schedule = DatadirGtfsLoader.load_gtfs_datadir(args.gtfs_datadir)

        with open(args.output_file, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(gtfs_schedule, f, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def generate_osm_xml(cls, args):

        gtfs_schedule = GtfsLoader.load_only_stops(args)

        bbox = gtfs_schedule.get_bounding_box(1000)
        loader = OverpassImporter(bbox)
        loader.generate_cache_routes(args.output_file)

    @classmethod
    def generate_osm_pickle(cls, args):
        try:
            # This will raise an exception if --osm-xml is not set
            osm_schedule = XmlOsmLoader.load_from_args(args)
        except:
            # No XML case, then load GTFS to get the bounding box
            # to then query OSM and build the schedule
            # This will potentially also raise an exception
            try:
                gtfs_schedule = GtfsLoader.load_from_args(args)

                bbox = gtfs_schedule.get_bounding_box(1000)
                loader = OverpassImporter(bbox)

                osm_schedule = Schedule()
                loader.load_routes(osm_schedule, None)
            except:
                raise AttributeError(
                        "--gtfs-datadir, --gtfs-pickle, or --osm-xml must be specified")

        with open(args.output_file, 'wb') as f:
            pickle.dump(osm_schedule, f, pickle.HIGHEST_PROTOCOL)


    @classmethod
    def setup_arguments(cls, top_level_parser, top_level_subparsers):
        # setup GtfsLoader as we need to load it
        cache_parser = top_level_subparsers.add_parser(
            "cache",
            help="Cache-related submenu")

        cache_subparsers = cache_parser.add_subparsers()

        # COMMAND: cache pickle-gtfs
        pickle_gtfs_parser = cache_subparsers.add_parser(
            "pickle-gtfs",
            help="Pickle GTFS dataset to speed up next runs")
        # TODO: reimplement these features
        #pickle_gtfs_parser.add_argument(
        #    "--without-routes",
        #    action="store_false",
        #    help="Skip routes, generating a stop-only cache")
        #pickled_gtfs_parser.add_argument(
        #    "--with-shapes",
        #    action="store_true",
        #    help="include routes' shapes, skipped otherwise")
        pickle_gtfs_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store the generated pickled file")

        DatadirGtfsLoader.setup_arguments(pickle_gtfs_parser, top_level_subparsers,
                                          required=True)
        pickle_gtfs_parser.set_defaults(func=CacheParser.generate_gtfs_pickle)


        # COMMAND: cache query-osm
        query_osm_parser = cache_subparsers.add_parser(
            "query-osm",
            help="query OpenStreetMap and store result in an XML file, to limit API requests")
        query_osm_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store query result from Overpass API")

        GtfsLoader.setup_arguments(query_osm_parser, top_level_subparsers)
        query_osm_parser.set_defaults(func=CacheParser.generate_osm_xml)


        # COMMAND: cache pickle-osm
        pickle_osm_parser = cache_subparsers.add_parser(
            "pickle-osm",
            help="Pickle OSM data to speed up next runs")
        pickle_osm_parser.add_argument(
            "--output-file",
            required=True,
            help="File to store the generated pickled file")

        group = pickle_osm_parser.add_mutually_exclusive_group(required=True)
        GtfsLoader.setup_arguments(group, top_level_subparsers, required=False)
        XmlOsmLoader.setup_arguments(group, top_level_subparsers)
        pickle_osm_parser.set_defaults(func=CacheParser.generate_osm_pickle)
