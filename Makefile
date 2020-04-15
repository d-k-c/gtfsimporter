
OUTPUT := $(CURDIR)/work
GTFS_IMPORTER := pipenv run python -m gtfsimporter.main

$(OUTPUT)/%/.stamp_downloaded:
	@mkdir -p $($(PROVIDER)_WORK_DIR)
	@echo "Creating $($(PROVIDER)_WORK_DIR)"
	@wget $($(PROVIDER)_REMOTE_URL)/$($(PROVIDER)_ARCHIVE) \
		-O $($(PROVIDER)_WORK_DIR)/$($(PROVIDER)_ARCHIVE)
	@touch $@

$(OUTPUT)/%/.stamp_extracted:
	@unzip $($(PROVIDER)_WORK_DIR)/$($(PROVIDER)_ARCHIVE) \
		-d $($(PROVIDER)_UNPACK_DIR)
	@touch $@

$(OUTPUT)/%/gtfs.pickle:
	@echo "Generating GTFS cache: $@"
	@echo "It can take several minutes to complete"
	$(GTFS_IMPORTER) \
		cache pickle-gtfs \
			--gtfs-datadir $($(PROVIDER)_UNPACK_DIR) \
			--output-file $@

$(OUTPUT)/%/osm.xml:
	@echo "Generating OSM XML cache with latest OSM data"
	$(GTFS_IMPORTER) \
		cache query-osm \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--output-file $@

$(OUTPUT)/%/osm.pickle:
	@echo "Generating OSM pickle file: $@"
	$(GTFS_IMPORTER) \
		cache pickle-osm \
			--osm-xml $($(PROVIDER)_OSM_XML_FILE) \
			--output-file $@

$(OUTPUT)/%/stops.osm:
	$(GTFS_IMPORTER) \
		stops export \
			--gtfs-datadir $($(PROVIDER)_UNPACK_DIR) \
			--output-file $@

$(OUTPUT)/%/missing_stops:
	$(GTFS_IMPORTER) \
		stops export-missing \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--osm-pickle $($(PROVIDER)_OSM_PICKLE_FILE) \
			--output-file $@

$(OUTPUT)/%/routes.osm:
	$(GTFS_IMPORTER) \
		routes export \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--osm-pickle $($(PROVIDER)_OSM_PICKLE_FILE) \
			--output-file $@

$(OUTPUT)/%/missing_routes.osm:
	$(GTFS_IMPORTER) \
		routes export-missing \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--osm-pickle $($(PROVIDER)_OSM_PICKLE_FILE) \
			--output-file $@


# Make is not fond of two "%" in a target. Work around it
# by dropping the prefix
route_%.osm:
ifeq ($(route),)
	$(error "Unspecified route, expecting 'route=<id>' as parameter")
endif
	$(GTFS_IMPORTER) \
		routes export \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--osm-pickle $($(PROVIDER)_OSM_PICKLE_FILE) \
			--route-ref $(route) \
			--output-file $@

update_route_%.osm:
ifeq ($(route),)
	$(error "Unspecified route, expecting 'route=<id>' as parameter")
endif
	$(GTFS_IMPORTER) \
		routes update \
			--gtfs-pickle $($(PROVIDER)_GTFS_PICKLE_FILE) \
			--osm-pickle $($(PROVIDER)_OSM_PICKLE_FILE) \
			--route-ref $(route) \
			--output-file $@


define gtfs-providers

# download and extract
$(2)_WORK_DIR		= $(OUTPUT)/$(1)
$(2)_UNPACK_DIR 	= $$($(2)_WORK_DIR)/gtfs
# cache (picke and xml)
$(2)_GTFS_PICKLE_FILE 	= $$($(2)_WORK_DIR)/gtfs.pickle
$(2)_OSM_XML_FILE 	= $$($(2)_WORK_DIR)/osm.xml
$(2)_OSM_PICKLE_FILE 	= $$($(2)_WORK_DIR)/osm.pickle
# stops
$(2)_STOPS_FILE 	= $$($(2)_WORK_DIR)/stops.osm
$(2)_MISSING_STOPS_FILE = $$($(2)_WORK_DIR)/missing_stops.osm
# routes
$(2)_ROUTES_FILE 	= $$($(2)_WORK_DIR)/routes.osm
$(2)_MISSING_ROUTES_FILE = $$($(2)_WORK_DIR)/missing_routes.osm

# target for a single route
$(2)_TARGET_ROUTE    = $$($(2)_WORK_DIR)/route_$(route).osm
$(2)_TARGET_ROUTE_UPDATE = $$($(2)_WORK_DIR)/update_route_$(route).osm

$(2)_TARGET_DOWNLOAD	= $$($(2)_WORK_DIR)/.stamp_downloaded
$(2)_TARGET_EXTRACT	= $$($(2)_WORK_DIR)/.stamp_extracted
$(2)_TARGET_PICKLE_GTFS = $$($(2)_GTFS_PICKLE_FILE)
$(2)_TARGET_QUERY_OSM 	= $$($(2)_OSM_XML_FILE)
$(2)_TARGET_PICKLE_OSM  = $$($(2)_OSM_PICKLE_FILE)
$(2)_TARGET_STOPS    	= $$($(2)_STOPS_FILE)
$(2)_TARGET_STOPS_MISSING = $$($(2)_MISSING_STOPS_FILE)
$(2)_TARGET_ROUTES   	= $$($(2)_ROUTES_FILE)
$(2)_TARGET_ROUTES_MISSING = $$($(2)_MISSING_ROUTES_FILE)

$(1)-fetch: $$($(2)_TARGET_DOWNLOAD)

$(1)-extract: 			$$($(2)_TARGET_EXTRACT)
$$($(2)_TARGET_EXTRACT):	$$($(2)_TARGET_DOWNLOAD)

$(1)-pickle-gtfs:		$$($(2)_TARGET_PICKLE_GTFS)
$$($(2)_TARGET_PICKLE_GTFS):	$$($(2)_TARGET_EXTRACT)

$(1)-query-osm:			$$($(2)_TARGET_QUERY_OSM)
$$($(2)_TARGET_QUERY_OSM):	$$($(2)_TARGET_EXTRACT)

$(1)-pickle-osm:		$$($(2)_TARGET_PICKLE_OSM)
$$($(2)_TARGET_PICKLE_OSM):	$$($(2)_TARGET_QUERY_OSM)

$(1)-export-stops:		$$($(2)_TARGET_STOPS)
$$($(2)_TARGET_STOPS):		$$($(2)_TARGET_EXTRACT)

$(1)-export-stops-missing:	$$($(2)_TARGET_STOPS_MISSING)
$$($(2)_TARGET_STOPS_MISSING):	$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_QUERY_OSM)

$(1)-export-route:		$$($(2)_TARGET_ROUTE)
$$($(2)_TARGET_ROUTE):		$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_PICKLE_OSM)

$(1)-update-route:		$$($(2)_TARGET_ROUTE_UPDATE)
$$($(2)_TARGET_ROUTE_UPDATE):	$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_PICKLE_OSM)

$(1)-export-routes:		$$($(2)_TARGET_ROUTES)
$$($(2)_TARGET_ROUTES):		$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_PICKLE_OSM)

$(1)-export-routes-missing:	$$($(2)_TARGET_ROUTES_MISSING)
$$($(2)_TARGET_ROUTES_MISSING):	$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_PICKLE_OSM)

$(1)-cache:			$$($(2)_TARGET_PICKLE_GTFS) $$($(2)_TARGET_PICKLE_OSM)

$(1)-clean-cache-osm:
	rm $$($(2)_TARGET_QUERY_OSM)
	rm $$($(2)_TARGET_PICKLE_OSM)

$(1)-clean-cache-gtfs:
	rm $$($(2)_TARGET_PICKLE_GTFS)

$(1)-cleanall:
	echo rm -rf $$($(2)_WORK_DIR)


$$($(2)_TARGET_DOWNLOAD):	PROVIDER=$(2)
$$($(2)_TARGET_EXTRACT):	PROVIDER=$(2)
$$($(2)_TARGET_PICKLE_GTFS):	PROVIDER=$(2)
$$($(2)_TARGET_QUERY_OSM):	PROVIDER=$(2)
$$($(2)_TARGET_PICKLE_OSM):	PROVIDER=$(2)
$$($(2)_TARGET_STOPS):		PROVIDER=$(2)
$$($(2)_TARGET_STOPS_MISSING):	PROVIDER=$(2)
$$($(2)_TARGET_ROUTE):		PROVIDER=$(2)
$$($(2)_TARGET_ROUTE_UPDATE):	PROVIDER=$(2)
$$($(2)_TARGET_ROUTES):		PROVIDER=$(2)
$$($(2)_TARGET_ROUTES_MISSING):	PROVIDER=$(2)

endef

# This is where the GTFS dataset are defined
include providers.mk

help:
	@echo "GTFS Importer - Import GTFS data to OpenStreetmap"
	@echo ""
	@echo "Helper Makefile to fetch and extract GTFS dataset from know providers"
	@echo ""
	@echo ""
	@echo "Getting GTFS data:"
	@echo "make <provider>-fetch		fetch GTFS archive for <provider>"
	@echo "make <provider>-extract		extract archive in work directory"
	@echo ""
	@echo "Cache section:"
	@echo "make <provider>-pickle-gtfs	generate cache from GTFS data"
	@echo "make <provider>-query-osm	generate XML file with latest OSM data"
	@echo "make <provider>-pickle-osm	generate cache from OSM data"
	@echo "make <provider>-cache		alias for pickle-gtfs and pickle-osm"
	@echo ""
	@echo "Stops section:"
	@echo "make <provider>-export-stops		export all GTFS stops"
	@echo "make <provider>-export-stops-missing	export stops missing in OSM"
	@echo ""
	@echo "Routes section:"
	@echo "make <provider>-export-route route=<id>	export only route with specified id"
	@echo "make <provider>-export-routes		export all GTFS routes"
	@echo "make <provider>-export-routes-missing	export routes missing in OSM"
	@echo "make <provider>-update-route route=<id>	update route with specified id"
	@echo ""
	@echo "Clean section:"
	@echo "    Cleaning up cache is required if upstream (be it OSM or GTFS) data"
	@echo "    has changed. That will force this tool to fetch up-to-date data"
	@echo "make <provider>-clean-cache-osm          Remove OSM-related cache files"
	@echo "make <provider>-clean-cache-gtfs         Remove GTFS cache file"
	@echo "make <provider>-cleanall                 Remove work directory"
	@echo ""
	@echo ""
	@echo "Supported providers:"
	@echo -e "\texo-chambly (Chambly-Richelieu-Carignan)"
	@echo -e "\texo-haut-st-laurent (Haut-Saint-Laurent)"
	@echo -e "\texo-laurentides (Laurentides)"
	@echo -e "\texo-presquile (La Presqu'île )"
	@echo -e "\texo-st-richelain (Le Richelain)"
	@echo -e "\texo-roussillon (Roussillon)"
	@echo -e "\texo-sorel-varennes (Sorel-Varennes)"
	@echo -e "\texo-sud-ouest (Sud-ouest)"
	@echo -e "\texo-vallee-richelieu (Vallée du Richelieu)"
	@echo -e "\texo-assomption (L'Assomption)"
	@echo -e "\texo-terrebonne (Terrebonne-Mascouche)"
	@echo -e "\texo-ste-julie (Sainte-Julie)"
	@echo -e "\tstl (Société de Transport de Laval)"
	@echo -e "\tstm (Société de Transport de Montréal)"
