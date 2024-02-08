#!/usr/bin/python

# See https://gist.github.com/emxsys/a507f3cad928e66f6410e7ac28e2990f
# See https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/0

import datetime
import logging
import math
import statistics
import socket
import time
from gpiozero import Button
from gpiozero import MCP3008

# Contants
WIND_SPEED_CALIBRATION = 1.18
WIND_DIRECTION_LOOKUP = {"0.4": 0.0, "1.4": 22.5, "1.2": 45.0, "2.8": 67.5, "2.7": 90.0, "2.9": 112.5, "2.2": 135.0, "2.5": 157.5,
  "1.8": 180.0, "2.0": 202.5, "0.7": 225.0, "0.8": 247.5, "0.1": 270.0, "0.3": 292.5, "0.2": 315.0, "0.6": 337.53}
ANEMOMETER_RADIUS_CM = 9.0
ANEMOMETER_CIRCUMFERENCE_CM = (2 * math.pi) * ANEMOMETER_RADIUS_CM
CM_IN_1KM = 100000.0
SECS_IN_1HOUR = 3600.0
RAIN_BUCKET_SIZE = 0.2794
FIVE_SECONDS = 5
FIVE_MINUTES = 5 * 60

rain_count = 0
wind_count = 0

def get_average_direction(angles):
  sin_sum = 0.0
  cos_sum = 0.0

  for angle in angles:
    r = math.radians(angle)
    sin_sum += math.sin(r)
    cos_sum += math.cos(r)

  flen = float(len(angles))
  s = sin_sum / flen
  c = cos_sum / flen
  arc = math.degrees(math.atan(s / c))
  average = 0.0

  if s > 0 and c > 0:
    average = arc
  elif c < 0:
    average = arc + 180
  elif s < 0 and c > 0:
    average = arc + 360

  return 0.0 if average == 360 else round(average,0)

def wind_trigger():
  global wind_count
  wind_count += 1

# We get two events for each rotation of the anemometer. The circumference has been pre-calculated to get the distance travelled.
# Convert this into km/hr and multiply by a standard calibration value.
def get_wind_speed( time_sec ):
  global wind_count

  rotations = wind_count / 2.0
  dist_km = ANEMOMETER_CIRCUMFERENCE_CM * rotations / CM_IN_1KM
  km_per_sec = dist_km / time_sec
  km_per_hour = km_per_sec * SECS_IN_1HOUR

  # reset the wind counter to start again
  wind_count = 0

  return km_per_hour * WIND_SPEED_CALIBRATION

def rain_trigger():
  global rain_count
  rain_count += 1

def get_rainfall():
  global rain_count
  rainfall = rain_count * RAIN_BUCKET_SIZE
  rain_count = 0
  return round(rainfall,2)

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  logging.info("Starting...")

  # setup our two triggers on button events
  wind_sensor = Button(5)
  rain_sensor = Button(6)
  rain_sensor.when_pressed = rain_trigger
  wind_sensor.when_pressed = wind_trigger

  wind_direction_adc = MCP3008(channel=0)
  try:
    wind_speed_readings = []
    wind_direction_readings = []

    average_wind_direction = 0

    while True:
      start_time = time.time()
      while time.time() - start_time <= FIVE_MINUTES:

        sample_start = time.time()
        sample_readings = []
        while time.time() - sample_start <= FIVE_SECONDS:
          # Wind direction handling
          wind_direction_reading = str(round(wind_direction_adc.value * 3.3,1))

          # Convert reading into a direction 0-360 degrees, only deal with good readings
          if wind_direction_reading in WIND_DIRECTION_LOOKUP:
            sample_readings.append(WIND_DIRECTION_LOOKUP[wind_direction_reading])

          time.sleep(1)
        wind_direction_readings.append( statistics.mean( sample_readings ))

        # Wind speed handling, let the events be counted for wind_speed_period seconds and get the speed
        wind_speed_readings.append( get_wind_speed( FIVE_SECONDS ))

      average_wind_direction = int(get_average_direction(wind_direction_readings))
      wind_gust = round(max(wind_speed_readings),2)
      mean_wind_speed = round(statistics.mean(wind_speed_readings),2)

      wind_direction_readings = []
      wind_speed_readings = []

      # Rainfall handler
      rainfall = get_rainfall()

      dts = time.time()
      logging.info(datetime.datetime.now().replace(microsecond=0).isoformat())
      #print(dts,"direction",average_wind_direction, "mean wind",mean_wind_speed, "gust", wind_gust, "rainfall", rainfall)
      sock = socket.socket()
      sock.connect(("raspberry2.home",2003))	
      message = "weather.wind_speed.mean {:.2f} {}\n".format( mean_wind_speed, dts ) 
      sock.send(message.encode())
      message = "weather.wind_speed.gust {:.2f} {}\n".format( wind_gust, dts ) 
      sock.send(message.encode())
      message = "weather.wind_direction {:.2f} {}\n".format( average_wind_direction, dts ) 
      sock.send(message.encode())
      message = "weather.rainfall {:.2f} {}\n".format( rainfall, dts ) 
      sock.send(message.encode())
      sock.close()

  except KeyboardInterrupt as e:
    logging.info("Interrupted...")

