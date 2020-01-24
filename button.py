import math, time, threading
import argparse
import mma8451
import numpy as np
import pandas as pd

import RPi.GPIO as GPIO

#Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('gesture', help='the name of the gesture to train')
args = parser.parse_args()
gname = args.gesture

#Setup the buton
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Setup the Accelerometer
sensor = mma8451.MMA8451()

#Loop as long as you like
timebase=1/100
gdata=[]
gtime=[]
recording=False
started=stopped=None
lapstart=None
while True:
    lapstart=time.time()
    #Button is pressed
    if not GPIO.input(17):
        if not recording:
            print('Recording Start ', end='')        
            recording=True
            started=time.time()
        gdata.append(sensor.acceleration)
        print(gdata[-1])
        gtime.append(time.time())
    elif recording:
        stopped=time.time()
        recording=False
        print('- Done')

        #Debounce
        time.sleep(0.1)

        #Write the data out
        df = pd.DataFrame(data=gdata, columns=['x','y','z'], index=gtime)
        #print(df.to_string())
        print(df)

        #Print a guessed position
        pos=[0,0,0]
        for i in range(len(gdata)):
            pos[0]=pos[0]+gdata[i][0]*timebase
            pos[1]=pos[1]+gdata[i][1]*timebase
            pos[2]=pos[2]+gdata[i][2]*timebase
        print('Position: {} after {} seconds'.format(pos, stopped-started))
        gdata=[]
        gtime=[]

    #100 times a second
    sl = timebase - (time.time()-lapstart)
    time.sleep(sl if sl > 0 else 0)
