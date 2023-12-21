#!/usr/bin/python3
#
# Script to be called from cron on a periodic basis.
# Read the temperatures from all devices and send this to a graphite service on port 2003
# using the simple protocol.

import argparse
import socket
import time
from DS18B20 import DS18B20

parser = argparse.ArgumentParser()
parser.add_argument("--host",help="Graphite server to send data to",default="localhost")
parser.add_argument("--port",type=int,help="Graphite server port to use",default=2003)
parser.add_argument("--nosend",action="store_true",help="Don't send data to Graphite")
parser.add_argument("--verbose",action="store_true",help="Print readings to console")
args = parser.parse_args()

devices = DS18B20()
names = devices.device_names()

# Simple name mapping for my sensors to make the metrics easier to use
alias = {
    "28-7fda411f64ff": "outside",
    "28-c3639c1e64ff": "inside"
}

send_to_graphite = not args.nosend

try:
    dts = time.time()

    if send_to_graphite:
        sock = socket.socket()
        sock.connect((args.host,args.port))	

    for i,name in enumerate(names):
        temp = devices.tempC(i)
        if name in alias:
            name = alias[name]
        message = "greenhouse.{}.temperature {:.2f} {}\n".format( name, temp, dts ) 
        if args.verbose:
            print(message[:-1])
        if send_to_graphite:
	        sock.send(message.encode())

    if send_to_graphite:
        sock.close()
except Exception as e:
    print("exiting",e)
