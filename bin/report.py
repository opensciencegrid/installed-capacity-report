#!/usr/bin/env python

# Author: Karthik
# Date: Jan 8th 2009
# Purpose: Simple installed capacity report - reports the installed capacity of sites as published by OIM (the actual capacity)
# Logic: Read the WLCG installed capacity values published as XML by MyOSG and summarize it

import ConfigParser
import commands
import datetime
from datetime import date
import libxml2
import logging
#import logging.handlers
import os
import re
from sendEmail import *
import socket
import sys
import time
import traceback
import urllib2
import csv
from urllib2 import urlopen
from array import array
import json

# global variables

gInstallDir = os.path.dirname(os.path.abspath( __file__ ))
gInstallDir = gInstallDir[:-4]

# get the installation directory. 

# MyOSG url containing the installed capacity XML data to be parsed

gMYOSG_URL = "http://myosg.grid.iu.edu/rgsummary/xml?summary_attrs_showhierarchy=on&summary_attrs_showwlcg=on&summary_attrs_showvoownership=on&gip_status_attrs_showtestresults=on&downtime_attrs_showpast=&account_type=cumulative_hours&ce_account_type=gip_vo&se_account_type=vo_transfer_volume&bdiitree_type=total_jobs&bdii_object=service&bdii_server=is-osg&start_type=7daysago&start_date=01%2F19%2F2010&end_type=now&end_date=01%2F19%2F2010&sc=on&sc_19=on&sc_29=on&sc_30=on&sc_65=on&sc_8=on&gridtype=on&gridtype_1=on&active=on&active_value=1&disable_value=1"

# url to view wlcg data: http://gstat-wlcg.cern.ch/apps/capacities/federations/

# xpath filter to use for parsing the XML data
gXPATH_FILTER ="//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/Name|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/WLCGInformation/AccountingName|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/WLCGInformation/KSI2KMin|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/WLCGInformation/HEPSPEC|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/WLCGInformation/StorageCapacityMin|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/WLCGInformation/TapeCapacity|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/VOOwnership/Ownership/Percent|"
gXPATH_FILTER += "//ResourceGroup/Resources/Resource[WLCGInformation/InteropAccounting='True']/VOOwnership/Ownership/VO|"
#gXPATH_FILTER += "//ResourceGroup[Resources/Resource/WLCGInformation/InteropAccounting='True']/SupportCenter/Name"
gXPATH_FILTER += "//ResourceGroup[Resources/Resource/WLCGInformation/InteropAccounting='True']/SupportCenter"

gReportDate = date.today().strftime("%a, %b %d %Y") 
gEmailReport = False
gConfigFile = "config.ini"
gLogPrefix = date.today().strftime("%Y-%m-%d") 
gLogFile = "/var/log/InstalledCapacity" + gLogPrefix + ".log"
gLookAtLog = "Look at the log file at " + gLogFile + " for further details of the error and stack trace."
gSubject = "Installed capacity report for " + str(gReportDate)
gWlcgCapacity = {}
gOimCapacity = {}
gTapeCapacity = {}

# Report formatter string
gFormat = {}
gFormat["text"] = " %-7s | %-22s | %10s | %10s | %10s | %-25s |" 
gFormat["html"] = "<tr bgcolor=white><td>%s</td><td>%s</td><td align=right>%s</td><td align=right>%s</td><td align=right>%s</td><td>%s</td></tr>" 
gFormat["csv"] = ",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\""


# Set up a specific logger with our desired output level and log rotations
# my_logger = logging.getLogger('MyLogger')
# my_logger.setLevel(logging.DEBUG)
# Add the log message handler to the logger. The log files will be rotated every maxBytes with a maximum # of files maintained at backupCount 
#handler = logging.handlers.RotatingFileHandler(gLogFile, maxBytes=10485760, backupCount=10) # 10 MB size per log file
#my_logger.addHandler(handler)


def log(message, trace=True, sendEmail=True):
    if trace:
        print message
        message += getTraceBack()
    t = datetime.datetime.utcnow()
    timeStampShort = datetime.datetime.fromtimestamp(time.mktime(t.timetuple()))
    timeStampLong = timeStampShort.ctime()
    message = str(timeStampLong) + " - " + str(message)
    print "\n" + message
    if trace:
        hostName = socket.gethostbyaddr(socket.gethostname())
        subject = "ERROR!!! While running Installed Capacity Reporting script at " + str(timeStampLong) + " on " + str(hostName)
        message = str(timeStampLong) + "\n\nHost where the script was run: " + str(hostName) + "\n\n" + str(message)
        if sendEmail:
            emailHelper(subject, message, "error")
        #print "\n" + gLookAtLog
        sys.exit(1)

def handle_args(args):
   # purpose: handle command line arguments in a non-standard way (getopt is the standard way)
   # Example: --print or -print for printing the report 
   # Logic: Loop through the command line arguments one at a time.
   #        Strip off the leading dashes in any options.
   #        Use a if conditional statement to check the value for the argument and if a value is expected for that argument, read it by doing a pop
   #        Set all appropriate global flags corresponding to the arguments, so that they could then be understood in other methods
   # If no appropriate arguments are found, print usage and exit the program
       message = ""
       global gEmailReport, gConfigFile
       while args:
          arg = args.pop(0)
          while arg.startswith('-'): # strip all leading dashes one at a time
             arg = arg[1:]
          if (arg == "email"):
             gEmailReport = True
          elif (arg == "help" or arg == "h"):
             print Usage()
             sys.exit(0)
          elif (arg == "config"):
             gConfigFile = args.pop(0) 
             if not os.path.isfile(gInstallDir + "/etc/" + gConfigFile):
                 message = "ERROR!!! Cannot read the config file " + gConfigFile + "\n"
                 log(message)
          else:
             message += arg + " is an invalid command line argument. For help see usage. "
             message += Usage()
             log(message)

def getTraceBack():
    message = "\nThe full stack trace of this error is provided below: \n"
    message += traceback.format_exc()
    return message

def Usage():
   usage = "\n\nUsage: " + sys.argv[0] + " -email \n" 
   usage += "The default behavior is to print the report.\nTo change this, specify -email so that the report would be emailed to the recepients specified in the config file.\n\n"
   usage += "Example on how to run this as a cronjob:\n"
   usage += "export INSTALL_DIR=\"/home/karunach/velai/osg/installed_capacity/pledged\"; $INSTALL_DIR/bin/report.py --email\n"
   usage += "The default behavior of the script is to print the report to STDOUT. To email use the --email option\n"
   usage += "The default configuration file used by the script is config.ini. You can override this by specifying your own config file using the --config <config_file> option.\n"
   usage += "Note: The config.ini files has to be in the $INSTALL_DIR/etc"
   return usage

def getXmlDoc(url):
    # read the xml document
    try:
        html = urllib2.urlopen(url).read()
    except:
        message = "ERROR!!! urllib2.urlopen(\"" + url + "\").read() failed in getXmlDoc(url)\n"
        log(message)
    try:
        doc = libxml2.parseDoc(html)
    except:
        message = "ERROR!!! libxml2.parseDoc(" + html + ") failed in getXmlDoc(url). url is " + url + "\n"
        log(message)
    return doc

def printHeader(reportFormat):
    message = "Report date: " + str(gReportDate) + "\n\n"
    if (reportFormat == "html"):
        message += "&nbsp;<p><br>"
    message += "Table 1: Report of installed computing and storage capacity at sites." 
    return message

def findSum(siteSum, index, accountingName, dict):
    if(len(siteSum) == 3):
        ksi2k = siteSum[0] + int(float(dict[index][accountingName]["KSI2KMin"]))
        hs06 = siteSum[1] + int(float(dict[index][accountingName]["HEPSPEC"]))
        tb = siteSum[2] + intTB(dict[index][accountingName]["StorageCapacityMin"])
        tapeCapacity = dict[index][accountingName]["TapeCapacity"]
        if(t1Site(accountingName) and validValue(tapeCapacity)):
            tb += int(tapeCapacity)
    else:
        ksi2k = int(float(dict[index][accountingName]["KSI2KMin"]))
        hs06 = int(float(dict[index][accountingName]["HEPSPEC"]))
        tb = intTB(dict[index][accountingName]["StorageCapacityMin"])
    return [ksi2k, hs06, tb]

def printDashes(reportFormat):
    dashFillLength = 102
    if reportFormat == "text":
        return "%s" % (dashFillLength*"-") + "\n"
    return  ""

def intTB(tb):
   # input sample: "100 TB"
   # return value: 100
   #return int(re.compile("(.*) TB").search(tb).group(1))
   try:
       return int(float(re.compile(".*?(\d+).*").search(tb).group(1)))
   except:
       return 0

# thousands comma separator
def comma(s, sep=','):   
    # input sample: 100000
    # return value: 100,000
    s = str(s).strip()
    if len(s) <= 3: return s  
    return comma(s[:-3], sep) + sep + s[-3:]

def makeDict(xmlDoc,filter):
    # use xpath to parse the xml document 
    # Fill out the data into a dictionary that is organized as the sample shown below:
    # dict[1][US-AGLT2][site] = AGLT2
    # dict[1][US-AGLT2][KSI2KMin] = 1000
    # dict[2][US-NET2][site] = BU_ATLAS_T2
    # dict[2][US-AGLT2][KSI2KMin] = 2000
    # etc.
    # The first dimension of the dictionary is a numerical index that could be later used 
    # to sort the dictionary in the same order in which the data was inserted
    federationNum=0     # use this to keep the index for different federations (AccountingName) separate by creating a wide gap. That way we can sort easily by Federations, irrespective of the order in which they occur in the XML data published by MyOSG (NOTE: federation is nothing but the AccountingName)
    accountingName = {} # Dictionary to keep track of the index values for the different AccountingNames
    key1 = ""
    key2 = ""
    voStr = ""
    sc = "" # support center
    dict = {}  # process and store the whole XML data into this dictionary
    excluded = False # flag indicating if a resource is excluded from the accounting
    for resource in xmlDoc.xpathEval(filter):
        if(resource.name == "SupportCenter"):
            for child in resource.children:
                if child.name == "Name":
                    sc = child.content
            continue
        if resource.name == "VO" or resource.name == "Percent":
            voStr += resource.content + " "
            continue
        elif resource.name == "Name":
            site = resource.content
        elif resource.name == "AccountingName":
            excluded = False
            if excludedAccountingNames(resource.content):
                excluded = True
                voStr = ""
                continue
            if resource.content not in accountingName: # if this AccountingName wasn't already encountered
               accountingName[resource.content] = federationNum * 100 # create a new start index for this AccountingName with a jump of 100, so that this won't conflict with any other AccountingName
               federationNum+=1 # increase the federation count
            else: # This AccountingName was already encountered before
               accountingName[resource.content] = accountingName[resource.content] + 1 # just increment the index by a value of 1 for the next resource in this federation 
            indexVal = accountingName[resource.content] # Store the index value of the dictionary in a variable so that it could eaasily used below 
            dict[indexVal] = {}
            key1 = resource.content
            dict[indexVal][key1] = {}
            dict[indexVal][key1]["sc"] = sc
            dict[indexVal][key1]["site"] = site
            dict[indexVal][key1]["vo"] = formatVOString(voStr.rstrip())
            voStr = ""
        elif resource.name != "AccountingName" and not excluded:
            key2 = resource.name
            dict[indexVal][key1][key2] = resource.content 
    xmlDoc.freeDoc()
    #print dict # if you print the dictionary at this point, you will be able to see the nicely formatted data structure into which the MyOSG xml data has been stored
    return dict

def formatVOString(voStr):
    # in = "10 CDF 90 CMS"
    # ret = "CDF: 10, CMS: 90"
    ret = ""
    voList = voStr.split()
    for i in range(0,len(voList)):
        if i%2 == 0:
            percent = voList[i]
        else:
            vo = voList[i]
            if ret != "":
                ret += ", "
            ret += vo + ": " + percent
    return ret

def emptyDict(dict):
    if len(dict.keys()) == 0:
        return True
    return False

def excludedAccountingNames(inStr):
    excluded = ["BR-SP-SPRACE", "T2_BR_UERJ"]
    if inStr in excluded:
        return True
    return False

def excludedWlcgFederationNames(inStr):
    excluded = []
    if inStr in excluded:
        return True
    return False

# Dictionary to map WLCG federation names to OIM federation names
# format is : oim[wlcgName] = oimName
gWlcgToOim = {}
mapurllink = 'http://gstat-wlcg.cern.ch/apps/topology/all/json'
response  = urllib2.urlopen(mapurllink)
s = response.read()
x = json.read(s)
for obj in x:
    if('USA'==obj['Country']): 
        gWlcgToOim[obj['Federation']]=  obj['FederationAccountingName']

#fix the US-FNAL-CMS
#gWlcgToOim["US-FNAL-CMS"] = "US-FNAL-CMS"


def makeReport(dict, reportFormat):
    global gOimCapacity, gTapeCapacity
    message = printHeader(reportFormat) + "\n"
    prevAccountingName = "" 
    prevSc = "" 
    message+= printDashes(reportFormat)
    if(reportFormat == "html"):
        message += "<table bgcolor=black cellspacing=1 cellpadding=5 border=1>"
    message+= hilight(gFormat[reportFormat],"yellow")  % ("#","Site","KSI2K","HS06","TB","VO Ownership") + "\n"
    message+= printDashes(reportFormat)
    # variables to keep track of site totals
    siteSum = []
    # variables to keep track of grand total for ATLAS and CMS vo
    grandSum = []
    resourceNum = 0
    for index in sorted(dict.keys()):
        resourceNum+=1
        for accountingName in dict[index]:
            sc = dict[index][accountingName]['sc']
            tapeCapacity = dict[index][accountingName]['TapeCapacity']
            gTapeCapacity[accountingName] = 0
            gOimCapacity[accountingName] = {}
            if prevAccountingName!= "" and accountingName != prevAccountingName:
                message+= printDashes(reportFormat)
                message+= hilight(gFormat[reportFormat])  % ("Total:", prevAccountingName, comma(siteSum[0]), comma(siteSum[1]), comma(str(siteSum[2])), "") + "\n"
                gOimCapacity[prevAccountingName]['hepspec'] = siteSum[1]
                gOimCapacity[prevAccountingName]['storage'] = siteSum[2] * 1000
                message+= printDashes(reportFormat)
                if prevSc != "" and sc != prevSc:
                    message+= emptyLine(reportFormat) 
                    message+= hilight(gFormat[reportFormat], "palegoldenrod")  % ("Total:", "All " + prevSc, comma(grandSum[0]), comma(grandSum[1]), comma(str(grandSum[2])),"") + "\n"
                    message+= printDashes(reportFormat)
                    grandSum = [0,0,0]
                message+= emptyLine(reportFormat) 
                siteSum = [0,0,0]
            message+= printSiteRow(resourceNum, accountingName, index, dict, reportFormat) + "\n"
            siteSum = findSum(siteSum, index, accountingName, dict)
            grandSum = findSum(grandSum, index, accountingName, dict)
            if(validValue(tapeCapacity)):
                gTapeCapacity[accountingName] += int(float(tapeCapacity))
            prevAccountingName = accountingName
            prevSc = sc
    message+= printDashes(reportFormat)
    gOimCapacity[prevAccountingName]['hepspec'] = siteSum[1]
    gOimCapacity[prevAccountingName]['storage'] = siteSum[2] * 1000
    message+= hilight(gFormat[reportFormat])  % ("Total:", prevAccountingName, comma(siteSum[0]), comma(siteSum[1]), comma(str(siteSum[2])),"") + "\n"
    message+= emptyLine(reportFormat) 
    message+= printDashes(reportFormat)
    message+= hilight(gFormat[reportFormat],"palegoldenrod")  % ("Total:", "All " + sc, comma(grandSum[0]), comma(grandSum[1]), comma(str(grandSum[2])),"") + "\n"
    message+= printDashes(reportFormat)
    if(reportFormat == "html"):
        message += "</table>"
    return message

def emptyLine(format):
    return gFormat[format]  %("","","","","","")  + "\n" # print an empty line for the purpose of visual clarity

def t1Site(name):
    if name.find("BNL") != -1 or name.find("USCMS-FNAL-") != -1: 
        return True
    return False

def hilight(inStr,color="gold"):
    # Example input: <tr bgcolor=white>
    # Example output: <tr bgcolor=gold>
    return inStr.replace("white",color)

def printSiteRow(resourceNum, accountingName, index, dict, reportFormat):
    message = hilight(gFormat[reportFormat],"white")  % (str(resourceNum) + ".",dict[index][accountingName]["site"],comma(dict[index][accountingName]["KSI2KMin"]),comma(dict[index][accountingName]["HEPSPEC"]),comma(intTB(dict[index][accountingName]["StorageCapacityMin"])), dict[index][accountingName]["vo"])
    tapeCapacity = dict[index][accountingName]["TapeCapacity"]
    if(t1Site(accountingName) and validValue(tapeCapacity)):
        message += "\n"
        message += hilight(gFormat[reportFormat],"white")  % (str(resourceNum) + ".",dict[index][accountingName]["site"]+"_TAPE",0,0,comma(tapeCapacity),"")
    return message

def validValue(val):
    if val != "" and val != "0":
        return True
    return False

def emailHelper(subject, message, emailType, configFile = None):
    try:
        if(configFile == None):
	    configFile = gConfigFile
        configFile = gInstallDir + "/etc/" + configFile
        print "\nUsing Config File: %s\n"%(configFile)
        if not os.path.isfile(configFile):
            message = "ERROR!!! Cannot read the config file" + configFile + "\n"
        gConfig = ConfigParser.ConfigParser()
        gConfig.read(configFile) 
        fromEmail = gConfig.get("emailCommon","from")
        smtpServer = gConfig.get("emailCommon","smtpServer")
        if(emailType == "error"):
            toEmail = '"' + gConfig.get("emailError","to") + '"'
        elif(emailType == "report"):
            toEmail = gConfig.get("emailReport","to")
        print "%s %s %s"%(fromEmail, toEmail, smtpServer)
        sendEmail(fromEmail, toEmail, subject, message, smtpServer)

    except:
        log("ERROR!!! while trying to send the report as an email.\n", True, False)

def getWlcgCapacities():
    global gWlcgCapacity
    now = datetime.datetime.now()
    yearof=now.year
    monthof=now.month
    filehandle = urlopen("http://gstat-wlcg.cern.ch/apps/capacities/federations/ALL/"+str(yearof)+"/"+str(monthof)+"/tier/all/csv")
    reader = csv.reader(filehandle)
    dataarray=[]
    for row in reader:
	if "USA" in row:
		if "Tier 1" in row or "Tier 2" in row:
			newarr=[]
			newarr.append(row[2])
			newarr.append(row[5])
			newarr.append(row[6])
			newarr.append(row[7])
			dataarray.append(newarr)

    for arr in dataarray:
        federationWlcg = arr[0]
	if excludedWlcgFederationNames(federationWlcg):
	    continue
        print "\nfederationWlcg=%s"%(federationWlcg)
        federation = gWlcgToOim[federationWlcg]
        hepspecVal = arr[1]
        disk = arr[2]
        tape = arr[3]
        gWlcgCapacity[federation] = {}
        gWlcgCapacity[federation]['hepspec'] = int(float(hepspecVal))
        gWlcgCapacity[federation]['storage'] = int(float(disk))
        gWlcgCapacity[federation]['storage'] += int(float(tape))

def compareOimAndWlcgCapacities(formatType): 
    message = ""
    format = {}
    dashes = "--------------------------------------------------------------------------------------------------------------------\n"
    format["text"] = " %3s | %-18s | %15s | %15s | %5s | %15s | %15s | %5s |\n" 
    format["html"] = "\n<tr bgcolor=white><td>%s</td><td>%s</td><td align=right>%s</td><td align=right>%s</td><td align=right>%s</td><td align=right>%s</td><td align=right>%s</td><td align=right>%s</td></tr>" 
    format["csv"] = ",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"\n"

    count = 0
    if(formatType == "text"):
        message = dashes
    elif(formatType == "html"):
        message = "<table bgcolor=black cellspacing=1 cellpadding=5 border=1>"
    message += hilight(format[formatType],"yellow") %("#", "Federation", "HS06 WLCG", "HS06 OIM", "%diff", "Storage WLCG", "Storage OIM", "%diff")
    if(formatType == "text"):
        message += dashes
    attributes = ['hepspec', 'storage']
    diff = {}
    diffSign = 1
    for federation in sorted(gOimCapacity.iterkeys()):
        count += 1
        for attr in attributes:
            try:
                if (gWlcgCapacity[federation][attr] - gOimCapacity[federation][attr] < 0):
		    diffSign = -1
                diff[attr] = (gWlcgCapacity[federation][attr] - gOimCapacity[federation][attr])*100/gWlcgCapacity[federation][attr]
    	    except:
                diff[attr] = 100 * diffSign
        try:
            message += format[formatType] %(str(count)+".", federation, comma(gWlcgCapacity[federation]['hepspec']), comma(gOimCapacity[federation]['hepspec']), diff['hepspec'], comma(gWlcgCapacity[federation]['storage']), comma(gOimCapacity[federation]['storage']), diff['storage'])
        except:
            message += format[formatType] %("NO DATA - missing site", "NO DATA", "NO DATA", "NO DATA", "NO DATA", "NO DATA", "NO DATA", "NO DATA")



    if(formatType == "text"):
        message += dashes
    elif(formatType == "html"):
        message += "</table>"
    return message


def compareOimAndWlcgCapacitiesHelper(formatType): 
    message = "\n"
    if (formatType == "html"):
        message += "&nbsp;<p>"
    message += "Table 2: Comparison of Installed capacities reported through MyOSG and WLCG."
    message += "\n"
    message += compareOimAndWlcgCapacities(formatType)
    return message

def main(argv=None):
    # Handle command line arguments
    handle_args(sys.argv[1:]) # pass the list except the first entry sys.argv[0], which is the script name itself

    # parse the MyOSG data and create the report
    xmlDoc = getXmlDoc(gMYOSG_URL) 

    # Make a data dictionary out of it with meaningful data that could be summarized
    try:
        dict = makeDict(xmlDoc,gXPATH_FILTER)
    except:
        log("ERROR!!! while trying to makeDict \n")

    message = {}

    try:
        getWlcgCapacities()
        for format in ["text", "html", "csv"]:
            message[format] = makeReport(dict, format) 
            message[format] += compareOimAndWlcgCapacitiesHelper(format)
    except:
        log("ERROR!!! while trying to makeReport \n")

    # If the user explicitly provides the --email flag from command line then email the report
    if(gEmailReport):
        emailHelper(gSubject, message, "report")
    else: # The default behavior is to print the report to stdout
        print message

    # Always log the report for records
    #log(message, trace = False)

if __name__ == "__main__":
    sys.exit(main())
