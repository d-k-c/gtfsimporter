# Extract Bus Routes from GTFS dataset


## About this script

Public Transport Agencies provide data about bus routes, trips, and stops. Most
of the bus routes are incomplete in Open Street Map, this script can help fill
the gaps by exporting missing stops and bus routes in JOSM compatible format.
In JOSM, stops and routes can be reviewed manually before being uploaded.

## What does it do?

It takes a route number as parameter. With that, it generates a list of all the
bus trips that are identified by this route number in the GTFS dataset, and
generate the route in a format that can be loaded by JOSM. You are strongly
advised to manually validate the generated output before uploading it to
OpenStreetMap.

Usually, for a given route number you'll get two trips, one for each direction.
For some bus routes, you'll get more trips. Reasons could be that some buses
only serve a part of the line, or that some stops are different depending on the
time of the day. Currently, only the longest trip of each route is generated in
the output file.

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

- When creating bus routes, this program expects bus stops to be already present
  in OpenStreetMap. If stops are missing, route creation will fail. If you use
  export-routes, output file will contain only routes for which stops were found
  in OSM.
- Route relations create this program don't contain ways, but one can use the
  --with-shapes switch to create a way that matches the shape of the route. This
  shape can be used to add ways to the route relation.

## Helper Makefile

The usual way to interact with this program is to use its main entrypoint:
main.py. But a Makefile is also provided to help interacting with known GTFS
data providers. For known providers, the Makefile will fetch GTFS archive, unzip
it, and wrap gtfsimporter commands for convenience. For instance, the `STM
(Société de Transport de Montréal` is a known provider, so you can just use
`make stm-export-routes` and it will do everything for you. Use `make help` for
more info.

Note that it generates a cache file to limit queries against the Overpass API.
This cache contains information about bus stops, so if bus stops change in OSM,
you need to delete it manually (for now) to force its renewal. For instance to
clear cache for the STM: `make stm-clean-stops-cache`

## TL;DR

How do I setup this project?
- `pipenv sync`

I want to generate stops
- `make stm-export-stops`

I want to see the route for line 10 of the STM network, what should I do?
- `make stm-export-route route=10 # result is in work/stm/route_10.osm`

Actually, I want all routes
- `make stm-export-routes # result is in work/stm/routes.osm`

