
import parole, traceback, sys, random, gc
import test
import pygame

boobspot = 0
sdr = None

@test.test()
def t_colorfield():
        global sdr
        scene = parole.display.scene
        
        def handleCommand(command):
            global sdr
            if command == 'quit':
                raise parole.ParoleShutdown
            elif command == 'fps':
                fps = parole.display.framerate()
                parole.info("FPS: %s", fps)
            elif command == 'move right':
                scene.positionOf[sdr] = (scene.positionOf[sdr][0]+5, scene.positionOf[sdr][1])
            elif command == 'move left':
                scene.positionOf[sdr] = (scene.positionOf[sdr][0]-5, scene.positionOf[sdr][1])
            elif command == 'move up':
                scene.positionOf[sdr] = (scene.positionOf[sdr][0], scene.positionOf[sdr][1]-5)
            elif command == 'move down':
                scene.positionOf[sdr] = (scene.positionOf[sdr][0], scene.positionOf[sdr][1]+5)
        
        if test.firstUpdate:
            parole.info("----> Press some keys. 'q' quits.")
            parole.info("----> 'F' logs the framerate.")
            test.firstUpdate = False
            parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                              handleCommand))
            sdr = parole.shader.Shader("testshader", (150,150))
            field = parole.shader.ColorField((255,255,255), (150,150))
            sdr.addPass(field)
            subsdr = parole.shader.Shader("subshader", (40,40))
            subsdr.addPass(parole.shader.ColorField((255,0,0), (10,10)),
                    pos=(10,10))
            sdr.addPass(subsdr, pos=(20,5))
            parole.display.scene.add(sdr, pos=(50,50))

        surf = parole.display.getSurface()
        surf.fill((0,0,0))

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
def t_texturepass():
    scene = parole.display.scene
    def handleCommand(command):
        sdr = data['sdr']
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'fps':
            fps = parole.display.framerate()
            parole.info("FPS: %s", fps)
        elif command == 'move right':
            scene.positionOf[sdr] = (scene.positionOf[sdr][0]+5, scene.positionOf[sdr][1])
        elif command == 'move left':
            scene.positionOf[sdr] = (scene.positionOf[sdr][0]-5, scene.positionOf[sdr][1])
        elif command == 'move up':
            scene.positionOf[sdr] = (scene.positionOf[sdr][0], scene.positionOf[sdr][1]-5)
        elif command == 'move down':
            scene.positionOf[sdr] = (scene.positionOf[sdr][0], scene.positionOf[sdr][1]+5)
        
    if test.firstUpdate:
        test.firstUpdate = False
        parole.pushUIEventHandler(parole.input.CommandMap(parole.conf.commands.testcommandset,
                                                          handleCommand))
        parole.info("Creating texture pass")
        texture = parole.shader.TexturePass("textures/condie.jpg")
        sdr = parole.shader.Shader("testshader", texture.size)
        sdr.addPass(texture)
        scene.add(sdr, pos=(100,100))
        data['sdr'] = sdr
        parole.info("Arrows move Condie, 'F' logs framerate, 'q' quits.")
        
    parole.display.getSurface().fill((0,0,0))

        

# TODO: We need to be able to use shaders efficiently like this. Currently
# doesn't work... the shaders get moved around a bunch and only show up at
# last location. 
def init_t_walk():
    global floorGlyph, playerGlyph, wallGlyph, traps
    floorGlyph = parole.map.AsciiTile('.', (127,150,127))
    playerGlyph = parole.map.AsciiTile('@', (255,64,64))
    wallGlyph = parole.map.AsciiTile('#', (196,196,196))
    traps = {
            "{\\White Sandy's cock}": parole.map.AsciiTile('^', (255,255,255)), 
            "{\\Red Max's cock}": parole.map.AsciiTile('^', (200,0,0)), 
            "{\\Green John's cock}": parole.map.AsciiTile('^', (0,200,0)),
            "{\\Blue Julie's VAGINA-TEETH}": parole.map.AsciiTile('^', (0,0,200)),
            "{\\Yellow Rick's cock}": parole.map.AsciiTile('^', (255,255,0))
        }

@test.test()
def t_walk():
    class Floor(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, -1, 
                floorGlyph)
            
        def __str__(self):
            return "the floor"
        
    class Player(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, 100,
                playerGlyph)
            
        def __str__(self):
            return 'the player'
            
    class Wall(parole.map.MapObject):
        def __init__(self):
            parole.map.MapObject.__init__(self, 0,
                wallGlyph)
            
        def __str__(self):
            return "the wall"
        
    class Trap(parole.map.MapObject):
        def __init__(self):
            self.name, glyph = random.choice(traps.items())
            parole.map.MapObject.__init__(self, 0,
                 glyph)
            
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
        startTime = parole.time()
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
            data['mapframe'].scrollTiles(1, 0)
        elif command == 'move left':
            data['mapframe'].scrollTiles(-1, 0)
        elif command == 'move down':
            data['mapframe'].scrollTiles(0, 1)
        elif command == 'move up':
            data['mapframe'].scrollTiles(0, -1)
    
    if test.firstUpdate:
        test.firstUpdate = False
        init_t_walk()

        walkCommands = parole.input.CommandMap(parole.conf.commands.walkcommands,
                                               handleWalk, peek=True)
        testCommands = parole.input.CommandMap(parole.conf.commands.testcommandset,
                                               handleTest, peek=False)
        parole.pushUIEventHandler((walkCommands, testCommands))
        
        scrsize = parole.display.getSurface().get_size()
        txtfont = parole.resource.getFont('fonts/monaco.ttf', 16)
        textsize = (scrsize[0], txtfont.get_linesize()*3)
        msg1Shader = parole.shader.TextBlockPass(txtfont,
                (200,200,200), text="Howdy! Use numpad (or vi keys) "\
                        "to move, arrows to scroll map,") 
        msg2Shader = parole.shader.TextBlockPass(txtfont, (200,200,200),
                text="`q' to quit.") 
        data['msg3Shader'] = parole.shader.TextBlockPass(txtfont,
                (200,200,200))
        parole.display.scene.add(msg1Shader, pos=(3, 0))
        parole.display.scene.add(msg2Shader, pos=(3, txtfont.get_linesize()))
        parole.display.scene.add(data['msg3Shader'], 
            pos=(3, txtfont.get_linesize()*2))

        gc.set_debug(gc.DEBUG_LEAK)
        
        sys.stderr.write('Count A: %s\n' % len(gc.get_objects()))
        sys.stderr.flush()
        # Map setup
        COLS, ROWS = parole.conf.walkoptions.cols, parole.conf.walkoptions.rows
        data['walkmap'] = parole.map.Map2D('Walk Map', (COLS, ROWS))
        sys.stderr.write('Count B: %s\n' % len(gc.get_objects()))
        sys.stderr.flush()
        mapsize = (scrsize[0], scrsize[1] - txtfont.get_linesize()*3)
        mappos = (0, txtfont.get_linesize()*3)
        tileSize = parole.map.AsciiTile.characterSize()
        data['mapframe'] = parole.map.MapFrame(mapsize, tileSize=tileSize)
        
        # place the players map object
        playerStartPos = (10,10) #(COLS/2, ROWS/2)
        data['player'] = Player()
        data['walkmap'].add(playerStartPos, data['player'])
        
        time = parole.time()
        
        # fill the map with objects
        for col in xrange(COLS):
            for row in xrange(ROWS):
                # floor
                data['walkmap'].add((col,row), Floor())
                
                # wall or trap or nothing
                item = random.choice([Wall, Trap] + [None]*8)
                if item and (col,row) != playerStartPos:
                    data['walkmap'].add((col, row), item())
            #sys.stderr.write('Count C: %s\n' % len(gc.get_objects()))
            #sys.stderr.flush()
                    
        time = parole.time() - time
        parole.info('Map creation time (%s x %s): %s => %s tiles per second.', 
                    COLS, ROWS, time, (float(COLS*ROWS) / float(time))*1000.0)

        data['mapframe'].setMap(data['walkmap'])

        parole.display.scene.add(data['mapframe'], pos=mappos)
        sys.stderr.write('Count D: %s\n' % len(gc.get_objects()))
        sys.stderr.flush()
        
    parole.display.getSurface().fill((0,0,0))
        
@test.test('ziptest.cfg')
def t_zip():
    
    if test.firstUpdate:
        test.firstUpdate = False
        parole.info('Bazongas!')
        raise parole.ParoleShutdown
    

loremIpsum = \
'''Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia deserunt mollit anim id est laborum. '''

block = None
frame = None

@test.test()
def t_textblock():
    global sdr, frame, block, scroller
    
    def handleCommand(command):
        global sdr, frame, block
        if command == 'quit':
            raise parole.ParoleShutdown
        elif command == 'fps':
            fps = parole.display.framerate()
            parole.info("FPS: %s", fps)
        elif command == 'move right':
            parole.display.scene.positionOf[frame] = (parole.display.scene.positionOf[frame][0]+5, parole.display.scene.positionOf[frame][1])
        elif command == 'move left':
            parole.display.scene.positionOf[frame] = (parole.display.scene.positionOf[frame][0]-5, parole.display.scene.positionOf[frame][1])
        elif command == 'move up':
            parole.display.scene.positionOf[frame] = (parole.display.scene.positionOf[frame][0], parole.display.scene.positionOf[frame][1]-5)
        elif command == 'move down':
            parole.display.scene.positionOf[frame] = (parole.display.scene.positionOf[frame][0], parole.display.scene.positionOf[frame][1]+5)
        elif command == 'scroll right':
            scroller.scrollPixels(10, 0)
        elif command == 'scroll left':
            scroller.scrollPixels(-10, 0)
        elif command == 'scroll up':
            scroller.scrollPixels(0, -10)
        elif command == 'scroll down':
            scroller.scrollPixels(0, 10)
    
    if test.firstUpdate:
        parole.info("----> Press some keys. 'q' quits.")
        parole.info("----> 'F' logs the framerate.")
        test.firstUpdate = False
        parole.pushUIEventHandler((parole.input.CommandMap(parole.conf.commands.testcommandset,
            handleCommand, peek=True),
            parole.input.CommandMap(parole.conf.commands.scrollcommands,
                handleCommand)))
        sdr = parole.shader.Shader("FrameContents", (300,450))
        field = parole.shader.ColorField((0,64,128), (300,450))
        sdr.addPass(field)
        font = parole.resource.getFont("fonts/Arial.ttf", 14)
        block = parole.shader.TextBlockPass(font, (255,255,255),
                wrap_width=274, bg_rgb=(0,64,128), align='left', wrap='word')
        #block.text = 'Sweet\nlittle\nannie banany\tis perc\vhed atop the back of my chair. She is most lovely, is she not?'
        block.text = ' '.join(loremIpsum.split('\n'))*5
        scroller = parole.shader.ScrollView((280,430), contents=[block],
                vbar=parole.shader.VerticalScrollbar((255,255,255),
                    (128,128,128), 5), followY=False)
        sdr.addPass(scroller, pos=(10,10))
        #sdr.addPass(block, pos=(10,10))

        sdr2 = parole.shader.Shader("BareTextShader", (100,100))
        sdr2.addPass(parole.shader.TextBlockPass(font, (255,255,255),
            text="Fags ahoy!"))
        parole.display.scene.add(sdr2, pos=(470, 10))

        frame = parole.shader.Frame((parole.shader.VerticalBevel((0,0,0), 
            (128,128,128), (255,255,255),1, 2, 1),
            parole.shader.VerticalBevel((0,0,0), (128,129,128), (255,255,255), 1, 2, 1),
            parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1, 2, 1),
            parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1, 2, 1),
            None,None,None,None),
            contents=[sdr])
        parole.display.scene.add(frame, pos=(10,10))

    #surf = parole.display.getSurface()
    #surf.fill((0,0,0))

#tests = [t_resource, t_zip, t_colorfield, t_texturepass, t_textblock, t_walk]
tests = [t_walk]

def main():
    #gc.set_debug(gc.DEBUG_LEAK)
    test.runTests(tests)
    test.summary()


if __name__ == "__main__":
    main()
