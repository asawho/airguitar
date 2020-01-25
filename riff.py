import sys, os, time, signal, random
import json
import argparse
import pygame
import numpy as np
import mma8451

class RiffGame():
    def __init__(self, cueOn):
        self.cueOn=cueOn

        #Setup termination handlers
        self.stopMainLoop=False
        def sigDown(signum, frame):
            print('Exiting...')
            self.stopMainLoop=True
        signal.signal(signal.SIGINT, sigDown)
        signal.signal(signal.SIGTERM, sigDown)

        #Setup accelerometer
        self.sensor = mma8451.MMA8451()

        #Setup pygame
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        #pygame.init()
        #pygame.display.set_mode((500,500))
        self.pyClock = pygame.time.Clock()

        #Load up the sounds
        self.numbers = ['song-one.wav','song-two.wav','song-three.wav','song-four.wav','song-five.wav','song-six.wav','song-seven.wav','song-eight.wav','song-nine.wav','song-ten.wav']    
        for i in range(len(self.numbers)):
            self.numbers[i]=pygame.mixer.Sound('sounds/' + self.numbers[i])
            self.numbers[i].set_volume(0.15)

        self.crowds = ['crowd-one.wav', 'crowd-two.wav']    
        for i in range(len(self.crowds)):
            self.crowds[i]=pygame.mixer.Sound('sounds/' + self.crowds[i])

        self.riffbase =     ['baba', 'nookie', 'sandman', 'roses-blaze', 'roses-paradise',  'ozzy-tears',   'nirvana-teen', 'meatloaf-anything']
        self.riffstarttype = ['fast', 'fast',   'fast',   'fast',        'fast',            'slow',         'slow',         'slow']
        self.riffs =    list(map(lambda x: x + '-riff.wav', self.riffbase))
        self.riffsup =  list(map(lambda x: x + '-up.wav', self.riffbase))
        
        for i in range(len(self.riffs)):
            self.riffs[i]=pygame.mixer.Sound('riffs/' + self.riffs[i])
        for i in range(len(self.riffsup)):
            if os.path.exists('riffs/' + self.riffsup[i]):
                self.riffsup[i]=pygame.mixer.Sound('riffs/' + self.riffsup[i])
            else:
                self.riffsup[i]=None

        #Game play vars
        self.stopMainLoop=False

    def play(self):
        gdata=np.zeros((200, 3))
        mode='off'
        songTotal=len(self.riffs)
        chosenSongIndex=None
        lastChosenIndexPlayed=None

        crowdPlaying=False

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

            #Always Play the crowd
            #print(np.max(gdata[:100, 1]), np.min(gdata[:100, 1]))
            inCrowdPos = np.min(gdata[:100, 1]) > -11 and np.max(gdata[:100, 1]) < -9
            if inCrowdPos:
                if not crowdPlaying:                
                    print('crowd on')
                    crowdPlaying=True
                    self.crowds[1].play(fade_ms=750)
                    pygame.mixer.music.set_volume(0.75)

            else:
                if crowdPlaying:
                    print('crowd off')
                    crowdPlaying=False
                    self.crowds[1].fadeout(1500)
                    self.crowds=self.crowds[1:] + [self.crowds[0]]
                    pygame.mixer.music.set_volume(1.0)

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
                        #7 just scales what angle we divide the songs among
                        chosenSongIndex = int(abs(ymean/(7))*songTotal)
                        if chosenSongIndex < 0: 
                            chosenSongIndex = 0
                        if chosenSongIndex >= songTotal:
                            chosenSongIndex=None
                            #chosenSongIndex = songTotal-1

                        if chosenSongIndex is not None and chosenSongIndex!=lastChosenIndexPlayed and self.cueOn:
                            self.numbers[chosenSongIndex].play()
                            lastChosenIndexPlayed = chosenSongIndex
                            print(chosenSongIndex)

                #We either stroke, pre-play or we bail
                else:
                    #print(acc)
                    if not flipZero:
                        flipZero=time.time()

                    elif time.time()-flipZero > 0.1:
                        #Play intro
                        if np.min(gdata[:10,2]) < -4 and chosenSongIndex is not None:
                            #Play the up
                            if self.riffsup[chosenSongIndex]:
                                mode='introplay'
                                print('playing intro {}'.format(chosenSongIndex))
                                self.riffsup[chosenSongIndex].play(fade_ms=250)
                            #Just go straight to the song
                            elif self.riffstarttype[chosenSongIndex]=='slow':
                                mode='riffplay'
                                print('playing song {}'.format(chosenSongIndex))
                                self.riffs[chosenSongIndex].play()

                        #Rip it
                        elif np.min(gdata[:10,0]) < -4 and chosenSongIndex is not None:
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
game=RiffGame(True)
game.play()
game.shutdown()