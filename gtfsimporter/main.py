
import sys
import argparse

from .cli.cache import CacheParser
from .cli.route import RouteParser
from .cli.stop import StopParser

def parse_command_line():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    CacheParser.setup_arguments(parser, subparsers)
    StopParser.setup_arguments(parser, subparsers)
    RouteParser.setup_arguments(parser, subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    parse_command_line()
    sys.exit(0)

