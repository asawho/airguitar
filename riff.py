import sys, os, time, signal, random
import json
import argparse
from enum import Enum
import pygame
import numpy as np
import mma8451

class RiffGame():
    def __init__(self):
        #Setup termination handlers
        self.stopMainLoop=False
        def sigDown(signum, frame):
            print('Exiting...')
            self.stopMainLoop=True
        signal.signal(signal.SIGINT, sigDown)
        signal.signal(signal.SIGTERM, sigDown)

        #Setup accelerometer
        self.sensor = mma8451.MMA8451()

        #Setup pygame, in trainging mode we are in a windowed environment so we can capture keys
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        #pygame.display.set_mode((500,500))
        self.pyClock = pygame.time.Clock()

        #Load up the sounds
        self.crowds = ['crowd-one.wav', 'crowd-two.wav']    
        for i in range(len(self.crowds)):
            self.crowds[i]=pygame.mixer.Sound('sounds/' + self.crowds[i])
        
        self.riffsup = ['baba-up.wav', 'nookie-up.wav']    
        for i in range(len(self.riffsup)):
            if self.riffsup[i]:
                self.riffsup[i]=pygame.mixer.Sound('riffs/' + self.riffsup[i])
        self.riffs = ['baba-riff.wav', 'nookie-riff.wav']    
        for i in range(len(self.riffs)):
            self.riffs[i]=pygame.mixer.Sound('riffs/' + self.riffs[i])
        self.riffsdown = [None, 'nookie-down.wav']    
        for i in range(len(self.riffsdown)):
            if self.riffsdown[i]:
                self.riffsdown[i]=pygame.mixer.Sound('riffs/' + self.riffsdown[i])                

        #Game play vars
        self.stopMainLoop=False

    def crowdSoundEvent(self, isOn, stateChangeAt):
        if isOn:
            self.crowds[1].play(fade_ms=750)
            pygame.mixer.music.set_volume(0.75)
        else:
            self.crowds[1].fadeout(1500)
            self.crowds=self.crowds[1:] + [self.crowds[0]]
            pygame.mixer.music.set_volume(1.0)

    def play(self):
        gdata=np.zeros((200, 3))
        mode='off'
        songTotal=len(self.riffs)
        chosenSongIndex=None

        #Start the game loop        
        while not self.stopMainLoop:
            #Grab the acceleration and buffer it
            acc = self.sensor.acceleration    
            gdata = np.roll(gdata, 1, axis=0)
            gdata[0]=acc
            #print(acc)
            inRiffSelectPos = abs(np.max(gdata[:25, 2])) < 2

            #Always bail
            inOffPos = np.max(gdata[:10, 1]) < 10 and np.min(gdata[:10, 1]) > 8
            if inOffPos and mode!='off':
                if chosenSongIndex is not None:
                    if self.riffsup[chosenSongIndex]:
                        self.riffsup[chosenSongIndex].stop()
                    self.riffs[chosenSongIndex].stop()
                mode='off'
                print('To {}'.format(mode))

            if mode=='off':
                #Palm down for half second, z at max x,y ~ 0
                #inCmdPos = np.max(gdata[:100, 2]) < 11 and np.min(gdata[:100, 2]) > 8 and abs(np.mean(gdata[:20,0])) < 2 and abs(np.mean(gdata[:20,1])) < 2
                #Thumbs up for one second and y < 0
                #print(abs(np.mean(gdata[:100, 2])), np.mean(gdata[:20,1])) 
                inCmdPos = np.max(gdata[:50, 2]) < 3 and np.min(gdata[:50, 2]) > -3 and np.max(gdata[:20,1]) < 2
                if inCmdPos:
                    mode='waitForStrike'
                    flipZero=None
                    chosenSongIndex=None
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
                        if chosenSongIndex >= songTotal:
                            chosenSongIndex = songTotal-1
                        #print(chosenSongIndex)
                #We either stroke, pre-play or we bail
                else:
                    #print(acc)
                    if not flipZero:
                        flipZero=time.time()
                    elif time.time()-flipZero > 0.1:
                        #Play intro
                        if np.min(gdata[:10,2]) < -4 and chosenSongIndex is not None:
                            mode='introplay'
                            print('playing intro {}'.format(chosenSongIndex))
                            if self.riffsup[chosenSongIndex]:
                                self.riffsup[chosenSongIndex].play(fade_ms=250)
                        #Rip it
                        elif np.min(gdata[:10,0]) < -2 and chosenSongIndex is not None:
                            mode='riffplay'
                            print('playing song {}'.format(chosenSongIndex))
                            self.riffs[chosenSongIndex].play()
                        else:
                            mode='off'
                            print('To {}'.format(mode))
            
            elif mode=='introplay':
                if np.min(gdata[:10,2]) >= -4:
                    mode='riffplay'
                    print('playing song {}'.format(chosenSongIndex))
                    if self.riffsup[chosenSongIndex]:
                        self.riffsup[chosenSongIndex].fadeout(250)
                    self.riffs[chosenSongIndex].play()

            elif mode=='riffplay':
                most = np.max(np.abs(gdata[:100]), axis=0)
                mag = np.sqrt(np.sum(most*most)) - 9.86
                if not pygame.mixer.get_busy():
                    mode='off'
                    print('Song ended -> off')
                #Stop moving monitor
                # elif mag < 2:
                #     self.riffs[chosenSongIndex].stop()
                #     mode='off'
                #     print('No movement -> off')

            #Framerate of 100
            self.pyClock.tick(100)

    def shutdown(self):
        pygame.mixer.music.stop()
        pygame.quit()
        sys.exit()

#Startup the game
#scp riffs\*.wav pi@raspberrypi:/home/pi/air/riffs
#sudo amixer cset numid=1 100%
game=RiffGame()
game.play()
game.shutdown()