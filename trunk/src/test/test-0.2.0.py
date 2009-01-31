
import parole, traceback, sys, logging

firstUpdate = True
boobspot = 0
sdr = None

def t_display():
    def update():
        global firstUpdate, boobspot, sdr
        if firstUpdate:
            logging.info("----> Press some keys. 'q' quits.")
            logging.info("----> 'F' logs the framerate.")
            firstUpdate = False
            sdr = parole.shader.Shader("testshader", (50,50), (150,150))
            field = parole.shader.ColorField((255,255,255), (0,0), (150,150))
            #field.alpha = 50
            sdr.addPass(field, "blend")
            parole.display.scene.append(sdr)

        for key in parole.input.getKeyPresses():
            if key == 'q':
                raise parole.ParoleShutdown
            elif key == 'F':
                fps = parole.display.framerate()
                logging.info("FPS: %s", fps)
            elif key == 'right':
                sdr.pos = (sdr.pos[0]+5, sdr.pos[1])
            elif key == 'left':
                sdr.pos = (sdr.pos[0]-5, sdr.pos[1])
            elif key == 'up':
                sdr.pos = (sdr.pos[0], sdr.pos[1]-5)
            elif key == 'down':
                sdr.pos = (sdr.pos[0], sdr.pos[1]+5)
        
        #tex = parole.resource.getTexture('saveavirgin.jpg')
        surf = parole.display.getSurface()
        surf.fill((0,0,0))
        #surf.blit(tex, (0+boobspot,0))
        
        #if surf.get_width() - boobspot < tex.get_width():
        #    boobspot = 0
        #else:
        #    boobspot += 1
        
    parole.startup('test.cfg', update, 'Testing')

def t_resource():
    global firstUpdate
    firstUpdate = True

    def update():
        global firstUpdate
        if firstUpdate:
            firstUpdate = False
            parole.info('Attempting to load a text resource...')
            text = parole.resource.getResource('text/test.txt')
            parole.info('"%s"', text)
        else:
            parole.info('All done!')
            raise parole.ParoleShutdown

    parole.startup('test.cfg', update, 'Resource Testing')

#tests = [t_display]
tests = [t_resource, t_display]
failed = {}

def main():
    for t in tests:
        failed[t] = False
        
    for t in tests:
        print '----------\nTest %s\n----------' % (t.__name__)
        try:
            t()
        except Exception, e:
            traceback.print_exception(type(e), e, sys.exc_traceback)
            print 'Test failed.'
            failed[t] = True
    
    print '\nSummary'
    print 'Pass | Fail | Test'
    for t in tests:
        if failed[t]:
            print '[ ]  | [X]  |', t.__name__
        else:
            print '[X]  | [ ]  |', t.__name__

if __name__ == "__main__":
    main()
