
STL_ARCHIVE	:= GTF_STL.zip
STL_REMOTE_URL 	:= http://www.stl.laval.qc.ca/opendata
$(eval $(call gtfs-providers,stl,STL))

STM_ARCHIVE	:= gtfs_stm.zip
STM_REMOTE_URL 	:= http://stm.info/sites/default/files/gtfs
$(eval $(call gtfs-providers,stm,STM))

EXO_ARCHIVE	:= google_transit.zip
EXO_REMOTE_URL	:= https://exo.quebec/xdata

define exo-gtfs-providers
$(2)_ARCHIVE 	:= $(EXO_ARCHIVE)
$(2)_REMOTE_URL	:= $(EXO_REMOTE_URL)/$(3)

$(eval $(call gtfs-providers,$(1),$(2)))
endef

$(eval $(call exo-gtfs-providers,exo-chambly,EXO_CRC,citcrc))
$(eval $(call exo-gtfs-providers,exo-haut-st-laurent,EXO_HSL,cithsl))
$(eval $(call exo-gtfs-providers,exo-laurentides,EXO_LA,citla))
$(eval $(call exo-gtfs-providers,exo-presquile,EXO_PI,citpi))
$(eval $(call exo-gtfs-providers,exo-st-richelain,EXO_LR,citlr))
$(eval $(call exo-gtfs-providers,exo-roussillon,EXO_ROUS,citrous))
$(eval $(call exo-gtfs-providers,exo-sorel-varennes,EXO_SV,citsv))
$(eval $(call exo-gtfs-providers,exo-sud-ouest,EXO_SO,citso))
$(eval $(call exo-gtfs-providers,exo-vallee-richelieu,EXO_VR,citvr))
$(eval $(call exo-gtfs-providers,exo-assomption,EXO_ASSO,mrclasso))
$(eval $(call exo-gtfs-providers,exo-terrebonne,EXO_TERREBONNE,mrclm))
$(eval $(call exo-gtfs-providers,exo-ste-julie,EXO_STE_JULIE,omitsju))
