import parole, logging, sys
import pygame

from pgu import gui

# This test script provides an updateFunc which just shows a hello world
# text shader

firstUpdate = True
sdr = None
sdr2 = None

def updateFunc():
    global firstUpdate, sdr, sdr2
    if firstUpdate:
        firstUpdate = False
        font = pygame.font.SysFont("Courier New", 12)
        sdr = parole.shader.Shader("testshader", (50,50), (150,150))
        parole.info('Creating textpass')
        field = parole.shader.ColorField((0,0,155), (0,0), (150,150))
        txt1 = parole.shader.TextPass("Hello, World!", (0,25), font,
                True, (255,255,255), 100)
        txt2 = parole.shader.PGU_TextPass('Hello, World!', (0,0), font,
                (0,155,0), 255)
        sdr.addPass(field, "blend")
        sdr.addPass(txt1, "blend")
        sdr.addPass(txt2, "blend")
        parole.display.scene.append(sdr)

        sdr2 = parole.shader.Shader("apptestshader", (210,50), (200,200))
        c = gui.Container(align=-1,valign=-1)
        c.add(gui.Button('Hello!'),0,0)
        #appPass = parole.shader.PGU_AppPass(c, (0,0), (200,200))
        #sdr2.addPass(appPass, "blend")
        #parole.display.scene.append(sdr2)

        parole.info("Press 'q' to quit.")

    for key in parole.input.getKeyPresses():
        if key == 'q':
            raise parole.ParoleShutdown

    surf = parole.display.getSurface()
    surf.fill((0,0,0))

