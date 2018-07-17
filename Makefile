
STM_GTS_ZIPFILE := gtfs_stm.zip
STM_REMOTE_FOLDER := http://stm.info/sites/default/files/gtfs

GTFS_FILES := agency.txt \
	      calendar_dates.txt \
	      fare_attributes.txt \
	      fare_rules.txt \
	      feed_info.txt \
	      frequencies.txt \
	      routes.txt \
	      shapes.txt \
	      stop_times.txt \
	      stops.txt \
	      trips.txt

DATADIR := data

default: $(DATADIR)/archive-extracted

$(DATADIR):
	mkdir -p $@

$(DATADIR)/$(STM_GTS_ZIPFILE): | $(DATADIR)
	wget -O $@ $(STM_REMOTE_FOLDER)/$(STM_GTS_ZIPFILE)

$(addprefix $(DATADIR)/,$(GTFS_FILES)): $(DATADIR)/archive-extracted

# files within the archive have a timestamp before the archive itself
# so create a timestamp file to prevent future extractions
$(DATADIR)/archive-extracted: $(DATADIR)/$(STM_GTS_ZIPFILE)
	unzip -d $(DATADIR) $^
	touch $@

.PHONY: list
list: $(DATADIR)/trips.txt
	@echo "Results are display in two columns: Number of trips | Line number"
	@tail -n+2 $^ | cut -d, -f1 | sort -n | uniq -c | sort -n -r
