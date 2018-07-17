= Extract Bus Routes from STM dataset

Source Website: http://www.stm.info/fr/a-propos/developpeurs


== About this script

The STM provides data about bus routes, trips, and stops. Most of the bus
routes are incomplete in Open Street Map, this script can help fill the gaps.

== What does it do?

`build_route` takes a route number as parameter. With that, it generates a list
of all the bus trips that are identified by this route number in the STM
dataset, and print them with the following format:

`GPS coordinates of the bus stop * stop code * stop name`

Usually, for a given route number you'll get two trips, one for each direction.
For some bus routes, you'll get more trips. Reasons could be that some buses
only serve a part of the line, or that some stops are different depending on the
time of the day.

== Set up

This project expects the dataset to be located in a directory called `data/`. To
automatically fetch the dataset from STM website, just type `make`. Otherwise,
you can download the archive your self and uncompress it in `data/`.


== TL;DR

- I want to see the route for line 10, what should I do?
- `make && ./build_route 10`
