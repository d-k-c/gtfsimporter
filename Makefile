
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

define gtfs-providers

$(2)_WORK_DIR   = $(OUTPUT)/$(1)
$(2)_UNPACK_DIR = $$($(2)_WORK_DIR)/gtfs

$(2)_TARGET_DOWNLOAD = $$($(2)_WORK_DIR)/.stamp_downloaded
$(2)_TARGET_EXTRACT  = $$($(2)_WORK_DIR)/.stamp_extracted

$(1)-fetch: $$($(2)_TARGET_DOWNLOAD)

$(1)-extract: 			$$($(2)_TARGET_EXTRACT)
$$($(2)_TARGET_EXTRACT):	$$($(2)_TARGET_DOWNLOAD)

$$($(2)_TARGET_DOWNLOAD):	PROVIDER=$(2)
$$($(2)_TARGET_EXTRACT):	PROVIDER=$(2)

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
	@echo ""
	@echo "Supported providers:"
	@echo -e "\tstl (Société de Transport de Laval)"
	@echo -e "\tstm (Société de Transport de Montréal)"
