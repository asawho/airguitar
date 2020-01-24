    #For training mode we use the keyboard to detect input not the shaking hand crap
    if args.mode=="train":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done=True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done=True
                lastBeatOffset = time.time() - songStart
                taps.append(lastBeatOffset)

        #If we are in easy mode, all we require is that one strum have taken place
        if args.mode == "easy":
            if not stoppedPlaying:
                currentOffset = time.time()-songStart
                #print(currentOffset)

                #Are we in the window to expect a beat
                if abs(beats[beatIndex] - currentOffset) <= beatFudge:
                    #print('In window, taps={}'.format(len(taps)))
                    #We got a beat, move on (later, say it has to be in the window)
                    if len(taps)>0:
                        beatIndex=beatIndex+1
                        beatsMissed=0
                        taps=[]

                #We missed a beat
                elif beats[beatIndex] - currentOffset < -beatFudge:
                    print('Missing {}'.format(beatsMissed))
                    beatsMissed=beatsMissed+1
                    beatIndex=beatIndex+1
                    if beatsMissed > 2:
                        pygame.mixer.music.pause()
                        pygame.mixer.music.get_pos()
                        stoppedAtOffset = currentOffset
                        stoppedPlaying=True
                        print('Failed')

            else:
                #Did we get a strum to start back up
                if len(taps) > 0:
                    beatsMissed=0
                    stoppedPlaying=False
                    songStart = time.time()-stoppedAtOffset
                    pygame.mixer.music.unpause()
