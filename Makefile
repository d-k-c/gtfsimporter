
OUTPUT := $(CURDIR)/work

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

$(OUTPUT)/%/.stamp_cache_created:
	pipenv run python -m gtfsimporter.main \
		--gtfs-datadir $($(PROVIDER)_UNPACK_DIR) \
		generate-cache $($(PROVIDER)_CACHE_FILE)
	@touch $@

$(OUTPUT)/%/.stamp_routes_created:
	pipenv run python -m gtfsimporter.main \
		--osm-cache $($(PROVIDER)_CACHE_FILE) \
		--gtfs-datadir $($(PROVIDER)_UNPACK_DIR) \
		export-routes --dest $($(PROVIDER)_ROUTES_FILE)
	@touch $@

# Make is not fond of two "%" in a target. Work around it
# by dropping the prefix
route_%.osm:
ifeq ($(route),)
	$(error "Unspecified route, expecting 'route=<id>' as parameter")
endif
	pipenv run python -m gtfsimporter.main \
		--osm-cache $($(PROVIDER)_CACHE_FILE) \
		--gtfs-datadir $($(PROVIDER)_UNPACK_DIR) \
		export-route --dest $@ $(route)


define gtfs-providers

$(2)_WORK_DIR   = $(OUTPUT)/$(1)
$(2)_UNPACK_DIR = $$($(2)_WORK_DIR)/gtfs
$(2)_CACHE_FILE = $$($(2)_WORK_DIR)/stops.cache
$(2)_ROUTES_FILE = $$($(2)_WORK_DIR)/routes.osm

$(2)_TARGET_DOWNLOAD = $$($(2)_WORK_DIR)/.stamp_downloaded
$(2)_TARGET_EXTRACT  = $$($(2)_WORK_DIR)/.stamp_extracted
$(2)_TARGET_CACHE_STOPS    = $$($(2)_WORK_DIR)/.stamp_cache_created
# target for a single route
$(2)_TARGET_ROUTE    = $$($(2)_WORK_DIR)/route_$(route).osm
$(2)_TARGET_ROUTES   = $$($(2)_WORK_DIR)/.stamp_routes_created

$(1)-fetch: $$($(2)_TARGET_DOWNLOAD)

$(1)-extract: 			$$($(2)_TARGET_EXTRACT)
$$($(2)_TARGET_EXTRACT):	$$($(2)_TARGET_DOWNLOAD)

$(1)-generate-stops-cache:	$$($(2)_TARGET_CACHE_STOPS)
$$($(2)_TARGET_CACHE_STOPS):	$$($(2)_TARGET_EXTRACT)

$(1)-clean-stops-cache:
	rm $$($(2)_TARGET_CACHE_STOPS)

$(1)-export-route:		$$($(2)_TARGET_ROUTE)
$$($(2)_TARGET_ROUTE):		$$($(2)_TARGET_CACHE_STOPS)

$(1)-export-routes:		$$($(2)_TARGET_ROUTES)
$$($(2)_TARGET_ROUTES):		$$($(2)_TARGET_CACHE_STOPS)

$$($(2)_TARGET_DOWNLOAD):	PROVIDER=$(2)
$$($(2)_TARGET_EXTRACT):	PROVIDER=$(2)
$$($(2)_TARGET_CACHE_STOPS):	PROVIDER=$(2)
$$($(2)_TARGET_ROUTE):		PROVIDER=$(2)
$$($(2)_TARGET_ROUTES):		PROVIDER=$(2)

endef

# This is where the GTFS dataset are defined
include providers.mk

help:
	@echo "GTFS Importer - Import GTFS data to OpenStreetmap"
	@echo ""
	@echo "Helper Makefile to fetch and extract GTFS dataset from know providers"
	@echo ""
	@echo "make <provider>-fetch		fetch GTFS archive for <provider>"
	@echo "make <provider>-extract		extract archive in a work directory"
	@echo "make <provider>-generate-stops-cache	generate a cache from latest OSM data"
	@echo "make <provider>-clean-stops-cache	delete cache timestamp, forcing its renewal"
	@echo "make <provider>-export-route	export a single route. Use route=id parameter"
	@echo "make <provider>-export-routes	export all found bus routes in JOSM format"
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
