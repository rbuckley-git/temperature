#!/usr/bin/python3
#
# Script to be called from cron on a periodic basis.
# Read some values from my local graphite and send them to the Met Office WOW service

import argparse
import datetime
import urllib.parse
import requests
import json
import statistics

parser = argparse.ArgumentParser()
parser.add_argument("--host",help="Graphite server to send data to",default="localhost")
parser.add_argument("--port",type=int,help="Graphite server port to use",default=8000)
parser.add_argument("--site",help="MetOffice site ID",default="4d8059a4-bfbb-11ee-aaf0-8f46228f35df")
parser.add_argument("--code",help="MetOffice site code",default="112233")
parser.add_argument("--verbose",action="store_true",help="Print readings to console")
args = parser.parse_args()

# See https://wow.metoffice.gov.uk/support/dataformats
url = "http://wow.metoffice.gov.uk/automaticreading"
site_id = "siteid=" + args.site
auth_code = "siteAuthenticationKey=" + args.code
software = "softwaretype=pi"

graphite_server_url = "http://" + args.host + ":" + str(args.port) + "/render?"

def celsius_to_fahrenheit( temp ):
    return round(( temp * 9 / 5 ) + 32,2)

def kmph_to_mph( speed ):
    return round( speed / 1.6, 2 )

# query the graphite server for values to average in the last hour
def find_average_value( name ):
    url = graphite_server_url + "target=movingAverage(" + name + ",'1h')&format=json&from=-1h"
    response = requests.get( url=url )
    if response.status_code == 200:
        content = json.loads(response.content)
        data = content[0]["datapoints"]
        return round(statistics.mean([v for v,t in  data]),2)

    return None

def send_met_office_data( url ):
    print(url)
    response = requests.get( url=url )
    if response.status_code != 200:
        if response.status_code == 429:
            print("Last request sent too recently")
        else:
            print(response.status_code)

metrics = [
    { 
        "name": "greenhouse.outside.temperature",
        "field": "tempf",
        "conversion": celsius_to_fahrenheit
    },
    { 
        "name": "weather.wind_speed.mean",
        "field": "windspeedmph",
        "conversion": kmph_to_mph
    }
]

dts = urllib.parse.quote_plus( datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") )

fields = []

# standard fields
fields.append(site_id)
fields.append(auth_code)
fields.append(software)
fields.append("dateutc=" + dts)

for metric in metrics:
    value = find_average_value( metric["name"] )
    if value:
        if metric["conversion"]:
            value = metric["conversion"](value)
        fields.append(metric["field"] + "=" + str(value))

send_met_office_data( url + "?" + "&".join(fields) )
