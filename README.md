# Extract Bus Routes from STM dataset

Source Website: http://www.stm.info/fr/a-propos/developpeurs


## About this script

The STM provides data about bus routes, trips, and stops. Most of the bus
routes are incomplete in Open Street Map, this script can help fill the gaps.

## What does it do?

It takes a route number as parameter. With that, it generates a list
of all the bus trips that are identified by this route number in the STM
dataset, and generate the route in a format that can be loaded by JOSM. You
are strongly advised to manually validate the generated output before uploading
it to OpenStreetMap.

Usually, for a given route number you'll get two trips, one for each direction.
For some bus routes, you'll get more trips. Reasons could be that some buses
only serve a part of the line, or that some stops are different depending on the
time of the day.

## Set up

To automatically fetch the dataset from STM website, just type `make` and it
will download and uncompress the latest STM GTFS zip and uncompress it to
`data`.

A `pipenv` environment is provided. If you have `pipenv` available on your
machine, type `pipenv sync` to install required dependencies. Otherwise, you can
install the dependencies yourself:
- haversine: a convenient module to compute the distance between two GPS
  coordinates
- overpy: module used to fetch results with the Overpass API


## TL;DR

- I want to see the route for line 10 of the STM network, what should I do?
- `make stm-extract`
- `pipenv sync`
- `pipenv run python -m gtfsimporter.main --gtfs-datadir work/stm/gtfs export-route --dest line_10.osm 10`
