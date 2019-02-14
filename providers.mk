
STL_ARCHIVE	:= GTF_STL.zip
STL_REMOTE_URL 	:= http://www.stl.laval.qc.ca/opendata
$(eval $(call gtfs-providers,stl,STL))

STM_ARCHIVE	:= gtfs_stm.zip
STM_REMOTE_URL 	:= http://stm.info/sites/default/files/gtfs
$(eval $(call gtfs-providers,stm,STM))
