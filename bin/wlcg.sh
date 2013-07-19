#!/bin/sh

# url to view wlcg data: http://gstat-wlcg.cern.ch/apps/capacities/federations/

mm=`date +%m`           #01 to 12
mmm=`date +%b`          #Apr

# m = 1 to 12 (Remove the leading 0 if any in mm)
if [ $mmm == "Oct" -o $mmm == "Nov" -o $mmm == "Dec" ]; then
    m=$mm
else
    m=${mm/0/}
fi

dd=`date +%d`           #01 to 31
yyyy=`date +%Y`         #2005

logFile=$INSTALL_DIR/var/log/${yyyy}-${mm}-${dd}.log
wlcgFile=$INSTALL_DIR/var/log/wlcg.txt

echo "curl http://gstat-wlcg.cern.ch/apps/capacities/federations/ALL/$yyyy/$m/all/csv"
curl http://gstat-wlcg.cern.ch/apps/capacities/federations/ALL/$yyyy/$m/all/csv --output $wlcgFile 2>>$logFile
exitCode=$?
[ $exitCode -ne 0 ] && echo "curl failed. Look at $logFile for the error details." && exit 1

if [ -r $wlcgFile ]; then
    wlcgCsv=`cat $wlcgFile|egrep "Tier 1,USA,|Tier 2,USA,"|cut -d',' -f3,6,7,8`
    echo "$wlcgCsv"
    rm -f $wlcgFile
else
    echo "Error!!! Cannot read from $wlcgFile"
    echo `date` "Error!!! Cannot read from $wlcgFile" >> $logFile && exit 1
fi
