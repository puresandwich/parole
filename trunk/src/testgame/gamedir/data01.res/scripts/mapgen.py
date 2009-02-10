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


def makeMap1(data, player):
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

    map[0,9].add(player)

    map.setAmbientLight((255,255,255), 0.75)

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

