from parole.colornames import colors
from parole.display import interpolateRGB
import pygame, random
from pprint import pprint

# import modules from other resource scripts
util = parole.resource.getModule('scripts/util.py')

class TestMapObject(parole.map.MapObject):
    def __init__(self, name, layer, shader, blocker=False, passer=False):
        parole.map.MapObject.__init__(self, layer, shader, blocksLOS=blocker)
        self.name = name
        self.blocker = blocker
        self.passer = passer

    def __str__(self):
        return self.name


def makeOutdoorMap(data):
    mbox = util.messageBox('Creating outdoors...')
    parole.display.update()

    # Create map 
    #COLS, ROWS = parole.conf.mapgenoptions.cols, parole.conf.mapgenoptions.rows
    COLS, ROWS = 96, 64
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
    stairsGenerator = parole.map.MapObjectGenerator("stairsGenerator", 
            lambda: TestMapObject('a stairway leading down', 100,
                parole.map.AsciiTile('>', colors['White'],
                    bg_rgb=(127,150,127)), passer=True))
    roomTemplate = \
"""
#######+#######
#.............#
#.............#
#.............#
+......>......+
#.............#
#.............#
#.............#
#######+#######
"""
    roomLegend = {  
            '#': wallGenerator,
            '+' : doorGenerator,
            '.' : floorGenerator,
            '>' : stairsGenerator,
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


    map.setAmbientLight((255,255,255), 0.75)

    brazier = parole.map.LightSource((255,255,255), 5.0)
    brazier.apply(map, (27,14))
    brazier.copy().apply(map, (27,18))
    brazier.copy().apply(map, (37,14))
    brazier.copy().apply(map, (37,18))
    brazier.copy().apply(map, (32,16))

    map.update()
    parole.display.scene.remove(mbox)
    parole.display.update()
    return map, (0,9) # return map and player starting pos

def makeDungeonMap(data):
    mbox = util.messageBox('Creating dungeon...')
    parole.display.update()

    COLS, ROWS = 96, 64
    map = parole.map.Map2D('Test Map', (COLS, ROWS))

    # First fill the level with solid rock (cellular automaton for colors)
    rockGenerator = \
        lambda bg_rgb: parole.map.MapObjectGenerator("rockGenerator",
            lambda: TestMapObject('solid rock', 100, 
                parole.map.AsciiTile(' ',#random.choice([' ']*3 + [',',';',"'", '"']),
                (random.randint(0,64),random.randint(0,64),random.randint(0,96)),
                bg_rgb=bg_rgb), blocker=True))
    darkColor = colors['Gray']
    lightColor = colors['LightSteelBlue']
    rockConditions = {
        0: rockGenerator(interpolateRGB(darkColor, lightColor, 0.0)),
        1: rockGenerator(interpolateRGB(darkColor, lightColor, 0.1)),
        2: rockGenerator(interpolateRGB(darkColor, lightColor, 0.2)),
        3: rockGenerator(interpolateRGB(darkColor, lightColor, 0.3)),
        4: rockGenerator(interpolateRGB(darkColor, lightColor, 0.4)),
        5: rockGenerator(interpolateRGB(darkColor, lightColor, 0.5)),
        6: rockGenerator(interpolateRGB(darkColor, lightColor, 0.6)),
        7: rockGenerator(interpolateRGB(darkColor, lightColor, 0.8)),
        8: rockGenerator(interpolateRGB(darkColor, lightColor, 0.9)),
        9: rockGenerator(interpolateRGB(darkColor, lightColor, 1.0))
    }
    rockAreaGenerator =  parole.map.CellularAutomataGenerator("rockAreaGenerator",
            0.35, rockConditions, seedEdges=True)
    rockAreaGenerator.apply(map)

    # Figure out what rooms will (try to) be on this map
    # The format is an ordered list of (room, num) tuples, indicating the order
    # in which to lay how many of what kind of rooms.
    roomBill = [
        (BrazierRoom,   20) # generate 20 brazier-rooms
    ]
    totalRequestedRooms = sum([num for (room, num) in roomBill])

    # Add the requested rooms
    rooms = []
    for roomType, nRooms in roomBill:
        for n in xrange(nRooms):
            layRoom(map, roomType, rooms)
    parole.debug('Laid %d of %d rooms.', len(rooms), totalRequestedRooms)

    # Connect the rooms
    connectRooms(map, rooms, BrazierDigger, 1, 14)

    # place the stairs in one of the rooms
    stairRoom = random.choice(rooms)
    stairPos = (random.randint(stairRoom.rect.left+1, stairRoom.rect.right-2),
                random.randint(stairRoom.rect.top+1,  stairRoom.rect.bottom-2))
    stairs = TestMapObject('a stairway leading up', 100,
            parole.map.AsciiTile('<', colors['White'], bg_rgb=(127,150,127)),
            passer=True)
    map[stairPos].add(stairs)

    # amount of ambient light in the dungeon 
    map.setAmbientLight((255,255,255), 0.1)

    map.update()

    parole.display.scene.remove(mbox)
    parole.display.update()
    return map, stairPos # return map and player starting pos

class BrazierRoom(object):
    # minimum/maximum rooms extents
    minRoomW, minRoomH = 6, 6
    maxRoomW, maxRoomH = 20, 20

    # possible floor colors
    floorColors = [
        'LightSalmon',
        'Peru',
        'PeachPuff',
        'Beige',
        'Bisque',
        'DimGray',
        'Tan',
        'DarkGoldenRod',
        'Khaki',
        'Sienna',
        'Chocolate',
        'SaddleBrown',
    ]

    def __floorGenerator(self, bg_rgb):
        return parole.map.MapObjectGenerator("brazier floor",
            lambda: TestMapObject('a dirt floor', 0,
                parole.map.AsciiTile(' ', (random.randint(0,64),
                random.randint(0,64), random.randint(0,96)), bg_rgb=bg_rgb)))

    def __init__(self, pos):
        self.pos = pos
        self.size = (random.randint(self.minRoomW, self.maxRoomW),
                     random.randint(self.minRoomH, self.maxRoomH))
        self.rect = pygame.Rect(self.pos, self.size)

        self.floorColor1 = colors[random.choice(BrazierRoom.floorColors)]
        self.floorColor2 = colors[random.choice(BrazierRoom.floorColors)]
        self.mixture = random.random()

        self.floorConditions = dict([
            (x, self.__floorGenerator(interpolateRGB(self.floorColor1,
                                                     self.floorColor2,
                                                     float(x)/10.))) \
            for x in xrange(11)
        ])
        # cellular automaton for laying 2-tone floors
        self.floorAreaGenerator = \
            parole.map.CellularAutomataGenerator("brazier floor area",
                    self.mixture, self.floorConditions, clearFirst=True,
                    seedEdges=True)

    def apply(self, map):
        # lay some floor
        floorRect = self.rect.inflate(-2, -2)
        self.floorAreaGenerator.apply(map, floorRect)

        # put braziers in the corners
        for corner in corners(floorRect):
            brazier = Brazier()
            map[corner].add(brazier)
            brazier.lightSource.apply(map, corner)

        #... and in the center of the room if it's big enough
        if self.rect.w * self.rect.h > 150:
            brazier = Brazier()
            map[self.rect.center].add(brazier)
            brazier.lightSource.apply(map, self.rect.center)

    def diggableOut(self):
        return [p for p in perimeter(self.rect) if p not in corners(self.rect)]

    def diggableIn(self):
        return [p for p in perimeter(self.rect) if p not in corners(self.rect)]

def layRoom(map, roomType, rooms):
    # number of times to try laying the room before giving up
    tries = 100

    # Keep choosing a random location and size for the room until we find one
    # that doesn't intersect with existing rooms, then place it and return
    while tries:
        tries -= 1
        roomPos = (random.randint(0, map.cols-1),
                   random.randint(0, map.rows-1))
        room = roomType(roomPos)

        if not map.rect().contains(room.rect):
            # we generated a rectangle not completely enclosed by the map
            continue

        if room.rect.collidelist([r.rect for r in rooms]) != -1:
            # the generated rectangle overlaps with an existing one
            continue

        rooms.append(room)

        room.apply(map)
        return True

    return False

def corners(rect):
    return (rect.topleft,
            (rect.topright[0]-1, rect.topright[1]),
            (rect.bottomleft[0], rect.bottomleft[1]-1),
            (rect.bottomright[0]-1, rect.bottomright[1]-1))

class Brazier(TestMapObject):
    def __init__(self):
        super(Brazier, self).__init__('a flaming brazier', 10,
                parole.map.AsciiTile('*', colors['Orange']), passer=True)
        self.lightSource = parole.map.LightSource((random.randint(200,255),
                                                   random.randint(200,255),
                                                   random.randint(200,255)), 
                                                  4.0 + 2.0*random.random())

def connectRooms(map, rooms, diggerClass, minDist, maxDist, adjacents=True):
    connectedPairs = []

    if adjacents:
        for room1 in rooms:
            for room2 in rooms:
                if room1 is room2:
                    continue
                pair1 = (room1, room2)
                pair2 = (room2, room1)
                if pair1 in connectedPairs or pair2 in connectedPairs:
                    continue

                if adjacent(room1, room2):
                    connectedPairs.append(pair1)
                    connectedPairs.append(pair2)
                    #parole.debug('adjacent: %r, %r', room1, room2)
                    connectAdjacent(map, room1, room2)

    for room1 in rooms:
        otherRooms = [r for r in rooms if r is not room1]
        otherRects = [r.rect for r in rooms if r is not room1]
        for inflation in xrange(minDist, maxDist+1):
            parole.debug('inflation %s', inflation)
            inflRoom1 = room1.rect.inflate(inflation, inflation)
            for otherIdx in inflRoom1.collidelistall(otherRects):
                room2 = otherRooms[otherIdx]
                pair1 = (room1, room2)
                pair2 = (room2, room1)
                if pair1 in connectedPairs or pair2 in connectedPairs:
                    continue

                connectDistant(map, room1, room2, rooms, diggerClass())
                connectedPairs.append(pair1)
                connectedPairs.append(pair2)

def adjacent(room1, room2):
    return room1.rect.inflate(2,2).colliderect(room2.rect.inflate(2,2))

def perimeter(rect):
    for y in (rect.top, rect.bottom-1):
        for x in xrange(rect.left, rect.left+rect.w):
            yield x,y
    for x in (rect.left, rect.right-1):
        for y in xrange(rect.top+1, rect.top+rect.h):
            yield x,y

def connectAdjacent(map, room1, room2):
    perim = list(perimeter(room1.rect))
    random.shuffle(perim)
    rm2Infl = room2.rect.inflate(2,2)
    for x,y in perim:
        if rm2Infl.collidepoint(x,y):
            if (x,y) not in corners(room1.rect) and (x,y) not in corners(rm2Infl):
                map[x,y].clear()
                map[x,y].add(adjacentFloor(room1))
                for (x2,y2) in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if room2.rect.collidepoint(x2,y2):
                        map[x2,y2].clear()
                        map[x2,y2].add(adjacentFloor(room1))
                        if (x2,y2) in corners(room2.rect):
                            for (x3,y3) in ((x2+1,y2),(x2-1,y2),(x2,y2+1),(x2,y2-1)):
                                if room2.rect.collidepoint(x3,y3):
                                    map[x3,y3].clear()
                                    map[x3,y3].add(adjacentFloor(room1))
                        return
                return

def adjacentFloor(room):
    return TestMapObject('a dirt floor', 0, parole.map.AsciiTile(' ',
        (random.randint(0,64),random.randint(0,64),random.randint(0,96)),
        bg_rgb=interpolateRGB(room.floorColor1, room.floorColor2, room.mixture)))

def sign(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0

def neighbors((x,y)):
    yield x+1, y
    yield x-1, y
    yield x, y+1
    yield x, y-1
    yield x+1, y+1
    yield x+1, y-1
    yield x-1, y+1
    yield x-1, y-1

def connectDistant(map, room1, room2, allRooms, digger):
    #parole.debug('Connecting distant rooms: %r, %r', room1, room2)
    p1 = [p for p in perimeter(room1.rect) if p not in corners(room1.rect)]
    p2 = [p for p in perimeter(room2.rect) if p not in corners(room2.rect)]
    #p1 = room1.diggableOut()
    #p2 = room2.diggableIn()

    while 1:
        startPos = random.choice(p1)
        endPos = random.choice(p2)
        dPos = (sign(endPos[0]-startPos[0]), sign(endPos[1]-startPos[1]))
        if room1.rect.collidepoint(startPos[0] + dPos[0], startPos[1] + dPos[1]):
            continue
        else:
            break

    x, y = startPos
    digger.digTile(map, map[x,y], room1, room2, allRooms)
    dx, dy = dPos
    movingX = random.choice((True, False))
    while (x,y) != endPos:
        if movingX:
            nx = x+dx
            ny = y
        else:
            nx = x
            ny = y+dy

        if room1.rect.collidepoint(nx,ny):
            movingX = not movingX
            continue

        if not digger.digTile(map, map[nx,ny], room1, room2, allRooms):
            break
        x, y = nx, ny
        if x == endPos[0] and y != endPos[1]:
            movingX = False
        elif x != endPos[0] and y == endPos[1]:
            movingX = True


class BrazierDigger(object):
    def __init__(self):
        self.alreadyDoored = []

    def door(self):
        return TestMapObject('a door', 100, parole.map.AsciiTile('+',
            colors['White']), passer=True)

    def digTile(self, map, tile, srcRoom, destRoom, allRooms):
        destPerim = list(perimeter(destRoom.rect))
        hasFloor = False
        for obj in list(tile):
            if obj.name == "solid rock":
                tile.remove(obj)
            elif obj.name == "a dirt floor":
                hasFloor = True
        if not hasFloor:
            tile.add(adjacentFloor(srcRoom))
    
        def addDoor():
            for n in neighbors((tile.col, tile.row)):
                if n[0] < 0 or n[1] < 0 or n[0] >= map.cols or n[1] >= map.rows:
                    continue
                for obj in map[n]:
                    if obj.name == 'a door':
                        return
            tile.add(self.door())
    
        if (tile.col, tile.row) in destPerim:
            if destRoom not in self.alreadyDoored:
                #tile.add(door())
                addDoor()
                self.alreadyDoored.append(destRoom)
            if (tile.col, tile.row) in corners(destRoom.rect):
                return True
            return False # stop here, we've reached the room
    
        for otherRoom in allRooms:
            if (otherRoom not in self.alreadyDoored) and \
                    (tile.col, tile.row) in list(perimeter(otherRoom.rect)):
                addDoor()
                self.alreadyDoored.append(otherRoom)
    
        return True

