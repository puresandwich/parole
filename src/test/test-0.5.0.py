
import parole, traceback, sys, random, gc
import test
import pygame, pickle, cPickle, bz2
from parole.display import interpolateRGB
from parole.colornames import colors

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


class Player(parole.map.MapObject):
    def __init__(self):
        playerGlyph = parole.map.AsciiTile('@', (255,255,255))
        parole.map.MapObject.__init__(self, 1000,
            playerGlyph)
        
    def __str__(self):
        return 'the player'

player = None

class TestMapObject(parole.map.MapObject):
    def __init__(self, name, layer, shader, blocker=False, passer=False):
        parole.map.MapObject.__init__(self, layer, shader, blocksLOS=blocker)
        self.name = name
        self.blocker = blocker
        self.passer = passer

    def __str__(self):
        return self.name


def makeMap1():
    global player
    # Create map 
    #COLS, ROWS = parole.conf.mapgenoptions.cols, parole.conf.mapgenoptions.rows
    COLS, ROWS = 128, 64
    map = parole.map.Map2D('Test Map', (COLS, ROWS))

    # Populate map with objects

    # Grass (cellular automata)
    grassGenerator = \
        lambda bg_rgb: parole.map.MapObjectGenerator("grassGenerator",
            lambda: TestMapObject('the grass', -200, 
                parole.map.AsciiTile(' ',#random.choice([' ']*3 + [',',';',"'", '"']),
                (random.randint(0,64),random.randint(96,160),random.randint(0,64)),
                bg_rgb=bg_rgb)))
    grassColor = colors['DarkGreen']
    sandColor = colors['Olive']
    grassConditions = {
        0: grassGenerator(interpolateRGB(sandColor, grassColor, 0.0)),
        1: grassGenerator(interpolateRGB(sandColor, grassColor, 0.1)),
        2: grassGenerator(interpolateRGB(sandColor, grassColor, 0.2)),
        3: grassGenerator(interpolateRGB(sandColor, grassColor, 0.3)),
        4: grassGenerator(interpolateRGB(sandColor, grassColor, 0.4)),
        5: grassGenerator(interpolateRGB(sandColor, grassColor, 0.5)),
        6: grassGenerator(interpolateRGB(sandColor, grassColor, 0.6)),
        7: grassGenerator(interpolateRGB(sandColor, grassColor, 0.8)),
        8: grassGenerator(interpolateRGB(sandColor, grassColor, 0.9)),
        9: grassGenerator(interpolateRGB(sandColor, grassColor, 1.0))
    }
    grassAreaGenerator =  parole.map.CellularAutomataGenerator("grassAreaGenerator",
            0.90, grassConditions, seedEdges=True)
    grassAreaGenerator.apply(map)

    # Flowers (cellular automata)
    baseRoseR, baseRoseG, baseRoseB = colors['DarkRed']
    roseGenerator = parole.map.MapObjectGenerator("roseGenerator",
            lambda: TestMapObject('a flower', -2,
                parole.map.AsciiTile('*', (baseRoseR + random.randint(-64,64),
                                           baseRoseG, baseRoseB)), passer=True))
    roseConditions = {
        # num neighbors   # generator
        6: roseGenerator,
        7: roseGenerator,
        8: roseGenerator,
        9: roseGenerator
    }
    roseAreaGenerator = parole.map.CellularAutomataGenerator("roseGenerator",
            0.35, roseConditions) 
    roseAreaGenerator.apply(map)

    # Trees
    baseTreeRGB = colors['ForestGreen']
    autumnTreeRGB = colors['Gold']
    treeGenerator = parole.map.MapObjectGenerator('treeGenerator',
            lambda: TestMapObject('a tree', 50, parole.map.AsciiTile('^',
                interpolateRGB(baseTreeRGB, autumnTreeRGB, max(0.0, min(1.0,
                    random.normalvariate(0.33, 0.3))))), blocker=True))
    forestConditions = {
        5: treeGenerator,
        6: treeGenerator,
        7: treeGenerator,
        8: treeGenerator,
        9: treeGenerator,
    }
    forestGenerator = parole.map.CellularAutomataGenerator("forestGenerator",
            0.25, forestConditions)
    forestGenerator.apply(map)

    # Road (cellular automata)
    baseRoadR, baseRoadG, baseRoadB = colors['SaddleBrown']
    roadGenerator = \
        lambda n: parole.map.MapObjectGenerator("roadGenerator",
            lambda: TestMapObject('the road', -3,
                parole.map.AsciiTile(random.choice([' ']*5 + ['.',"'"]), 
                    colors['SaddleBrown'],
                    bg_rgb=(baseRoadR-(n)*5+random.randint(00,00),
                            baseRoadG-(n)*5+random.randint(00,00),
                            baseRoadB-(n)*5+random.randint(00,00)))))
    roadConditions = {
        3: roadGenerator(3),
        4: roadGenerator(4),
        5: roadGenerator(5),
        6: roadGenerator(6),
        7: roadGenerator(7),
        8: roadGenerator(8),
        9: roadGenerator(9)
    }
    roadAreaGenerator = parole.map.CellularAutomataGenerator("roadGenerator",
            0.50, roadConditions, seedEdges=True, clearFirst=True)
    # road stretches across map centered at y=9, with a height of 5
    roadAreaGenerator.apply(map, pygame.Rect((0,7), (COLS,5)))

    # Rectangular room
    floorGenerator = parole.map.MapObjectGenerator("floorGenerator", 
            lambda: TestMapObject('the floor', 10, parole.map.AsciiTile('.',
                colors['Gray'], bg_rgb=colors['DarkKhaki'])))
    wallGenerator = parole.map.MapObjectGenerator("wallGenerator", 
            lambda: TestMapObject('a wall', 100, parole.map.AsciiTile('#',
                (127,150,127), bg_rgb=(127,150,127)), blocker=True))
    doorGenerator = parole.map.MapObjectGenerator("doorGenerator", 
            lambda: TestMapObject('a door', 100, parole.map.AsciiTile('+',
                colors['White'], bg_rgb=colors['DarkKhaki']), passer=True))
    roomTemplate = \
"""
#######+#######
#.............#
#.............#
#.............#
+.............+
#.............#
#.............#
#.............#
#######+#######
"""
    roomLegend = {  
            '#': wallGenerator,
            '+' : doorGenerator,
            '.' : floorGenerator
        }
    roomGenerator = parole.map.TemplateGenerator("roomGenerator",
            roomTemplate, roomLegend, clearFirst=True)
    map.applyGenerator(roomGenerator, pygame.Rect((25,12), (20,20)))

    # perlin water
    waterGenerator = parole.map.PerlinGenerator("waterGenerator",
            lambda t, n: TestMapObject('some water', 0,
            parole.map.AsciiTile(' ', colors['White'],
                bg_rgb=interpolateRGB(colors['RoyalBlue'],
                    colors['LightBlue'], n))),
            lambda t, r: float(t.col - r.x) / r.w,
            lambda t, r: float(t.row - r.y) / r.h,
            lambda t, r: random.random(), clearFirst=True)
    map.applyGenerator(waterGenerator, pygame.Rect((25, 35), (20, 20)))
    data['waterGenerator'] = waterGenerator


    tree = TestMapObject('a tree', 50, parole.map.AsciiTile('^',
        interpolateRGB(baseTreeRGB, autumnTreeRGB, max(0.0, min(1.0,
            random.normalvariate(0.33, 0.3))))), blocker=True)
    map[0,8].add(tree)
    data['tree'] = tree

    player = Player()
    map[0,9].add(player)

    map.setAmbientLight((255,255,255), 0.7)

    light = parole.map.LightSource(colors['Orange'], 1.0)
    #light.apply(map, (0,9))
    data['light'] = light
    brazier = parole.map.LightSource((255,255,255), 5.0)
    brazier.apply(map, (27,14))
    brazier.copy().apply(map, (27,18))
    brazier.copy().apply(map, (37,14))
    brazier.copy().apply(map, (37,18))
    brazier.copy().apply(map, (32,16))

    map.update()
    return map

def makeMap2():
    # Create map 
    #COLS, ROWS = parole.conf.mapgenoptions.cols, parole.conf.mapgenoptions.rows
    COLS, ROWS = 33, 22
    map = parole.map.Map2D('Test Map', (COLS, ROWS))

    # Populate map with objects
    template = \
"""
123456789ab
"""
    legend = {
            '1': parole.map.MapObjectGenerator('1', 
                lambda: TestMapObject('1', 1, 
                    parole.map.AsciiTile('*', (255,255,255)))),
            '2': parole.map.MapObjectGenerator('2', 
                lambda: TestMapObject('2', 1, 
                    parole.map.AsciiTile('*', (64,64,64)))),
            '3': parole.map.MapObjectGenerator('3', 
                lambda: TestMapObject('3', 1, 
                    parole.map.AsciiTile('*', (255,0,0)))),
            '4': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('4', 1, 
                    parole.map.AsciiTile('*', (0,255,0)))),
            '5': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('5', 1, 
                    parole.map.AsciiTile('*', (0,0,255)))),
            '6': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('6', 1, 
                    parole.map.AsciiTile('*', (255,255,0)))),
            '7': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('7', 1, 
                    parole.map.AsciiTile('*', (0,255,255)))),
            '8': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('8', 1, 
                    parole.map.AsciiTile('*', (255,0,255)))),
            '9': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('8', 1, 
                    parole.map.AsciiTile('*', (64,0,0)))),
            'a': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('8', 1, 
                    parole.map.AsciiTile('*', (0,64,0)))),
            'b': parole.map.MapObjectGenerator('4', 
                lambda: TestMapObject('8', 1, 
                    parole.map.AsciiTile('*', (0,0,64))))
        }
    gen = parole.map.TemplateGenerator('gen', template, legend)
    gen.applyTiled(map)

    return map

def makeMap3():
    map = makeMap2()
    map.setAmbientLight((255,255,255), 0.5)
    return map

def message(text):
    data['msg3Shader'].text = text

def messageBox(text, align='center'):
    font = parole.resource.getFont("fonts/Arial.ttf", 14)
    block = parole.shader.TextBlockPass(font, (255,255,255),
            wrap_width=274, bg_rgb=(0,64,128), align=align, wrap='word')
    block.text = text
    block.update()
    sdr = parole.shader.Shader("FrameContents", 
            (block.width+20, block.height+20))
    sdr.addPass(parole.shader.ColorField((0,64,128), sdr.size))
    sdr.addPass(block, (10,10))
    mbox = parole.shader.Frame((parole.shader.VerticalBevel((0,0,0), 
        (128,128,128), (255,255,255),1, 2, 1),
        parole.shader.VerticalBevel((0,0,0), (128,129,128), (255,255,255), 1, 2, 1),
        parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1,
            2, 1),
        parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1,
            2, 1),
        None,None,None,None),
        contents=[sdr])
    mbox.update()
    parole.display.scene.add(mbox, pos=mbox.centeredPos())
    return mbox

class AimOverlay(parole.map.AsciiTile):
    def __init__(self):
        super(AimOverlay, self).__init__('*', (64,32,255))
    def __repr__(self):
        return "AimOverlay()"
def addAimOverlay(tile):
    if tile is not data['mapframe'].getMap()[player.pos]:
        tile.addOverlay(AimOverlay())
    return True
def remAimOverlay(tile):
    for ovly in tile.overlays.keys():
        if isinstance(ovly, AimOverlay):
            tile.removeOverlay(ovly)
    return True


lookAnnote = None
zapping = False

@test.test()
def t_mapgen():
    def handleWalk(command):
        global lookAnnote, player, zapping
        if not player:
            return
        map = data['mapframe'].getMap()
        frame = data['mapframe']

        displacement = (0,0)
        moveTree = 'tree' in command

        if command in ['north','treenorth']:
            displacement = (0,-1)
        elif command in ['south', 'treesouth']:
            displacement = (0, 1)
        elif command in ['east', 'treeeast']:
            displacement = (1, 0)
        elif command in ['west', 'treewest']:
            displacement = (-1, 0)
        elif command in ['northeast', 'treenortheast']:
            displacement = (1,-1)
        elif command in ['northwest', 'treenorthwest']:
            displacement = (-1, -1)
        elif command in ['southeast', 'treesoutheast']:
            displacement = (1, 1)
        elif command in ['southwest', 'treesouthwest']:
            displacement = (-1,1)
        elif command in ('examine', 'zap'):
            if lookAnnote:
                if zapping:
                    zapping = False
                    zapPos = (lookAnnote.tile.col, lookAnnote.tile.row)
                    if map.traceLOS(player.pos, zapPos, remAimOverlay) is \
                            map[zapPos]:
                        message('You zap that space into oblivion!')
                        map[zapPos].clear()
                    else:
                        message('You need line-of-sight to zap!')

                frame.removeAnnotation(lookAnnote)
                lookAnnote = None
            else:
                playerTile = map[player.pos]
                if command == 'zap':
                    zapping = True
                    lookAnnote = frame.annotate(playerTile,
                        'Zap: %s.' % ', '.join([str(x) for x in playerTile]),
                        lineRGB=(64,32,255), reticleRGB=(64,32,255))
                else:
                    lookAnnote = frame.annotate(playerTile,
                        'You see: %s.' % ', '.join([str(x) for x in \
                            playerTile]))
            return
        elif command == 'save':
            mbox = messageBox('Saving...')
            parole.display.update()
            time = parole.time()
            data['mapframe'].setMap(None)
            f = bz2.BZ2File('mapsave.sav', 'w')
            saveData = (map, player, data['light'], data['tree'])
            cPickle.dump(saveData, f, protocol=-1)
            f.close()
            data['mapframe'].setMap(map)
            if data['fov']:
                data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
            time = (parole.time() - time) or 1
            parole.info('Map save time: %dms', time)
            parole.display.scene.remove(mbox)
            return
        elif command == 'restore':
            mbox = messageBox('Restoring...')
            parole.display.update()
            if lookAnnote:
                data['mapframe'].removeAnnotation(lookAnnote)
                lookAnnote = None
            data['mapframe'].setMap(None)
            time = parole.time()
            f = bz2.BZ2File('mapsave.sav', 'r')
            map, player, data['light'], data['tree'] = cPickle.load(f)
            #sd = cPickle.load(f)
            f.close()
            data['mapframe'].setMap(map)
            if data['fov']:
                data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
            time = (parole.time() - time) or 1
            parole.info('Map restore time: %dms', time)
            parole.display.scene.remove(mbox)
            return
        elif command == 'toggle fov':
            if data['fov']:
                data['mapframe'].bindVisibilityToFOV(None, None)
            elif player:
                data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
            data['fov'] = not data['fov']
            return
            
        if data['msg3Shader'].text:
            message('')
        curPos = moveTree and data['tree'].pos or player.pos
        if not moveTree and lookAnnote:
            curPos = (lookAnnote.tile.col, lookAnnote.tile.row)
        newPos = (curPos[0] + displacement[0], curPos[1] + displacement[1])

        if newPos[0] < 0 or newPos[1] < 0 or newPos[0] >= map.cols or \
                newPos[1] >= map.rows:
            return

        if lookAnnote and not moveTree:
            frame.removeAnnotation(lookAnnote)
            lookTile = map[newPos]
            if zapping:
                map.traceLOS(player.pos, curPos, remAimOverlay)
                if map.traceLOS(player.pos, newPos, addAimOverlay) is \
                        lookTile:
                    lookAnnote = frame.annotate(lookTile,
                        'Zap: %s.' % ', '.join([str(x) for x in lookTile]),
                        lineRGB=(64,32,255), reticleRGB=(64,32,255))
                else:
                    lookAnnote = frame.annotate(lookTile,
                        'Not in LOS.',
                        lineRGB=(64,32,255), reticleRGB=(64,32,255))
            else:
                lookAnnote = frame.annotate(lookTile,
                    'You see: %s.' % ', '.join([str(x) for x in lookTile]))

            return

        for obj in map[newPos]:
            if obj.blocker:
                message('Your way is blocked by %s.' % obj)
                return
            if obj.passer:
                message('You pass by %s.' % obj)


        map[curPos].remove(moveTree and data['tree'] or player)
        if not moveTree: data['light'].remove(map)
        data['light'].rgb = random.choice([colors['Orange'],
            colors['Chocolate'], colors['Coral'], colors['Yellow'],
            colors['Pink']])
        map[newPos].add(moveTree and data['tree'] or player)
        if not moveTree: data['light'].apply(map, newPos)

        # This works, but is too slow without some sort of pre-caching and/or
        # optimization: animated water (each application uses random new
        # perlin Z).
        #map.applyGenerator(data['waterGenerator'], 
        #        pygame.Rect((25, 35), (20, 20)))

        map.update()

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
        elif command == "makeMap1":
            time = parole.time()
            map = makeMap1()
            time = (parole.time() - time) or 1
            parole.info('Map creation time (%s x %s): %sms => %s tiles per second.',
                        map.cols, map.rows, time, 
                        (float(map.cols*map.rows) / float(time))*1000.0)
            #import pdb
            #pdb.set_trace()
            #pickle.dump(map, open('map.pkl', 'w'))
            data['mapframe'].setMap(map)
            #data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
            data['fov'] = False
        elif command == "makeMap2":
            map = makeMap2()
            data['mapframe'].setMap(map)
        elif command == "makeMap3":
            map = makeMap3()
            data['mapframe'].setMap(map)

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
        msg1Shader = parole.shader.TextBlockPass(txtfont,
                (200,200,200), text="Use numpad (or vi keys) "\
                        "to move, arrows to scroll map,") 
        msg2Shader = parole.shader.TextBlockPass(txtfont, (200,200,200),
                text="`1'-`3' to make maps, `q' to quit. `x' looks, ctrl "\
                        "moves tree.") 
        data['msg3Shader'] = parole.shader.TextBlockPass(txtfont,
                (200,200,200))
        parole.display.scene.add(msg1Shader, pos=(3, 0))
        parole.display.scene.add(msg2Shader, pos=(3, txtfont.get_linesize()))
        parole.display.scene.add(data['msg3Shader'], 
            pos=(3, txtfont.get_linesize()*2))

        # Map frame setup
        # Create MapFrame and add to scene
        mapsize = (scrsize[0], scrsize[1] - txtfont.get_linesize()*3)
        mappos = (0, txtfont.get_linesize()*3)
        tileSize = parole.map.AsciiTile.characterSize()
        data['mapframe'] = parole.map.MapFrame(mapsize, tileSize=tileSize)
        parole.display.scene.add(data['mapframe'], pos=mappos)

        # it's useful for debugging to make some things available from the
        # console
        parole.__dict__['makeMap1'] = makeMap1 

    #parole.display.getSurface().fill((0,0,0))

#tests = [t_resource, t_zip, t_colorfield, t_texturepass, t_textblock, t_mapgen]
#tests = [t_resource, t_colorfield, t_texturepass, t_textblock, t_mapgen]
tests = [t_mapgen]

def main():
    #gc.set_debug(gc.DEBUG_LEAK)
    test.runTests(tests)
    test.summary()


if __name__ == "__main__":
    main()
