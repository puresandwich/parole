#Parole Advanced Roguelike Engine
#Copyright (C) 2006-2009 Max Bane
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
Provides a fluffy splash animation to advertise the engine.
"""

import parole, shader, display, pygame, resource

doneSplash = False
splash = None

def doSplash(duration = 3000):
    global splash
    splash = SplashShader()
    splash.startTime = parole.time()
    splash.endTime = splash.startTime + duration
    display.scene.add(splash)
    parole.pushAnimation()

class SplashShader(shader.Shader):
    def __init__(self):
        super(SplashShader, self).__init__("SplashShader",
                size=display.getSurface().get_size())
        self.startTime = 0
        self.endTime = 0

        self.goldSound = resource.getSound('sounds/enginesplash.wav')

        # Background field
        self.pBG = shader.ColorField((255,255,255), self.size)
        self.addPass(self.pBG, pos=(0,0))

        font = resource.getFont('fonts/monaco.ttf', 12)

        # Copyright
        gray = (108,108,108)
        copyright = "Engine copyright 2009 by Max Bane"
        copyrightSize = font.size(copyright)
        copyrightPass = shader.TextBlockPass(font, gray,
                text=copyright)
        copyrightPos = (self.size[0]/2 - copyrightSize[0]/2,
                        self.size[1] - copyrightSize[1])
        self.addPass(copyrightPass, pos=copyrightPos)

        font = resource.getFont('fonts/monaco.ttf', 18)
        self.font = font

        # P A R O L E - initial positions
        paroleSize = font.size("P A R O L E")
        spaceWidth = font.size(" ")[0]
        parolePos = (self.size[0]/2 - paroleSize[0]/2, 
                     self.size[1]/4 - paroleSize[1])
        green = (0,128,0)
        pos = list(parolePos)
        self.pStarts = {}
        self.pP = shader.TextBlockPass(font, green, text="P")
        self.addPass(self.pP, pos=tuple(pos))
        self.pStarts[self.pP] = tuple(pos)
        pos[0] += font.size("P")[0] + spaceWidth
        self.pA = shader.TextBlockPass(font, green, text="A")
        self.addPass(self.pA, pos=tuple(pos))
        self.pStarts[self.pA] = tuple(pos)
        pos[0] += font.size("A")[0] + spaceWidth
        self.pR = shader.TextBlockPass(font, green, text="R")
        self.addPass(self.pR, pos=tuple(pos))
        self.pStarts[self.pR] = tuple(pos)
        pos[0] += font.size("R")[0] + spaceWidth
        self.pO = shader.TextBlockPass(font, green, text="O")
        self.addPass(self.pO, pos=tuple(pos))
        self.pStarts[self.pO] = tuple(pos)
        pos[0] += font.size("O")[0] + spaceWidth
        self.pL = shader.TextBlockPass(font, green, text="L")
        self.addPass(self.pL, pos=tuple(pos))
        self.pStarts[self.pL] = tuple(pos)
        pos[0] += font.size("L")[0] + spaceWidth
        self.pE = shader.TextBlockPass(font, green, text="E")
        self.addPass(self.pE, pos=tuple(pos))
        self.pStarts[self.pE] = tuple(pos)

        # title
        self.pDests = {}
        smoke = (64, 64, 64)
        titleSize = font.size("Python Advanced ROgueLike Engine")
        self.titleSize = titleSize
        pos = [self.size[0]/2 - titleSize[0]/2,
               self.size[1]/2 - titleSize[1]]
        self.titlePos = tuple(pos)
        titlePasses = {}
        self.pDests[self.pP] = tuple(pos)
        pos[0] += font.size("P")[0]
        titlePasses[shader.TextBlockPass(font, smoke, text="ython ")] = \
            tuple(pos)
        pos[0] += font.size("ython ")[0]
        self.pDests[self.pA] = tuple(pos)
        pos[0] += font.size("A")[0]
        titlePasses[shader.TextBlockPass(font, smoke, text="dvanced ")] = \
            tuple(pos)
        pos[0] += font.size("dvanced ")[0]
        self.pDests[self.pR] = tuple(pos)
        pos[0] += font.size("R")[0]
        self.pDests[self.pO] = tuple(pos)
        pos[0] += font.size("O")[0]
        titlePasses[shader.TextBlockPass(font, smoke, text="gue")] = \
            tuple(pos)
        pos[0] += font.size("gue")[0]
        self.pDests[self.pL] = tuple(pos)
        pos[0] += font.size("L")[0]
        titlePasses[shader.TextBlockPass(font, smoke, text="ike ")] = \
            tuple(pos)
        pos[0] += font.size("ike ")[0]
        self.pDests[self.pE] = tuple(pos)
        pos[0] += font.size("E")[0]
        titlePasses[shader.TextBlockPass(font, smoke, text="ngine")] = \
            tuple(pos)
        self.titlePasses = titlePasses

        self.addUpdateFunc(SplashShader.updateSplash)
        self.touch()

        self.movementDone = False
        self.gold = False
        self.fadeAlpha = 0
        self.fader = shader.ColorField((0,0,0, 0), self.size)

    def updateSplash(self):
        global doneSplash, splash
        self.touch()
        now = parole.time()
        progress = (now - self.startTime) / \
                    float(self.endTime - self.startTime)

        if progress <= 0.2:
            return

        if progress <= 0.6:
            for (p, dest) in self.pDests.iteritems():
                start = self.pStarts[p]
                y = start[1] + ((progress-0.2)/(0.6-0.2))*(dest[1]-start[1])
                x = start[0] + ((progress-0.2)/(0.6-0.2))*(dest[0]-start[0])
                self.positionOf[p] = (int(x), int(y))
            return
        elif not self.movementDone:
            for (p, dest) in self.pDests.iteritems():
                self.positionOf[p] = dest
            self.movementDone = True
            return

        if progress < 1.0 and self.titlePasses.keys()[0] not in self.passes:
            for p, pos in self.titlePasses.items():
                self.addPass(p, pos=pos)
            return

        if progress > 1.0 and not self.gold:
            for p in self.titlePasses.keys() + self.pDests.keys():
                self.remPass(p)
            self.addPass(shader.TextBlockPass(self.font, (255,215,0),
                text="Python Advanced ROgueLike Engine"), pos=self.titlePos)
            self.goldSound.play()
            self.gold = True
        elif progress > 1.1 and self.fadeAlpha < 255:
            if self.fader not in self.passes:
                parole.debug("adding fader!")
                self.addPass(self.fader, pos=(0,0))
            self.fadeAlpha = (now - (self.endTime + \
                0.1*(self.endTime-self.startTime)))/500.0 * 255
            self.fader.rgb = (0, 0, 0, min(255, int(self.fadeAlpha)))
        elif self.fadeAlpha >= 255:
            parole.popAnimation()
            self.clean()
            display.scene.remove(self)
            doneSplash = True
            splash = None

