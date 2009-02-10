
import parole, traceback, sys, random, gc
import pygame, pickle, cPickle, bz2
from parole.colornames import colors

# Test game state info
data = {}
#firstUpdate = True
player = None
lookAnnote = None
zapping = False

def init():
    # called on the very first frame update. loads script modules from the game
    # resources (gamedir/*.res)
    global util, mapgen
    util = parole.resource.getModule('scripts/util.py')
    mapgen = parole.resource.getModule('scripts/mapgen.py')

# The player object
class Player(parole.map.MapObject):
    def __init__(self):
        playerGlyph = parole.map.AsciiTile('@', (255,255,255))
        parole.map.MapObject.__init__(self, 1000,
            playerGlyph)
        self.blocker = True
        
    def __str__(self):
        return 'the player'


# The main frame function
def updateFunc():
    init()

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
            text="'?' for more help.") 
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

    newMap()

    while 1:
        yield

    #parole.display.getSurface().fill((0,0,0))

def message(text):
    data['msg3Shader'].text = text

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

def newMap():
    global player
    mbox = util.messageBox('Creating map...')
    parole.display.update()
    time = parole.time()
    player = Player()
    map = mapgen.makeMap1(data, player)
    time = (parole.time() - time) or 1
    parole.info('Map creation time (%s x %s): %sms => %s tiles per second.',
                map.cols, map.rows, time, 
                (float(map.cols*map.rows) / float(time))*1000.0)
    data['mapframe'].setMap(map)
    #data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
    data['fov'] = False
    parole.display.scene.remove(mbox)

helpBox = None

def help():
    global helpBox
    testCommands = parole.conf.commands.testcommandset.keypresses
    walkCommands = parole.conf.commands.walkcommands.keypresses
    helpText = \
"""Keybindings [{\\red command}: {\\green key 1{\\white /}...{\\white /}key n}]

{\\red Quit}: {\\green %s}\t\t{\\red FPS}: {\\green %s}\t\t{\\red Reset map}: {\\green %s}
{\\red Scroll right}: {\\green %s}\t{\\red Scroll left}: {\\green %s}\t{\\red Scroll up}: {\\green %s}\t{\\red Scroll down}: {\\green %s}
{\\red Move north}: {\\green %s}\t{\\red Move south}: {\\green %s}\t{\\red Move west}: {\\green %s}\t{\\red Move east}: {\\green %s}
{\\red Move northeast}: {\\green %s}\t{\\red Move southeast}: {\\green %s}\t{\\red Move northwest}: {\\green %s}\t{\\red Move southwest}: {\\green %s}
{\\red Examine}: {\\green %s}\t\t{\\red Zap}: {\\green %s}\t\t{\\red Save map}: {\\green %s}\t\t{\\red Restore map}: {\\green %s}
{\\red Toggle FOV}: {\\green %s}\t\t{\\red Move tree}: {\\green ctrl}

[Press {\\green %s} to dismiss this help]
""" % (findKey("quit", testCommands), 
       findKey("fps", testCommands),
       findKey("makeMap1", testCommands),
       findKey('scroll right', testCommands),
       findKey('scroll left', testCommands),
       findKey('scroll up', testCommands),
       findKey('scroll down', testCommands),
       findKey('north', walkCommands),
       findKey('south', walkCommands),
       findKey('west', walkCommands),
       findKey('east', walkCommands),
       findKey('northeast', walkCommands),
       findKey('southeast', walkCommands),
       findKey('northwest', walkCommands),
       findKey('southwest', walkCommands),
       findKey('examine', walkCommands),
       findKey('zap', walkCommands),
       findKey('save', walkCommands),
       findKey('restore', walkCommands),
       findKey('toggle fov', walkCommands),
       findKey('dismiss', testCommands))

    helpBox = util.messageBox(helpText, textWidth=480)
    
def findKey(command, commandSet):
    keys = []
    for key,comm in commandSet.iteritems():
        if comm == command:
            keys.append(key)
    return '{\\white /}'.join(keys)

fpsBox = None

def handleTest(command):
    global fpsBox, helpBox

    if command == 'quit':
        raise parole.ParoleShutdown
    elif command == 'scroll right':
        data['mapframe'].scrollTiles(1, 0)
    elif command == 'scroll left':
        data['mapframe'].scrollTiles(-1, 0)
    elif command == 'scroll down':
        data['mapframe'].scrollTiles(0, 1)
    elif command == 'scroll up':
        data['mapframe'].scrollTiles(0, -1)
    elif command == "makeMap1":
        newMap()
    elif command == "help":
        if not helpBox:
            help()
    elif command == "dismiss":
        if helpBox:
            parole.display.scene.remove(helpBox)
            helpBox = None
    elif command == "fps":
        if not fpsBox:
            fpsBox = parole.shader.FPS(
                    parole.resource.getFont('fonts/monaco.ttf', 16))
            fpsBox.update()
            parole.display.scene.add(fpsBox,
                    pos=(parole.display.getSurface().get_width() - \
                        fpsBox.width,0))
        else:
            parole.display.scene.remove(fpsBox)
            fpsBox = None

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
        mbox = util.messageBox('Saving...')
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
        mbox = util.messageBox('Restoring...')
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
        mbox = util.messageBox('Patience...')
        parole.display.update()
        if data['fov']:
            data['mapframe'].bindVisibilityToFOV(None, None)
        elif player:
            data['mapframe'].bindVisibilityToFOV(player, 16, remember=True)
        data['fov'] = not data['fov']
        parole.display.scene.remove(mbox)
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
            if data['mapframe'].inFOV(lookTile):
                lookAnnote = frame.annotate(lookTile,
                    'You see: %s.' % ', '.join([str(x) for x in lookTile]))
            else:
                lookAnnote = frame.annotate(lookTile,
                    'You cannot see here.')

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

