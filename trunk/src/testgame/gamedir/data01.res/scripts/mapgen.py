from parole.colornames import colors
from parole.display import interpolateRGB
import pygame, random

class TestMapObject(parole.map.MapObject):
    def __init__(self, name, layer, shader, blocker=False, passer=False):
        parole.map.MapObject.__init__(self, layer, shader, blocksLOS=blocker)
        self.name = name
        self.blocker = blocker
        self.passer = passer

    def __str__(self):
        return self.name


def makeOutdoorMap(data):
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
    return map, (0,9) # return map and player starting pos

def makeDungeonMap(data):
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

    # Add some rooms
    nRooms = 20
    roomRects = []
    for n in xrange(nRooms):
        layRoom(map, roomRects)
    parole.debug('Laid %d of %d rooms.', len(roomRects), nRooms)

    # Connect the rooms
    connectRooms(map, roomRects)

    # place the stairs in one of the rooms
    stairRoomRect = random.choice(roomRects)
    stairPos = (random.randint(stairRoomRect.left+1, stairRoomRect.right-2),
                random.randint(stairRoomRect.top+1,  stairRoomRect.bottom-2))
    stairs = TestMapObject('a stairway leading up', 100,
            parole.map.AsciiTile('<', colors['White'], bg_rgb=(127,150,127)),
            passer=True)
    map[stairPos].add(stairs)

    # no ambient light in the dungeon (0.0 intensity)
    map.setAmbientLight((255,255,255), 0.0)

    map.update()
    return map, stairPos # return map and player starting pos

def layRoom(map, roomRects):
    # cellular automaton for lay floors with organic coloring
    floorGenerator = \
        lambda bg_rgb: parole.map.MapObjectGenerator("floorGenerator",
            lambda: TestMapObject('a dirt floor', 0, 
                parole.map.AsciiTile(' ',#random.choice([' ']*3 + [',',';',"'", '"']),
                (random.randint(0,64),random.randint(0,64),random.randint(0,96)),
                bg_rgb=bg_rgb)))
    darkColor = colors['SaddleBrown']
    lightColor = colors['Olive']
    rockConditions = {
        0: floorGenerator(interpolateRGB(darkColor, lightColor, 0.0)),
        1: floorGenerator(interpolateRGB(darkColor, lightColor, 0.1)),
        2: floorGenerator(interpolateRGB(darkColor, lightColor, 0.2)),
        3: floorGenerator(interpolateRGB(darkColor, lightColor, 0.3)),
        4: floorGenerator(interpolateRGB(darkColor, lightColor, 0.4)),
        5: floorGenerator(interpolateRGB(darkColor, lightColor, 0.5)),
        6: floorGenerator(interpolateRGB(darkColor, lightColor, 0.6)),
        7: floorGenerator(interpolateRGB(darkColor, lightColor, 0.8)),
        8: floorGenerator(interpolateRGB(darkColor, lightColor, 0.9)),
        9: floorGenerator(interpolateRGB(darkColor, lightColor, 1.0))
    }
    floorAreaGenerator =  parole.map.CellularAutomataGenerator("rockAreaGenerator",
            0.4, rockConditions, clearFirst=True, seedEdges=True)

    # minimum/maximum rooms extents
    minRoomW, minRoomH = 6, 6
    maxRoomW, maxRoomH = 20, 20

    # number of times to try laying the room before giving up
    tries = 100

    # Keep choosing a random location and size for the room until we find one
    # that doesn't intersect with existing rooms, then place it and return
    while tries:
        tries -= 1
        roomPos = (random.randint(0,map.cols-1), 
                   random.randint(0,map.rows-1))
        roomSize = (random.randint(minRoomW, maxRoomW),
                    random.randint(minRoomH, maxRoomH))
        roomRect = pygame.Rect(roomPos, roomSize)

        if not map.rect().contains(roomRect):
            # we generated a rectangle not completely enclosed by the map
            continue

        if roomRect.collidelist(roomRects) != -1:
            # the generate rectangle overlaps with an existing one
            continue

        roomRects.append(roomRect)

        # we've got a clear space for the room, so lay some floor
        #floorRect = pygame.Rect((roomPos[0]+1, roomPos[1]+1), 
        #                        (roomSize[0]-1, roomSize[1]-1))
        floorRect = roomRect.inflate(-2, -2)
        floorAreaGenerator.apply(map, floorRect)

        # put braziers in the corners
        for corner in corners(floorRect):
            brazier = Brazier()
            map[corner].add(brazier)
            brazier.lightSource.apply(map, corner)

        #... and in the center of the room if it's big enough
        if roomRect.w * roomRect.h > 150:
            brazier = Brazier()
            map[roomRect.center].add(brazier)
            brazier.lightSource.apply(map, roomRect.center)
            
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

def connectRooms(map, roomRects):
    connectedPairs = []
    for room1 in roomRects:
        for room2 in roomRects:
            if room1 == room2:
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

    for room1 in roomRects:
        otherRects = [r for r in roomRects if r != room1]
        for inflation in xrange(1, 15):
            inflRoom1 = room1.inflate(inflation, inflation)
            for otherIdx in inflRoom1.collidelistall(otherRects):
                room2 = otherRects[otherIdx]
                pair1 = (room1, room2)
                pair2 = (room2, room1)
                if pair1 in connectedPairs or pair2 in connectedPairs:
                    continue

                connectDistant(map, room1, room2, roomRects)
                connectedPairs.append(pair1)
                connectedPairs.append(pair2)

def adjacent(room1, room2):
    return room1.inflate(2,2).colliderect(room2.inflate(2,2))

def perimeter(rect):
    for y in (rect.top, rect.bottom-1):
        for x in xrange(rect.left, rect.left+rect.w):
            yield x,y
    for x in (rect.left, rect.right-1):
        for y in xrange(rect.top+1, rect.top+rect.h):
            yield x,y

def connectAdjacent(map, room1, room2):
    perim = list(perimeter(room1))
    random.shuffle(perim)
    rm2Infl = room2.inflate(2,2)
    for x,y in perim:
        if rm2Infl.collidepoint(x,y):
            if (x,y) not in corners(room1) and (x,y) not in corners(rm2Infl):
                map[x,y].clear()
                map[x,y].add(adjacentFloor())
                for (x2,y2) in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if room2.collidepoint(x2,y2):
                        map[x2,y2].clear()
                        map[x2,y2].add(adjacentFloor())
                        if (x2,y2) in corners(room2):
                            for (x3,y3) in ((x2+1,y2),(x2-1,y2),(x2,y2+1),(x2,y2-1)):
                                if room2.collidepoint(x3,y3):
                                    map[x3,y3].clear()
                                    map[x3,y3].add(adjacentFloor())
                        return
                return

def adjacentFloor():
    return TestMapObject('a dirt floor', 0, parole.map.AsciiTile(' ',
        (random.randint(0,64),random.randint(0,64),random.randint(0,96)),
        bg_rgb=interpolateRGB(colors['SaddleBrown'], colors['Olive'], 0.4)))

def door():
    return TestMapObject('a door', 100, parole.map.AsciiTile('+',
        colors['White']), passer=True)

def connectDistant(map, room1, room2, allRooms):
    parole.debug('Connecting distant rooms: %r, %r', room1, room2)
    p1 = [p for p in perimeter(room1) if p not in corners(room1)]
    p2 = [p for p in perimeter(room2) if p not in corners(room2)]
    destPerim = list(perimeter(room2))

    def visitTile(tile):
        hasFloor = False
        for obj in list(tile):
            if obj.name == "solid rock":
                tile.remove(obj)
            elif obj.name == "a dirt floor":
                hasFloor = True
        if not hasFloor:
            tile.add(adjacentFloor())

        if (tile.col, tile.row) in destPerim:
            tile.add(door())
            return False # stop here, we've reached the room

        if room2.collidepoint((tile.col, tile.row)):
            return False # we should have stopped already?

        for otherRoom in allRooms:
            if (tile.col, tile.row) in list(perimeter(otherRoom)):
                tile.add(door())

        return True

    map.traceRay(random.choice(p1), random.choice(p2), visitTile)
