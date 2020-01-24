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
frequency = 100
timebase=1/frequency
gdata=np.zeros((frequency*2, 3))
gdataSum=np.zeros((frequency*2, 3))

gtime=[]
recording=False
started=stopped=None
lapstart=None
mode='off'
lastMark=time.time()
songTotal=10
while True:
    lapstart=time.time()
    
    #Grab the acceleration and buffer it
    acc = sensor.acceleration    
    gdata = np.roll(gdata, 1, axis=0)
    gdata[0]=acc
    #print(acc)
    inRiffSelectPos = abs(np.max(gdata[:25, 2])) < 2

    #Always bail
    inOffPos = np.max(gdata[:50, 1]) < 10 and np.min(gdata[:50, 1]) > 8
    if inOffPos:
        mode='off'

    if mode=='off':
        #Palm down for half second, z at max x,y ~ 0
        #inCmdPos = np.max(gdata[:100, 2]) < 11 and np.min(gdata[:100, 2]) > 8 and abs(np.mean(gdata[:20,0])) < 2 and abs(np.mean(gdata[:20,1])) < 2
        #Thumbs up for one second and y < 0
        #print(abs(np.mean(gdata[:100, 2])), np.mean(gdata[:20,1])) 
        inCmdPos = np.max(gdata[:100, 2]) < 2 and np.min(gdata[:100, 2]) > -1 and np.max(gdata[:20,1]) < 1
        if inCmdPos:
            mode='waitForStrike'
            flipZero=None
            print('To {}'.format(mode))

    elif mode=='waitForStrike':        
        #Z is zero for the duration, if it is not zero, x better be dramatically negative         
        zZero = abs(np.max(gdata[:25, 2])) < 2
        if zZero:
            #Select is done by y angle over 0.5 seconds
            ymax=np.max(gdata[:50,1])
            ymin=np.min(gdata[:50,1])
            ymean=np.mean(gdata[:50,1])
            if abs(ymax-ymin) < 1 and ymin < 0:
                chosenSongIndex = int(abs(ymean/9.86)*songTotal)
                if chosenSongIndex < 0: 
                    chosenSongIndex = 0
                if chosenSongIndex > songTotal:
                    chosenSongIndex = songTotal
                print(chosenSongIndex)
        #We either stroke or we bail
        else:
            if not flipZero:
                flipZero=time.time()
            elif time.time()-flipZero > 0.1:
                if np.min(gdata[:10,0]) < -15 and chosenSongIndex:
                    mode='riffplay'
                    print('playing song {}'.format(chosenSongIndex))
                else:
                    mode='off'
                    print('To {}'.format(mode))
    
    elif mode=='riffplay':
        most = np.max(np.abs(gdata[:25]), axis=0)
        mag = np.sqrt(np.sum(most*most)) - 9.86
        if mag < 2:
            mode='off'
            print('To {}'.format(mode))

    #Button is pressed
    if not GPIO.input(17):
        print('Curr: {} Avg 2: {} Avg 1: {} Avg 0.5: {}'.format(acc[2], gdataSum[0][2]/(frequency*2), gdataSum[-frequency][2]/(frequency), gdataSum[-50][2]/(frequency/2)))
    # else:
    #     if mode=='off':

    #     if not recording:
    #         print('Recording Start ', end='')        
    #         recording=True
    #         started=time.time()
    #     gdata.append(sensor.acceleration)
    #     print(gdata[-1])
    #     gtime.append(time.time())
    # elif recording:
    #     stopped=time.time()
    #     recording=False
    #     print('- Done')

    #     #Debounce
    #     time.sleep(0.1)

    #     #Write the data out
    #     df = pd.DataFrame(data=gdata, columns=['x','y','z'], index=gtime)
    #     #print(df.to_string())
    #     print(df)

    #     #Print a guessed position
    #     pos=[0,0,0]
    #     for i in range(len(gdata)):
    #         pos[0]=pos[0]+gdata[i][0]*timebase
    #         pos[1]=pos[1]+gdata[i][1]*timebase
    #         pos[2]=pos[2]+gdata[i][2]*timebase
    #     print('Position: {} after {} seconds'.format(pos, stopped-started))
    #     gdata=[]
    #     gtime=[]

    #100 times a second
    sl = timebase - (time.time()-lapstart)
    #print(sl)
    time.sleep(sl if sl > 0 else 0)
