import math, time, threading
import mma8451

class StateWatch():
    def __init__(self, predicate, timeToOn=0, timeToOff=0):
        self.predicate=predicate

        self.timeToOn = timeToOn
        self.timeToOff = timeToOff
        self.lastTransition = None

        self.watches=[]

        self.on = False
        self.stateChangeAt = time.time()

    def tick(self):
        isOn = self.predicate()
        #If we are on
        if self.on:
            #If sensor says we are off
            if not isOn:
                #If we already have been here, watch the time and go off when it is time
                if self.lastTransition is not None or self.timeToOff==0:
                    if self.timeToOff==0 or time.time() - self.lastTransition > self.timeToOff:
                        self.stateChangeAt = time.time()
                        self.lastTransition=None
                        self.on=False    
                        self._onChange()
                #First try, so start the timer
                else:
                    self.lastTransition=time.time()

            #Reset the timer
            else:
                self.lastTransition=None

        #If we are off
        else:
            #If sensor says we are on
            if isOn:
                #If we already have been here, watch the time and go off when it is time
                if self.lastTransition is not None or self.timeToOn==0:
                    if self.timeToOn==0 or time.time() - self.lastTransition > self.timeToOn:
                        self.stateChangeAt = time.time()
                        self.lastTransition=None
                        self.on=True
                        self._onChange()
                #First try, so start the timer
                else:
                    self.lastTransition=time.time()

            #Reset the timer
            else:
                self.lastTransition=None

    def _onChange(self):
        for cb in self.watches:
            cb(self.on, self.stateChangeAt)

    def addWatch(self, callback):
        self.watches.append(callback)
    def removeWatch(self, callback):
        while callback in self.watches:
            self.watches.remove(callback)

class AccelCommands(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

        self.sensor = mma8451.MMA8451()
        self.ca = (0,0,0)   #Current accelerations
        self.la = (0,0,0)   #Last accelerations
        self.cvmag = 0      #Magnitude of current acceleration
        self.lvmag = 0      #Magnitude of last acceleration

        def moveMonitor():
            #print(abs(self.cvmag - 9.8))
            return abs(self.cvmag - 9.8) > 2.0

        def handUpMonitor():
            if not self.moveWatch.on and self.ca[1] < -8.8 and self.ca[1] > -10.8:
                return True
            return False

        def handDownMonitor():
            if not self.moveWatch.on and self.ca[1] > 8.8 and self.ca[1] < 10.8:
                return True
            return False

        self.downAt = None
        self.lastDownTrigger = time.time()
        def tapDownMonitor():            
            if self.downAt is None:
                if self.ca[1] > 8.8 and self.ca[1] < 10.8:
                    self.downAt=time.time()
            else:
                if not (self.ca[1] > 7.0 and self.ca[1] < 15):
                    #print(self.ca)
                    self.downAt=None
                elif time.time()-self.downAt > 2.0:
                    if abs(self.ca[2]) > 5:
                        if time.time() - self.lastDownTrigger > 0.1:
                            #print(self.ca)
                            self.lastDownTrigger = time.time()
                            return True
            return False

        self.upAt = None
        self.madeItUp = False
        self.comeDownAt = time.time()
        self.lastUpTrigger = time.time()
        def tapUpMonitor():     
            if not self.madeItUp:
                if self.upAt is None:
                    if self.ca[1] < -8.8 and self.ca[1] > -10.8:
                        self.upAt=time.time()
                else:
                    if not (self.ca[1] < -8.8 and self.ca[1] > -10.8):
                        self.upAt=None
                    elif time.time()-self.upAt > 2.0:
                        print('Up')
                        self.madeItUp=True

            else:
                if self.cvmag > 30:
                    if time.time() - self.lastUpTrigger > 0.25:
                        print(self.ca)
                        self.lastUpTrigger = time.time()
                        return True

                if self.comeDownAt is None:
                    if self.ca[1] > 8.8 and self.ca[1] < 10.8:
                        self.comeDownAt=time.time()
                else:
                    if not (self.ca[1] > 8.8 and self.ca[1] < 10.8):
                        self.comeDownAt=None
                    elif time.time()-self.comeDownAt > 1.0:
                        print('Down')
                        self.madeItUp=False
                        self.upAt=None
                        self.comeDownAt=None

            return False

        self.handUpWatch = StateWatch(handUpMonitor, timeToOn=1.0, timeToOff=0.2)
        self.handDownWatch = StateWatch(handDownMonitor, timeToOn=1.0, timeToOff=0.2)
        self.tapDownWatch = StateWatch(tapDownMonitor, timeToOn=0.0, timeToOff=0.0)
        self.tapUpWatch = StateWatch(tapUpMonitor, timeToOn=0.0, timeToOff=0.0)
        self.moveWatch = StateWatch(moveMonitor)

        self._watches=[self.moveWatch, self.handUpWatch, self.handDownWatch, self.tapDownWatch]

    def calcVals(self, lastv, curv, maxdv, mindv, maxv, minv):
        #dv, maxdv, mindv, maxv, minv
        dv = abs(curv-lastv)
        if dv > abs(maxdv):
            maxdv=dv
        if dv < abs(mindv):
            mindv=dv
        if maxv > abs(curv):
            maxv=curv
        if minv < abs(curv):
            minv=curv
        return (curv, dv, maxdv, mindv, maxv, minv)

    def run(self):
        freq=1/100
        avgOver=10
        avgDX=[0]*avgOver
        avgDY=[0]*avgOver
        avgDZ=[0]*avgOver
        maxDX, maxDY, maxDZ=0,0,0
        minDX, minDY, minDZ=0,0,0
        maxX, maxY, maxZ=0,0,0
        minX, minY, minZ=0,0,0

        moveThresh=0.5

        lx,ly,lz = self.la = self.sensor.acceleration
        ll = self.lvmag = math.sqrt(lx*lx + ly*ly + lz*lz)
        while True:
            x, y, z = self.ca = self.sensor.acceleration
            l = self.cvmag = math.sqrt(x*x + y*y + z*z)

            for m in self._watches:
                m.tick()

            #lx, dx, maxDX, minDX, maxX, minX = self.calcVals(lx, x, maxDX, minDX, maxX, minX)
            #ly, dy, maxDY, minDY, maxY, minY = self.calcVals(ly, y, maxDY, minDY, maxY, minY)
            #lz, dz, maxDZ, minDZ, maxZ, minZ = self.calcVals(lz, z, maxDZ, minDZ, maxZ, minZ)

                #print('accelerating')
            #else:
                #print('constant')

            #print(y)

            #print(l)
            # if maxDX > moveThresh or maxDY > moveThresh or maxDZ > moveThresh:
            #     if self.moving
            #     self.moving=True
            # else:
            #     self.moving=False
            # avgDX=[1:]+dx
            # avgDY=[1:]+dy
            # avgDZ=[1:]+dz

            # if dx > maxDX: 
            #     maxDX=dx
            # if dy > maxDX: 
            #     maxDX=dx
            # if dx > maxDX: 
            #     maxDX=dx

            # if lx-x
            #print('Acceleration: x={0:0.3f}m/s^2 y={1:0.3f}m/s^2 z={2:0.3f}m/s^2'.format(x, y, z))

            time.sleep(1/100)            
