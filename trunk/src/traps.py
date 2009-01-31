import parole, traceback, sys, random, pygame

data = {}
firstUpdate = True

def main():
    parole.startup("test.cfg", frame, "PAROLE Engine Demonstration")

def frame():
    global firstUpdate
    
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
    
    if firstUpdate:
        firstUpdate = False
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
        
        COLS, ROWS = 96, 32
        mapsize = (scrsize[0], scrsize[1] - txtfont.get_linesize()*3)
        mappos = (0, txtfont.get_linesize()*3)
        data['walkmap'] = parole.map.Map2D('Walk Map', mappos, mapsize, (COLS, ROWS))
        
        # place the players map object
        playerStartPos = (COLS/2, ROWS/2)
        data['player'] = Player()
        data['walkmap'].add(playerStartPos, data['player'])
        
        # fill the map with objects
        for col in range(COLS):
            for row in range(ROWS):
                # floor
                data['walkmap'].add((col,row), Floor())
                
                # wall or trap or nothing
                item = random.choice([Wall, Trap, None, None, None, None, None, None, None, None])
                if item and (col,row) != playerStartPos:
                    data['walkmap'].add((col, row), item())
                
        parole.display.scene.add(data['walkmap'])
        
    parole.display.getSurface().fill((0,0,0))
    
if __name__ == "__main__":
    main()