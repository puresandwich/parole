
import parole, traceback, sys, random
import test
import pygame

boobspot = 0
sdr = None

@test.test()
def t_colorfield():
        global sdr
        
        def handleCommand(command):
            global sdr
            if command == 'quit':
                raise parole.ParoleShutdown
            elif command == 'fps':
                fps = parole.display.framerate()
                parole.info("FPS: %s", fps)
            elif command == 'move right':
                sdr.pos = (sdr.pos[0]+5, sdr.pos[1])
            elif command == 'move left':
                sdr.pos = (sdr.pos[0]-5, sdr.pos[1])
            elif command == 'move up':
                sdr.pos = (sdr.pos[0], sdr.pos[1]-5)
            elif command == 'move down':
                sdr.pos = (sdr.pos[0], sdr.pos[1]+5)
        
        if test.firstUpdate:
            parole.info("----> Press some keys. 'q' quits.")
            parole.info("----> 'F' logs the framerate.")
            test.firstUpdate = False
            parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                              handleCommand))
            sdr = parole.shader.Shader("testshader", (50,50), (150,150))
            field = parole.shader.ColorField((255,255,255), (0,0), (150,150))
            #field.alpha = 50
            sdr.addPass(field, parole.shader.BLEND)
            parole.display.scene.add(sdr)

        #tex = parole.resource.getTexture('saveavirgin.jpg')
        surf = parole.display.getSurface()
        surf.fill((0,0,0))
        #surf.blit(tex, (0+boobspot,0))
        
        #if surf.get_width() - boobspot < tex.get_width():
        #    boobspot = 0
        #else:
        #    boobspot += 1

@test.test()
def t_resource():
        if test.firstUpdate:
            test.firstUpdate = False
            parole.info('Attempting to load a text resource...')
            text = parole.resource.getResource('text/test.txt')
            parole.info('"%s"', text)
        else:
            parole.info('All done!')
            raise parole.ParoleShutdown


data = {}
@test.test()
def t_textpass():
    def handleCommand(command):
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'fps':
            fpsTxt = parole.shader.TextLinePass(
                    str(parole.display.framerate()),
                    (0,0), data['font'], True,
                    (255,0,0), 255
                )
            data['sdr'].clearPasses()
            data['sdr'].addPass(fpsTxt, parole.shader.BLEND)
            data['sdr'].size = fpsTxt.size

    if test.firstUpdate:
        test.firstUpdate = False
        #font = pygame.font.SysFont("Courier New", 24)
        #font = pygame.font.Font("monaco.ttf", 24)
        parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                          handleCommand))
        font = parole.resource.getFont("fonts/monaco.ttf", 24)
        parole.info('Creating textpass')
        txt = parole.shader.TextLinePass("Hello, World!", (0,0), font,
                True, (255,255,255), 255)
        sdr = parole.shader.Shader("testshader", (50,50), txt.size)
        sdr.addPass(txt, parole.shader.BLEND)
        parole.display.scene.add(sdr)
        data['sdr'] = sdr
        data['font'] = font
        parole.info("'q' quits, space updates onscreen TextLinePass with framerate.")

    surf = parole.display.getSurface()
    surf.fill((0,0,0))

@test.test()
def t_texturepass():
    def handleCommand(command):
        sdr = data['sdr']
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'fps':
            fps = parole.display.framerate()
            parole.info("FPS: %s", fps)
        elif command == 'move right':
            sdr.pos = (sdr.pos[0]+5, sdr.pos[1])
        elif command == 'move left':
            sdr.pos = (sdr.pos[0]-5, sdr.pos[1])
        elif command == 'move up':
            sdr.pos = (sdr.pos[0], sdr.pos[1]-5)
        elif command == 'move down':
            sdr.pos = (sdr.pos[0], sdr.pos[1]+5)
        
    if test.firstUpdate:
        test.firstUpdate = False
        parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                          handleCommand))
        parole.info("Creating texture pass")
        #texture = parole.shader.TexturePass(pygame.image.load("condie.jpg"), (0,0))
        texture = parole.shader.TexturePass("textures/condie.jpg", (0,0))
        sdr = parole.shader.Shader("testshader", (100,100), texture.size)
        sdr.addPass(texture, parole.shader.BLEND)
        parole.display.scene.add(sdr)
        data['sdr'] = sdr
        parole.info("Arrows move Condie, 'F' logs framerate, 'q' quits.")
        
    parole.display.getSurface().fill((0,0,0))

@test.test()
def t_textgrid():
    def drawGrid():
        parole.display.scene.empty()
        scrsize = parole.display.getSurface().get_size()
        x = x0 = (scrsize[0] - (scrsize[0] / data['charwidth'])*data['charwidth']) / 2
        y = y0 = (scrsize[1] - (scrsize[1] / data['lineheight'])*data['lineheight']) / 2

        while y + data['lineheight'] < scrsize[1]:
            while x + data['charwidth'] < scrsize[0]:
                sdr = parole.shader.Shader("grid%s,%s" % (x,y), (x,y), 
                                           (data['charwidth'], data['lineheight']))
                sdr.addPass(parole.shader.TextLinePass(data['gridchar'], (0,0), data['font'], True, (255,255,255), 255),
                            parole.shader.BLEND)
                parole.display.scene.add(sdr)
                x += data['charwidth']
            y += data['lineheight']
            x = x0
            
    def handleCommand(command):
        if command == "quit":
            raise parole.ParoleShutdown
            
    if test.firstUpdate:
        test.firstUpdate = False
        parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                          handleCommand))
        font = parole.resource.getFont("fonts/monaco.ttf", 16)
        data['font'] = font
        data['lineheight'] = font.get_linesize()
        data['charwidth'] = font.size('W')[0]
        data['gridchar'] = 'x'
        drawGrid()
        parole.info("'q' quits, any other key sets new grid character.")
    
        
    for key in parole.input.peekKeyPresses():
        if len(key) == 1:
            data['gridchar'] = key
            t = parole.time()
            for sdr in parole.display.scene:
                for p in sdr.passes:
                    p.text = key
            t = parole.time() - t
            parole.info("Refresh time: %sms", t)
        
    parole.display.getSurface().fill((0,0,0))
        
tmap = None


# NOTE: deprecated by new Map interface. See more sophisticated test t_walk.
@test.test()
def t_map():
    global tmap
    
    def handleCommand(command):
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'move right':
            tmap.viewportPos = (tmap.viewportPos[0]+1, tmap.viewportPos[1])
        elif command == 'move left':
            tmap.viewportPos = (tmap.viewportPos[0]-1, tmap.viewportPos[1])
        elif command == 'move down':
            tmap.viewportPos = (tmap.viewportPos[0], tmap.viewportPos[1]+1)
        elif command == 'move up':
            tmap.viewportPos = (tmap.viewportPos[0], tmap.viewportPos[1]-1)
            
    if test.firstUpdate:
        test.firstUpdate = False
        parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                          handleCommand))
        tmap = parole.map.Map2D('Test Map', (0,0), parole.display.getSurface().get_size(),
                             (80,25))
        
        for y in range(tmap.rows):
            for x in range(tmap.cols):
                tmap.add((x,y), 
                         parole.map.MapObject(0, 
                                              parole.map.AsciiPass(str(y)[-1], 
                                                                   ((5*x)%255,(5*y)%255,255))))
        parole.display.scene.add(tmap)
    
    parole.display.getSurface().fill((0,0,0))
        
@test.test()
def t_walk():
    class Floor(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, -1, 
                                          parole.map.AsciiPass('.', (127,150,127)))
            
        def __str__(self):
            return "the floor"
        
    class Player(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, 100,
                                          parole.map.AsciiPass('@', (255,64,64)))
            
        def __str__(self):
            return 'the player'
            
    class Wall(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, 0,
                                          parole.map.AsciiPass('#', (196,196,196)))
            
        def __str__(self):
            return "the wall"
        
    class Trap(parole.map.MapObject):
        def __init__(self):
            self.name, rgb = random.choice(
                [("Sandy's cock", (255,255,255)), 
                 ("Max's cock", (200,0,0)), 
                 ("John's cock", (0,200,0)),
                 ("Julie's VAGINA-TEETH", (0,0,200)),
                 ("Rick's cock", (255,255,0))])
            parole.map.MapObject.__init__(self, 0,
                                          parole.map.AsciiPass('^', rgb))
            
        def __str__(self):
            return self.name
        
        def trigger(self):
            data['msg3Shader'].text += " You stumble into %s! [more]" % (self,)
            def next(who):
                # This is definitely a suboptimal way of doing this
                parole.popUIEventHandler()
                data['msg3Shader'].text = "You are raped without mercy by %s! You die." % (who,)
                parole.pushUIEventHandler(lambda e: e.type==pygame.KEYDOWN and parole.shutdown() or None)
                
            parole.pushUIEventHandler(lambda event: event.type == pygame.KEYDOWN and next(self) or None)
            
    def handleWalk(command):
        displacement = (0,0)
        if command == 'north':
            displacement = (0,-1)
        elif command == 'south':
            displacement = (0, 1)
        elif command == 'east':
            displacement = (1, 0)
        elif command == 'west':
            displacement = (-1, 0)
        elif command == 'northeast':
            displacement = (1,-1)
        elif command == 'northwest':
            displacement = (-1, -1)
        elif command == 'southeast':
            displacement = (1, 1)
        elif command == 'southwest':
            displacement = (-1,1)
            
        player = data['player']
        map = data['walkmap']
        curPos = player.pos
        newPos = (curPos[0] + displacement[0], curPos[1] + displacement[1])
        
        # Punish the player for leaving the map
        if newPos[0] < 0 or newPos[0] >= map.cols or newPos[1] < 0 or newPos[1] >= map.rows:
            data['msg3Shader'].text = "You fall off the map, asshole. You die."
            map.remove(curPos, player)
            parole.pushUIEventHandler(lambda event: event.type == pygame.KEYDOWN \
                                                    and parole.shutdown() or None)
            return
        
        # wall collisions
        for obj in map.tileAt(newPos):
            if isinstance(obj, Wall):
                data['msg3Shader'].text = "You bump into %s." % (obj,)
                return
        
        # Move the player
        data['msg3Shader'].text = "You walk %s." % (command,)
        map.remove(curPos, player)
        map.add(newPos, player)
        
        # Potentially trigger a trap
        for obj in map.tileAt(newPos):
            if isinstance(obj, Trap):
                if random.random() < 0.33:
                    # the trap is triggered
                    obj.trigger()
                else:
                    # trap evaded
                    data['msg3Shader'].text += " You deftly evade %s." % (obj,)
    
    def handleTest(command):
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'move right':
            data['walkmap'].viewportPos = (data['walkmap'].viewportPos[0]+1, 
                                           data['walkmap'].viewportPos[1])
        elif command == 'move left':
            data['walkmap'].viewportPos = (data['walkmap'].viewportPos[0]-1, 
                                           data['walkmap'].viewportPos[1])
        elif command == 'move down':
            data['walkmap'].viewportPos = (data['walkmap'].viewportPos[0], 
                                           data['walkmap'].viewportPos[1]+1)
        elif command == 'move up':
            data['walkmap'].viewportPos = (data['walkmap'].viewportPos[0], 
                                           data['walkmap'].viewportPos[1]-1)
    
    if test.firstUpdate:
        test.firstUpdate = False
        walkCommands = parole.input.CommandMap(parole.conf.commands.walkcommands,
                                               handleWalk, peek=True)
        testCommands = parole.input.CommandMap(parole.conf.commands.testcommandset,
                                               handleTest, peek=False)
        parole.pushUIEventHandler((walkCommands, testCommands))
        
        scrsize = parole.display.getSurface().get_size()
        txtfont = parole.resource.getFont('fonts/monaco.ttf', 16)
        textsize = (scrsize[0], txtfont.get_linesize()*3)
        msg1Shader = parole.shader.TextLinePass("Howdy! Use numpad (or vi keys) to move, arrows to scroll map,", 
                                            (3,0), txtfont, True, (200,200,200), 255)
        msg2Shader = parole.shader.TextLinePass("`q' to quit.", 
                                            (3,txtfont.get_linesize()), txtfont, True, (200,200,200), 255)
        data['msg3Shader'] = parole.shader.TextLinePass("", 
                                            (3,txtfont.get_linesize()*2), txtfont, True, (200,200,200), 255)
        parole.display.scene.add(msg1Shader)
        parole.display.scene.add(msg2Shader)
        parole.display.scene.add(data['msg3Shader'])
        
        COLS, ROWS = 80,80
        mapsize = (scrsize[0], scrsize[1] - txtfont.get_linesize()*3)
        mappos = (0, txtfont.get_linesize()*3)
        data['walkmap'] = parole.map.Map2D('Walk Map', mappos, mapsize, (COLS, ROWS),
                                           parole.map.AsciiPass.characterSize())
        
        # place the players map object
        playerStartPos = (10,10) #(COLS/2, ROWS/2)
        data['player'] = Player()
        data['walkmap'].add(playerStartPos, data['player'])
        
        time = parole.time()
        
        # fill the map with objects
        for col in range(COLS):
            for row in range(ROWS):
                # floor
                data['walkmap'].add((col,row), Floor())
                
                # wall or trap or nothing
                item = random.choice([Wall, Trap, None, None, None, None, None, None, None, None])
                if item and (col,row) != playerStartPos:
                    data['walkmap'].add((col, row), item())
                    
        time = parole.time() - time
        parole.info('Map creation time (%s x %s): %s => %s tiles per second.', 
                    COLS, ROWS, time, (float(COLS*ROWS) / float(time))*1000.0)
                
        parole.display.scene.add(data['walkmap'])
        
    parole.display.getSurface().fill((0,0,0))
        
@test.test('ziptest.cfg')
def t_zip():
    
    if test.firstUpdate:
        test.firstUpdate = False
        parole.info('Bazongas!')
        raise parole.ParoleShutdown

tests = [t_resource, t_colorfield, t_texturepass, t_textpass, t_textgrid, t_walk]
#tests = [t_walk]

def main():
    test.runTests(tests)
    test.summary()


if __name__ == "__main__":
    main()
