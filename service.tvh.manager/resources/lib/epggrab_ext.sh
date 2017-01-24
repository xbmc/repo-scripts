#! /bin/sh
#
# Please place your command line for grabbing epg-data from external provider here
# Make sure all grabbers are configured properly and choose the appropriate socket
# of tvheadend!
#
# More information about XMLTV: http://wiki.xmltv.org/index.php/Main_Page
# XMLTV Project Page: http://sourceforge.net/projects/xmltv/files/
#
# Arguments:    $1: path for epg.xml
#               $2: path of PyEPG/XMLTV socket of tvheadend
#
# Provider: epgdata.com
tv_grab_eu_epgdata --days=4 | tee $1 | nc -U $2
#
# Provider: Egon zappt (german)
#tv_grab_eu_egon --days=4 | tee $1 | nc -w 5 -U $2
exit 0
