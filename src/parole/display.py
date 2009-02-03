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
TODO: Display module pydocs.
"""

import pygame, parole, logging, config
import pygame.sprite

__displaySurf = None
__workSurf = None
__clearedSurf = None

__fpsClock = None
__modeDirty = False
__clearColor = (0,0,0,0)

defaultPosition = (0, 0)

scene = None

#==============================================================================

class Scene(pygame.sprite.OrderedUpdates):
    def __init__(self):
        super(Scene, self).__init__()
        self.positionOf = {}
        self.removalQueue = set()

    def add(self, *shaders, **kwargs):
        super(Scene, self).add(*shaders)
        pos = kwargs.get('pos', defaultPosition)
        for shader in shaders:
            self.positionOf[shader] = pos

    def remove(self, shader):
        """
        Queue C{shader} for removal from the scene at the end of the current
        frame.
        """
        self.removalQueue.add(shader)

    def removeAll(self):
        for shader in self:
            self.remove(shader)

    def flushRemovals(self):
        for shader in self.removalQueue:
            super(Scene, self).remove(shader)
            try:
                del self.positionOf[shader]
            except KeyError:
                pass
        self.removalQueue.clear()

#==============================================================================

lastModeConfs = {}

def __onConfigChange(conf):
        global __modeDirty, __clearColor
        for key in lastModeConfs.keys():
            if conf.display[key] != lastModeConfs[key]:
                __modeDirty = True
                lastModeConfs[key] = conf.display[key]
                parole.info('New value for display.%s: %s', key, 
                            lastModeConfs[key])

        pygame.time.set_timer(parole.GeneralUpdateEvent,
                conf.display.generalUpdateDelay)
        parole.info('General display update delay: %s',
                conf.display.generalUpdateDelay)

        __clearColor = parseColor(conf.display.clearColor)
        parole.info('Display clear color: %s', __clearColor)
        
        if __modeDirty:
            parole.debug('Config changed; mode dirty')

def parseColor(string):
    return tuple([int(c.strip()) for c in string.split(',')])
            
def init():
    """
    init() -> None
    
    Initializes the display module and creates the display surface according
    to the current config settings. Automatically called during engine startup -
    user code shouldn't need to use this function.
    """
    global __fpsClock, scene
    
    for opt in ['width', 'height', 'depth', 'fullscreen', 'hwaccel']:
        lastModeConfs[opt] = None
        
    parole.conf.notify(__onConfigChange, True)
    scene = Scene()
    __fpsClock = pygame.time.Clock()
    __setMode()
    
def unload():
    parole.conf.notify(__onConfigChange, False)

#==============================================================================
    
validDepths = [0, 8, 16, 32]
__lastDepth = 32

#==============================================================================

#def addConfigOptions():
#    """
#    addConfigOptions() -> None
#    
#    Registers the display module's config options. Handled by the engine - most
#    user code shouldn't need to call this.
#    """
#    categories.append('display')
#
#    # display options
#    config.addOption('display.width', '640', 'Display width in pixels', 
#        config.validateInt)
#    config.addOption('display.height', '480', 'Display height in pixels', 
#        config.validateInt)
#    config.addOption('display.fullscreen', 'false', 'Fullscreen display?', 
#        config.validateBool)
#    config.addOption('display.hwaccel', 'true', 
#        'Attempt to use hardware acceleration?', config.validateBool)
#    config.addOption('display.depth', '0', 'Possible values: 0, 8, 16, 32', 
#        __validateDepth)

#==============================================================================

def __setMode():
    global __modeDirty, __displaySurf, __workSurf, __lastDepth, __clearedSurf
    __modeDirty = False
    resolution = (int(parole.conf.display.width), 
                  int(parole.conf.display.height))
    fs = bool(parole.conf.display.fullscreen)
    hw = bool(parole.conf.display.hwaccel)
    depth = parole.conf.display.depth
    if depth not in validDepths:
        error('Bad value for display.depth: %s. Should be one of %s.',
              depth, ', '.join(validDepths))
        depth = __lastDepth
    else:
        __lastDepth = depth
    
    flags = 0
    if fs:
        flags |= pygame.FULLSCREEN
        
    if hw:
        flags |= pygame.HWSURFACE
        flags |= pygame.DOUBLEBUF
        
    parole.debug('Creating display surface...')
    __displaySurf = pygame.display.set_mode(resolution, flags, depth)
    parole.debug('... bingo!')
    #__clearedSurf = pygame.Surface(resolution).convert_alpha()
    #clearSurface(__clearedSurf, __clearedSurf.get_rect())
    
    if hw:
        __workSurf = pygame.Surface(resolution, pygame.SWSURFACE, __displaySurf)
    else:
        __workSurf = None
        
    logging.info('New mode: %s %s %sx%sx%s', hw and 'HW' or 'SW',
        fs and 'Fullscreen' or 'Window', resolution[0], resolution[1], depth)
    

#==============================================================================

def getSurface():
    """
    getSurface() -> pygame.Surface

    Returns the current display surface.
    """
    return __workSurf and __workSurf or __displaySurf

#==============================================================================

def clearSurface(surf, rect=None, color=None):
    surf.fill(color or __clearColor, rect or surf.get_rect())

#==============================================================================
    
def update():
    """
    update() -> None
    
    Called once per frame by the engine's main loop to update the display.
    Most user programs should never have to call this directly. Updates and
    draws any shaders in the scene list, in order.
    """
    rectangels = None

    if parole.haveModule['shader']:
        surf = getSurface()
        #for sdr in scene:
        #    sdr.update()
        #    sdr.draw(surf)
        
        # TODO: only clear/blit dirty shaders, and reblit shaders underneath
        scene.clear(surf, clearSurface)
        scene.update()
        for p in scene:
            p.setBlittingParent(scene)
        rectangles = scene.draw(surf)
        #for sdr in scene:
        #    sdr.update()
        #    
        #    # shader-wide alpha and blend functions
        #    if sdr.alpha < 255 and sdr.alpha > 0:
        #        # the surface-wide alpha is < 255, but it also has per-pixel
        #        # alpha. SDL won't combine surface-wide and per-pixel
        #        # alphas, so we have to do it ourselves
        #        alphaSubtractor = pygame.Surface(sdr.size).convert_alpha()
        #        alphaSubtractor.fill((0,0,0, 255 - p.alpha))
        #        # TODO: is it bad that we do this every frame? shouldn't the
        #        # shader just do this itself whenever its alpha changes?
        #        sdr.image.blit(alphaSubtractor, (0,0), 
        #                special_flags=pygame.locals.BLEND_SUB)
        #                       
        #    surf.blit(sdr.image, scene.positionOf[sdr])

        # Flushed queued removals from the scene
        scene.flushRemovals()

    if __workSurf is not None:
        __workSurf.blit(__displaySurf, (0,0))
        pygame.display.flip()
    else:
        pygame.display.update(rectangles)
    __fpsClock.tick()
    if __modeDirty:
        __setMode()

#==============================================================================

def framerate():
    """
    framerate() -> int
    
    Returns the average frames-per-second at which the display has been
    operating for the last few frames.
    """
    return __fpsClock.get_fps()

#==============================================================================

def clampRGB(rgb):
    if rgb and type(rgb) is tuple and len(rgb) == 3:
        r, g, b = rgb
        return (max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)))
    return rgb

#==============================================================================

def interpolateRGB(rgb1, rgb2, percent):
    return (int((rgb2[0]-rgb1[0])*percent + rgb1[0]),
            int((rgb2[1]-rgb1[1])*percent + rgb1[1]),
            int((rgb2[2]-rgb1[2])*percent + rgb1[2]))

#==============================================================================

def screenTextSize(font):
    """
    Returns C{(col,row)} where C{col} is the floor of the width of the screen
    expressed in characters rendered by C{font} (assuming monospace), and
    C{row} is likewise for the height.
    """
    fw, fh = font.size('#')
    sw, sh = getSurface().get_size()
    return (sw/fw, sh/fh)
