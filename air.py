import sys, os, time, signal, random
import json
import argparse
from enum import Enum
import pygame
import accel

class StateEnum(Enum):
    OFF=0
    SONG_READY=1
    SONG_PLAYING=2
    SONG_PLAYING_FAILED=3
    RIFF_READY=4
    RIFF_PLAYING=5

class AirGuitarGame():
    def __init__(self, song, mode):
        trainFile = os.path.splitext(args.song)[0]+'.txt'

        if not os.path.isfile(args.song):
            print ("Unable to find song file {}".format(args.song))
            sys.exit()
        if not os.path.isfile(trainFile) and args.mode!="train":
            print ("Unable to find label file {}".format(trainFile))
            sys.exit()

        #Setup termination handlers
        self.stopMainLoop=False
        def sigDown(signum, frame):
            print('Exiting...')
            self.stopMainLoop=True
        signal.signal(signal.SIGINT, sigDown)
        signal.signal(signal.SIGTERM, sigDown)

        #Setup accelerometer
        self.acc = accel.AccelCommands()
        self.acc.start()

        #Setup pygame, in trainging mode we are in a windowed environment so we can capture keys
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        pygame.init()
        #pygame.display.set_mode((500,500))
        self.pyClock = pygame.time.Clock()

        #Load up the sounds
        pygame.mixer.music.load(args.song)
        self.misses = ['miss-one.wav', 'miss-two.wav', 'miss-three.wav', 'miss-four.wav', 'miss-five.wav']
        for i in range(len(self.misses)):
            self.misses[i]=pygame.mixer.Sound('sounds/' + self.misses[i])
        self.crowds = ['crowd-one.wav', 'crowd-two.wav']    
        for i in range(len(self.crowds)):
            self.crowds[i]=pygame.mixer.Sound('sounds/' + self.crowds[i])
        self.commands = ['command-off.wav', 'command-on.wav', 'command-next.wav', 'command-previous.wav', 'command-song-mode.wav', 'command-riff-mode.wav']    
        for i in range(len(self.commands)):
            self.commands[i]=pygame.mixer.Sound('sounds/' + self.commands[i])
        self.curses = ['curse-bollocks.wav', 'curse-poop.wav', 'curse-skank.wav', 'curse-sod-off.wav', 'curse-wanker.wav']    
        for i in range(len(self.curses)):
            self.curses[i]=pygame.mixer.Sound('sounds/' + self.curses[i])
        self.drums = ['drum-cowbell.wav']    
        for i in range(len(self.drums)):
            self.drums[i]=pygame.mixer.Sound('sounds/' + self.drums[i])

        #Read the timing file file
        self.beats=[]
        with open(trainFile) as txt:
            self.beats = txt.read().splitlines(True)
        for i in range(len(self.beats)):
            self.beats[i]=float(self.beats[i].split('\t')[0])

        #Game play vars
        self.stopMainLoop=False
        self.lastPlayState=StateEnum.OFF
        self.playState=StateEnum.OFF
        self.playStatePending=None
        self.stateData={}

    def crowdSoundEvent(self, isOn, stateChangeAt):
        if isOn:
            self.crowds[1].play(fade_ms=750)
            pygame.mixer.music.set_volume(0.75)
        else:
            self.crowds[1].fadeout(1500)
            self.crowds=self.crowds[1:] + [self.crowds[0]]
            pygame.mixer.music.set_volume(1.0)

    def commandTapEvent(self, isOn, stateChangeAt):
        if isOn:
            #Random curse
            if random.random() * 100 < 10:
                print('Random sound')
                snd = random.randint(0,len(self.curses)-1)
                self.curses[snd].play()
            elif self.playState==StateEnum.OFF:
                print('Song Mode')
                self.playStatePending=StateEnum.SONG_READY
            elif self.playState==StateEnum.SONG_READY or self.playState==StateEnum.SONG_PLAYING or self.playState==StateEnum.SONG_PLAYING_FAILED:
                print('Riff Mode')
                self.playStatePending=StateEnum.RIFF_READY
            elif self.playState==StateEnum.RIFF_READY or self.playState==StateEnum.RIFF_PLAYING:
                print('Off')
                self.playStatePending=StateEnum.OFF

    def drumEvent(self, isOn, stateChangeAt):
        if isOn:
            self.drums[0].play()

    def play(self):
        #Always on        
        self.acc.tapDownWatch.addWatch(self.commandTapEvent)

        #Start the game loop        
        while not self.stopMainLoop:
            if self.playState == StateEnum.OFF:
                #On State Entry
                if self.lastPlayState!=self.playState:
                    self.stateData={}
                    pygame.mixer.music.fadeout(1000)                    
                    pygame.mixer.stop()
                    self.acc.handUpWatch.removeWatch(self.crowdSoundEvent)
                    self.acc.tapUpWatch.removeWatch(self.drumEvent)

            #Wait for a hand raise to start
            elif self.playState == StateEnum.SONG_READY:
                #On State Entry
                if self.lastPlayState!=self.playState:
                    self.acc.handUpWatch.addWatch(self.crowdSoundEvent)
                    #self.acc.tapUpWatch.addWatch(self.drumEvent)
                    self.stateData={}
                    self.stateData["handUpPassed"]=False

                #If the hand goes up, mark it
                if self.acc.handUpWatch.on:
                    self.stateData["handUpPassed"]=True
                #If the hand was up and now isn't start
                elif self.stateData["handUpPassed"]:
                    beatIndex=0
                    beatFudge=0.25
                    beatsMissed=0

                    stoppedPlaying=False
                    stoppedAtOffset=None
                    songStart=time.time()
                    pygame.mixer.music.play()

                    self.playStatePending=StateEnum.SONG_PLAYING

                #On State Exit
                if self.lastPlayState==StateEnum.SONG_READY and self.playState!=self.lastPlayState:
                    pass

            #Play it 
            elif self.playState == StateEnum.SONG_PLAYING:
                #Is the song over
                if not pygame.mixer.music.get_busy():
                    self.playStatePending = StateEnum.SONG_READY
                
                #Else if we have beats left
                elif beatIndex<len(self.beats):
                    currentOffset = time.time()-songStart
                    nextBeatOffset = self.beats[beatIndex] 

                    #Are we in the window to expect a beat and did we get one
                    #print('Next: {} Current {}'.format(nextBeatOffset,currentOffset))
                    if abs(nextBeatOffset - currentOffset) <= beatFudge:
                        if self.acc.moveWatch.on or abs(nextBeatOffset - self.acc.moveWatch.stateChangeAt) <= beatFudge:
                            #print("Hit at {}".format(self.beats[beatIndex]))
                            beatIndex=beatIndex+1
                            beatsMissed=0            

                    #We missed
                    if nextBeatOffset + beatFudge < currentOffset:
                        print('Miss at {}'.format(self.beats[beatIndex]))
                        self.misses[0].play()
                        self.misses=self.misses[1:] + [self.misses[0]]
                        beatsMissed=beatsMissed+1
                        beatIndex=beatIndex+1
                        if beatsMissed > 5:
                            pygame.mixer.music.pause()
                            pygame.mixer.music.get_pos()
                            stoppedAtOffset = currentOffset
                            stoppedPlaying=True
                            self.playStatePending=StateEnum.SONG_PLAYING_FAILED
                            print('Failed')
                
                #By default, let the song playout

            #Play it 
            elif self.playState == StateEnum.SONG_PLAYING_FAILED:
                #On State Entry
                if self.lastPlayState!=self.playState:
                    print('Enter')
                    self.stateData={}
                    self.stateData["handUpPassed"]=False

                #If the hand goes up, mark it
                if self.acc.handUpWatch.on:
                    self.stateData["handUpPassed"]=True
                #If the hand was up and now isn't resume
                elif self.stateData["handUpPassed"]:
                    beatsMissed=0
                    stoppedPlaying=False
                    songStart = time.time()-stoppedAtOffset
                    pygame.mixer.music.unpause()
                    self.playStatePending=StateEnum.SONG_PLAYING

                #On State Exit
                if self.lastPlayState==StateEnum.SONG_PLAYING_FAILED and self.playState!=self.lastPlayState:
                    #Smash and break stuff disable
                    pass

            elif self.playState == StateEnum.RIFF_READY:
                #On State Entry
                if self.lastPlayState!=self.playState:
                    self.acc.handUpWatch.addWatch(self.crowdSoundEvent)
                    self.stateData={}
                    pygame.mixer.music.fadeout(1000)                    
                    pygame.mixer.stop()

            self.lastPlayState=self.playState
            if self.playStatePending is not None:            
                self.playState=self.playStatePending
                self.playStatePending=None

                if self.playState==StateEnum.OFF:
                    self.commands[0].play()                
                    time.sleep(self.commands[0].get_length())
                elif self.playState==StateEnum.SONG_READY:
                    self.commands[4].play()
                    time.sleep(self.commands[4].get_length())
                elif self.playState==StateEnum.RIFF_READY:
                    self.commands[5].play()
                    time.sleep(self.commands[5].get_length())

            #Framerate of 100
            self.pyClock.tick(100)

    def shutdown(self):
        pygame.mixer.music.stop()
        pygame.quit()
        sys.exit()

#Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('song', help='.wav file of the song to play')
parser.add_argument('-mode', default="solo", help='play mode, [solo]')
args = parser.parse_args()

#Startup the game
#sudo amixer cset numid=1 100%
game=AirGuitarGame(args.song, args.mode)
game.play()
game.shutdown()