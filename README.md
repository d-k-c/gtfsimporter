# Extract Bus Routes from GTFS dataset


## About this script

Public Transport Agencies provide data about bus routes, trips, and stops. Most
of the bus routes are incomplete in Open Street Map, this script can help fill
the gaps by exporting missing stops and bus routes in JOSM compatible format.
In JOSM, stops and routes should be reviewed manually before being uploaded.

## Set up

A `pipenv` environment is provided. If you have `pipenv` available on your
machine, type `pipenv sync` to install required dependencies. Otherwise, you can
install the dependencies yourself:
- haversine: a convenient module to compute the distance between two GPS
  coordinates
- overpy: module used to fetch results with the Overpass API
- requests: to query manually Overpass API and cache interesting data

The main entrypoint is gtfsimporter/main.py. Run `pipenvrun python -m
gtfsimporter.main --help` to get a list of available commands.

## Limitations

- When parsing GTFS data, only the longest trip for each direction is kept.
  Sometimes, shorter or different trips exist because some buses only run on a
  part of the line, or stop at different places depending on the time of day.
- When creating bus routes, this program expects bus stops to be already present
  in OpenStreetMap. This is purely to limit the size of each change, to make
  review easier.
- Route relations created by this program don't contain ways.

## Helper Makefile

The usual way to interact with this program is to use its main entrypoint:
main.py. But a Makefile is also provided to help interacting with known GTFS
data providers. For known providers, the Makefile will fetch GTFS archive, unzip
it, and wrap gtfsimporter commands for convenience. For instance, the `STM
(Société de Transport de Montréal` is a known provider, so you can just use
`make stm-export-routes` and it will do everything for you. Use `make help` for
more info.

The first run can be quite long because GTFS data are fully parsed to generate
stops and routes lists. Cache files are then generated to make following
invocations faster.

## TL;DR

How do I setup this project?
- `pipenv sync`

I want to generate stops
- `make stm-export-stops`

I want to see the route for line 10 of the STM network, what should I do?
- `make stm-export-route route=10 # result is in work/stm/route_10.osm`

Actually, I want all routes
- `make stm-export-routes # result is in work/stm/routes.osm`

Sorry, I meant only *missing* routes
- `make stm-export-routes-missing`

Route 10 has changed, what can I do?
- `make stm-update-route route=10`

I want to update my local version of OSM data
- `make stm-clean-cache-osm # on following runs, cache will be re-generated`
