#!/usr/bin/python3

# Class to access the temperature sensor data and make it available.
# Largely code copied from the user manual. I am using two DS18B20 
# devices in a probe format with a long lead. These are one-wire protocol
# communications and each device has its own address. Multiple devices can
# be wired in parallel. They appear in /sys/bus/w1/devices/ as folders
# with a prefix 28. The pseudo file w1_slave contains the data.
# 
# For example:
#
# $ cat /sys/bus/w1/devices/28-7fda411f64ff/w1_slave 
# c6 00 55 00 7f ff 0c 10 bd : crc=bd YES
# c6 00 55 00 7f ff 0c 10 bd t=12375
#
# This code reads the data from this file and extracts the t=<n> bit.

import os
import glob
import time

class DS18B20:
    def __init__(self):
        os.system('modprobe w1-gpio') 
        os.system('modprobe w1-therm')
        base_dir = '/sys/bus/w1/devices/' 
        device_folder = glob.glob(base_dir + '28*') 
        self._count_devices = len(device_folder) 
        self._devices = list()
        i=0
        while i < self._count_devices:
            self._devices.append(device_folder[i] + '/w1_slave') 
            i += 1

    def device_names(self):
        names = list()
        for i in range(self._count_devices):
            names.append(self._devices[i]) 
            temp = names[i][20:35] 
            names[i] = temp

        return names
 
    def _read_temp(self, index):
        f = open(self._devices[index], 'r') 
        lines = f.readlines()
        f.close()
        return lines
    
    def tempC(self, index = 0):
        lines = self._read_temp(index)
        retries = 5
        while (lines[0].strip()[-3:] != 'YES') and (retries > 0):
            time.sleep(0.1)
            lines = self._read_temp(index) 
            retries -= 1

        if retries == 0:
            return 998
        
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp = lines[1][equals_pos + 2:]
            return float(temp) / 1000 
        return 999 # error 
        
    def device_count(self):
        return self._count_devices
