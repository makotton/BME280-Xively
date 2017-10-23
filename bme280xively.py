#!/usr/bin/python

import sys
import time
import smbus
import urllib2
import requests
import json
import datetime
import threading
import traceback

API_KEY = "********************"    # Xively API Key
FEED_ID = "********************"    # Xively Feed ID
INTERVAL = 60   # second

#  class Xively
class Xively:
       # constructor
       def __init__(self,  apiKey, feedId):
              self.apiKey = apiKey
              self.feedId = feedId

       # data send
       def send2Xively(self,  channel,  value):
              request = {'datastreams' : [ {'id' : channel,   'current_value' : value}]}
              jsonString= json.dumps(request)
              url = "https://api.xively.com/v2/feeds/" + self.feedId + ".json"
              headers = {"X-ApiKey": self.apiKey}
              response = requests.put(url, headers = headers, data = jsonString)
              return response

       # data send ++
       def postData(self, temperature, humidity, pressure):
              self.send2Xively('Temperature',  temperature)
              self.send2Xively('Humidity',  humidity)
              self.send2Xively('Pressure',  pressure)        	
# <-- 

#  class Sensor
class Sensor:
        # constant
        DEVICE_ADDRESS = 0x76
        BUS_CHANNEL = 1

        # constructor
        def __init__(self,  address = DEVICE_ADDRESS,  channel = BUS_CHANNEL):
                self.address = address
                self.channel = channel
                self.t_fine = 0.0
                self.data = []
                self.calibration = []
                self.digTemperature = []
                self.digPressure = []
                self.digHumidity = []

                self.bus = smbus.SMBus(self.channel)        	
                self.bus.write_byte_data(self.address, 0xF2, 0x01)
                self.bus.write_byte_data(self.address, 0xF4, 0x27)
                self.bus.write_byte_data(self.address, 0xF5, 0xA0)

        # set sensor data
        def setSensorData(self):
                del self.calibration[:]
                for i in range (0x88, 0x88+24):
                        self.calibration.append(self.bus.read_byte_data(self.address, i))
                self.calibration.append(self.bus.read_byte_data(self.address, 0xA1))
                for i in range (0xE1, 0xE1+7):
                        self.calibration.append(self.bus.read_byte_data(self.address, i))
        
                self.digTemperature = []
                self.digTemperature.append((self.calibration[1] << 8) | self.calibration[0])
                self.digTemperature.append((self.calibration[3] << 8) | self.calibration[2])
                self.digTemperature.append((self.calibration[5] << 8) | self.calibration[4])

                self.digPressure = []
                self.digPressure.append((self.calibration[7] << 8) | self.calibration[6])
                self.digPressure.append((self.calibration[9] << 8) | self.calibration[8])
                self.digPressure.append((self.calibration[11]<< 8) | self.calibration[10])
                self.digPressure.append((self.calibration[13]<< 8) | self.calibration[12])
                self.digPressure.append((self.calibration[15]<< 8) | self.calibration[14])
                self.digPressure.append((self.calibration[17]<< 8) | self.calibration[16])
                self.digPressure.append((self.calibration[19]<< 8) | self.calibration[18])
                self.digPressure.append((self.calibration[21]<< 8) | self.calibration[20])
                self.digPressure.append((self.calibration[23]<< 8) | self.calibration[22])

                self.digHumidity = []
                self.digHumidity.append(self.calibration[24] )
                self.digHumidity.append((self.calibration[26]<< 8) | self.calibration[25])
                self.digHumidity.append(self.calibration[27] )
                self.digHumidity.append((self.calibration[28]<< 4) | (0x0F & self.calibration[29]))
                self.digHumidity.append((self.calibration[30]<< 4) | ((self.calibration[29] >> 4) & 0x0F))
                self.digHumidity.append(self.calibration[31] )
        	
                for i in range(1, 2):
                        if self.digTemperature[i] & 0x8000:
                                self.digTemperature[i] = (-self.digTemperature[i] ^ 0xFFFF) + 1

                for i in range(1, 8):
                        if self.digPressure[i] & 0x8000:
                                self.digPressure[i] = (-self.digPressure[i] ^ 0xFFFF) + 1

                for i in range(0, 6):
                        if self.digHumidity[i] & 0x8000:
                                self.digHumidity[i] = (-self.digHumidity[i] ^ 0xFFFF) + 1  
	
        # get temperature
        def getTemperature(self):
                temperatureRawData = (self.data[3] << 12) | (self.data[4] << 4) | (self.data[5] >> 4)
                var1 = (temperatureRawData / 16384.0 - self.digTemperature[0] / 1024.0) * self.digTemperature[1]
                var2 = (temperatureRawData / 131072.0 - self.digTemperature[0] / 8192.0) * (temperatureRawData / 131072.0 - self.digTemperature[0] / 8192.0) * self.digTemperature[2]
                self.t_fine = var1 + var2
                temperature = self.t_fine / 5120.0
                return temperature

        # get humidity
        def getHumidity(self):
                humidityRawData  = (self.data[6] << 8)  |  self.data[7]
                humidity = self.t_fine - 76800.0
                if humidity != 0:
                        humidity = (humidityRawData - (self.digHumidity[3] * 64.0 + self.digHumidity[4]/16384.0 * humidity)) * (self.digHumidity[1] / 65536.0 * (1.0 + self.digHumidity[5] / 67108864.0 * humidity * (1.0 + self.digHumidity[2] / 67108864.0 * humidity)))
                else:
                        return 0
                humidity = humidity * (1.0 - self.digHumidity[0] * humidity / 524288.0)
                if humidity > 100.0:
                        humidity = 100.0
                elif humidity < 0.0:
                        humidity = 0.0
                return humidity
        	
        # get pressure
        def getPressure(self):
                pressureRawData = (self.data[0] << 12) | (self.data[1] << 4) | (self.data[2] >> 4)
                var1 = (self.t_fine / 2.0) - 64000.0
                var2 = (((var1 / 4.0) * (var1 / 4.0)) / 2048) * self.digPressure[5]
                var2 = var2 + ((var1 * self.digPressure[4]) * 2.0)
                var2 = (var2 / 4.0) + (self.digPressure[3] * 65536.0)
                var1 = (((self.digPressure[2] * (((var1 / 4.0) * (var1 / 4.0)) / 8192)) / 8)  + ((self.digPressure[1] * var1) / 2.0)) / 262144
                var1 = ((32768 + var1) * self.digPressure[0]) / 32768
        	
                if var1 == 0:
                        return 0
                pressure = ((1048576 - pressureRawData) - (var2 / 4096)) * 3125
                if pressure < 0x80000000:
                        pressure = (pressure * 2.0) / var1
                else:
                        pressure = (pressure / var1) * 2
                var1 = (self.digPressure[8] * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
                var2 = ((pressure / 4.0) * self.digPressure[7]) / 8192.0
                pressure = pressure + ((var1 + var2 + self.digPressure[6]) / 16.0)  
                return  (pressure/100)
        	
        # check sensor data
        def checkData(self):
                del self.data[:]
                for i in range (0xF7,  0xF7+8):
                        self.data.append(self.bus.read_byte_data(self.address, i))
        
                temperature = round(self.getTemperature(),  2)
                humidity = round(self.getHumidity(),  2)
                pressure =round(self.getPressure(),  2)
        
                print "temperature : %0.2f / humidity : %0.2f / pressure : %0.2f" %(temperature, humidity, pressure)                
                return {"t": temperature, "h": humidity, "p": pressure}
#                xively.send2Xively('Temperature',  temperature)
#                xively.send2Xively('Humidity',  humidity)
#                xively.send2Xively('Pressure',  pressure)        	
# <-- 

# entry point
if __name__ == '__main__':
        # create instance
        xively = Xively(API_KEY, FEED_ID) 
        sensor = Sensor()
        threads = []

        # monitoring
        while True:
                try:
                        time.sleep(INTERVAL)
                        sensor.setSensorData()
                        value = sensor.checkData()
                        for thread in threads:
                                thread.join()
                        t1 = threading.Thread(target=xively.postData, args=(value['t'],  value['h'], value['p']))
                        t1.start()
                        threads.append(t1)
                except KeyboardInterrupt:
                        print 'KeyboardInterrupt'
                        break
                except:
                        print 'other'
                        print traceback.format_exc()
                        break
