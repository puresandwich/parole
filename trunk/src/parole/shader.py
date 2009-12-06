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
TODO: Shader module pydocs.

The Parole shader module provides a 2-D software "shader" system vaguely 
inspired by that of the Cipher Engine. It is intended to supplement, though
not replace, PyGame's system of Surfaces and Sprites.
"""

import pygame, parole, logging, config, resource, cStringIO, math, sys
import re, string, colornames, traceback
import display
from display import clampRGB
from pygame.sprite import *
from pygame.locals import *

def __init():
    """
    Initializes the shader module. Automatically called during engine startup -
    most user code shouldn't need this function.
    """
    pass

def __unload():
    pass

#==============================================================================

#def addConfigOptions():
#    """
#    addConfigOptions() -> None
#    
#    Registers the shader module's config options. Handled by the engine - most
#    user code shouldn't need to call this.
#    """
#    config.categories.append('shader')

#==============================================================================
#{ Main Base Classes
#==============================================================================

class PosDict(dict):
    """
    Utility class for C{positionOf} member variables of C{Shader}
    instances. 
    """
    def __init__(self, shader, *args, **kwargs):
        super(PosDict, self).__init__(*args, **kwargs)
        self.shader = shader

    def __setitem__(self, child, pos):
        if not isinstance(child, Shader) or type(pos) is not tuple or \
                len(pos) != 2 or type(pos[0]) is not int or type(pos[1]) \
                is not int:
            raise TypeError('PosDict: key must be Shader instance and '
                            'value must be tuple of two ints.')

        # Touch the parent shader whenever one of it's children's
        # positions is changed
        if child in self and self[child] != pos:
            self.shader.touch()

        # Store the position
        super(PosDict, self).__setitem__(child, pos)

#==============================================================================

class Shader(Sprite):
    """
    Shader(name, pos=None, size=None, alpha=255, passes=None) -> Shader

    TODO: Shader docs.
    """

    defaultPasses = OrderedUpdates()
    defaultPos = (0,0)
    defaultSize = (1,1)
    defaultAlpha = 255

    shaderCount = 0

    def __init__(self, name, size=None, alpha=255, passes=None, initImage=True):
        Sprite.__init__(self)

        self.__name = '%s%s' % (name, Shader.shaderCount)
        Shader.shaderCount += 1

        self.parents = set()

        # Tracks children's positions
        self.positionOf = PosDict(self)

        self.rect = None

        # Separate our passes instance from the class's
        if not isinstance(self, Pass):
            self.passes = Shader.defaultPasses.copy()
            self.dirtyPasses = Shader.defaultPasses.copy()
            self.updateDirtyPasses = Shader.defaultPasses.copy()
            self.removedPassRects = []
        
        # This keeps track of which blendfunc each pass should use
        # map: pass -> blendfunc
        self.__blendfuncs = {}

        # The shader's update functions
        self.__updateFuncs = []

        # Shader global effects
        #self.__pos = Shader.defaultPos
        self.__size = Shader.defaultSize
        self.__alpha = Shader.defaultAlpha
        #if pos is not None: self.pos = pos       # Shader's onscreen position
        if size is not None: self.size = size    # Onscreen size
        if alpha is not None: self.alpha = alpha # Global alpha
        self.last_size = self.size

        if initImage:
            self.image = pygame.Surface(self.size).convert_alpha()
            display.clearSurface(self.image, self.image.get_rect())
        else:
            self.image = None

        self.__dirty = True

        for p in passes or []:
            self.addPass(p)

        #parole.debug("New %s: %s" % \
        #        (isinstance(self, Pass) and 'Pass' or 'Shader', self))

    def __str__(self):
        return self.name

    def __getstate__(self):
        state = self.__dict__.copy()
        state['image'] = self.image and True or False
        if not self.parents:
            # don't pass along parent groups if we have no actual parents
            # (otherwise pickling any onscreen Shader will end up pickling the
            # whole display scene).
            state['_Sprite__g'] = {}
        #state['_Sprite__g'] = {}
        #state['parents'] = set()

        #parole.debug('Shader.__getstate__: %r', state)
        return state

    def __setstate__(self, state):
        #parole.debug('Shader.__setstate__: %r', state)
        self.__dict__.update(state)
        if self.image:
            self.image = pygame.Surface(self.size).convert_alpha()
            display.clearSurface(self.image, self.image.get_rect())
            self.__dirty = True

    def childRect(self, child):
        """
        The rectangle of the given child shader, indicating position and size.
        """
        return Rect(self.positionOf[child], child.size)

    def touch(self):
        """
        Mark this Shader as "dirty" -- it's image will be updated during the
        next frame. This also marks all parents of this Shader as dirty.
        """
        self.__dirty = True
        self.touchParents()
        
    def touchParents(self):
        """
        Touches all the parents of this Shader, marking them as dirty.
        """
        for p in self.parents: 
            p.touch()
            p.dirtyPasses.add(self)

    def clean(self):
        """
        Marks this Shader as no longer dirty.
        """
        self.__dirty = False
        for p in self.parents:
            p.dirtyPasses.remove(self)

    @property
    def dirty(self):
        """
        Property: whether or not this Shader is dirty.
        """
        return self.__dirty

    @parole.Property
    def pos():
        """
        Property: the position of this Shader within its parent(s). Setting
        this to a new value sets the Shader's position in all of its parents.
        Getting the value returns the Shader's position in its first parent.
        To get or set this Shader's position in a particular parent, use that
        parent's C{positionOf} attribute.
        """
        def fget(self):
            if self.parents:
                for p in self.parents:
                    return p.positionOf[self]
            else:
                return self.defaultPos
        def fset(self, val):
            for p in self.parents:
                p.positionOf[self] = val

    @parole.Property
    def size():
        """
        Property: the rectangular size of this Shader. Setting this to a new
        value touches the Shader.
        """
        def fget(self):
            return self.__size
        def fset(self, val):
            if val != self.__size:
                self.__size = val
                if val:
                    self.rect = pygame.Rect((0,0), val)
                self.touch()

    @parole.Property
    def width():
        def fget(self):
            return self.__size[0]
        def fset(self, val):
            if val != self.__size[0]:
                self.size = (val, self.__size[1])

    @parole.Property
    def height():
        def fget(self):
            return self.__size[1]
        def fset(self, val):
            if val != self.__size[1]:
                self.size = (self.__size[0], val)

    @parole.Property
    def alpha():
        def fget(self):
            return self.__alpha
        def fset(self, val):
            if val != self.__alpha:
                self.__alpha = val
                self.touchParents()

    def setBlittingParent(self, parent):
        self.rect = parent and Rect(parent.positionOf[self], self.size)

    def update(self, parent=None, destImage=None, updatePasses=True,
            blitPasses=True, blitDirtyOnly=False):
        """
        Updates the shader's state. This will cause any animated or otherwise
        time-sensitive effects to advance. The C{parent} argument may
        optionally be supplied to let the shader know which parent is updating
        it, in case the shader's behavior is sensitive to that. The shader
        will update all of its child passes (unless C{updatePasses} is
        C{False}) and blit them (unless C{blitPasses} is C{False}) to the
        shaders image surface (or to C{destImage} if it is supplied).
        """
        if not self.dirty:
            return
        self.clean()

        #parole.debug('Shader/Pass %s: updating...', self)

        # Apply any update functions to ourselves
        for updateFunc in self.__updateFuncs:
            updateFunc(self)

        # Set up our surface on resize
        sizeChanged = False
        if self.size != self.last_size:
            sizeChanged = True
            self.image = pygame.Surface(self.size).convert_alpha()
            display.clearSurface(self.image, self.image.get_rect())
            self.last_size = self.size
            #parole.debug('%s: Adding all passes to dirty', self)
            #self.updateDirtyPasses.add(self.passes)
            if destImage:
                parole.warn("Shader.update(): destination image given, but "
                            "shader size has changed!")
        elif self.image is None:
            self.image = pygame.Surface(self.size).convert_alpha()
            display.clearSurface(self.image, self.image.get_rect())

        #else:
        #    # Passes that were dirty as of this frame/update
        #    self.updateDirtyPasses.add(self.dirtyPasses)

        # Passes have no subpasses, so they need venture no further hence
        if isinstance(self, Pass):
            return

        self.updateDirtyPasses.empty()
        if sizeChanged:
            self.updateDirtyPasses.add(self.passes)
        else:
            self.updateDirtyPasses.add(self.dirtyPasses)

        # Update and blit each pass
        if updatePasses:
            self.updatePasses()
        if blitPasses:
            self.blitPasses(destImage, blitDirtyOnly)

        # make sure that only dirty passes remain in self.dirtyPasses
        # (a non-dirty pass could get in there by via addPass())
        for dp in self.dirtyPasses:
            if not dp.dirty:
                self.dirtyPasses.remove(dp)

    def updatePasses(self):
        """
        Updates the shader's child passes. User shaders should usually call
        this function at some point during their C{update()} if they do not
        call their superclass's C{update()}, or if they specify
        C{updatePasses=False} when they do.
        """
        #parole.debug('%s: updating %s passes: %s', self,
        #        len(self.updateDirtyPasses),
        #        ['%s: %s' % (s, s.rect) for s in self.updateDirtyPasses.sprites()])
        #parole.debug('%s: updating %s passes', self,
        #        len(self.updateDirtyPasses))
        self.updateDirtyPasses.update()

    def blitPasses(self, dest=None, dirtyOnly=False):
        """
        Blits child passes that have changed since they were last blitted to
        this shader's {image}, or to C{dest} if it is given. User shaders
        should usually call this during their C{update()} if they do not
        call their superclass's C{update()}, or if they specify
        C{blitPasses=False} when they do.
        """
        dest = dest or self.image
        passes = dirtyOnly and self.updateDirtyPasses or self.passes

        #parole.debug('%s: blitting %s passes (dirtyOnly=%s): %s', self,
        #        len(passes), dirtyOnly,
        #        ['%s: %s' % (s, s.rect) for s in passes.sprites()])
        #parole.debug('%s: blitting %s passes (dirtyOnly=%s)', self,
        #        len(passes), dirtyOnly)

        if not dirtyOnly:
            parole.display.clearSurface(dest, dest.get_rect())
        else:
            for rect in self.removedPassRects:
                parole.display.clearSurface(dest, rect)
        self.removedPassRects = []

        for p in passes:
            p.setBlittingParent(self)
            if dirtyOnly:
                parole.display.clearSurface(dest, p.rect)
        passes.draw(dest)

    def remPass(self, p):
        """
        Remove first occurrence of the given pass from this shader.
        """

        #parole.debug("Shader %s: removing pass '%s'", self, p)
        self.passes.remove(p)
        self.dirtyPasses.remove(p)
        p.parents.remove(self)
        try:
            self.removedPassRects.append(pygame.Rect(self.positionOf[p], p.size))
            del self.positionOf[p]
        except KeyError:
            pass
        self.touch()
        
    def clearPasses(self):
        """
        Removes all passes from this shader.
        """
        for p in self.passes.sprites():
            self.remPass(p)
        self.touch()

    def addPass(self, p, pos=None):
        """
        Append pass C{p} to this shader, optionally specifying the pass's
        desired position within this Shader. If no position is specified,
        self.defaultPos is used.
        """
        #parole.debug("Shader %s: adding pass %s (%s)" % (self, p, pos or \
        #    self.defaultPos))

        self.passes.add(p)
        self.dirtyPasses.add(p)
        p.parents.add(self)
        self.positionOf[p] = pos or self.defaultPos
        self.touch()

    def addUpdateFunc(self, f):
        """
        Append update function f to this shader.
        """
        parole.debug("Shader %s: adding update function %s" % (self, f))
        self.__updateFuncs.append(f)
        self.touch()

    def remUpdateFunc(self, f):
        """
        Remove update function f from this shader.
        """
        parole.debug("Shader %s: removing update function %s" % (self, f))
        self.__updateFuncs.append(f)
        self.__updateFuncs.remove(f)
        self.touch()

    def centeredPos(self, parent=None):
        """
        Returns the (x,y) coordinates at which this shader would be centered
        on its first parent, or on the given parent, or on the screen if none is
        specified the shader has no parent.
        """
        if (not parent) and self.parents:
            parent = list(self.parents)[0]

        if parent:
            return (int(round(parent.width/2.)) - int(round(self.width/2.)),
                    int(round(parent.height/2.)) - int(round(self.height/2.)))
        else:
            scr = display.getSurface()
            return (scr.get_width()/2 - self.width/2,
                    scr.get_height()/2 - self.height/2)
    
    @property
    def name(self):
        """
        The name of this shader (read-only).
        """

        return self.__name
    
#==============================================================================

class Pass(Shader):
    """
    Pass(name, pos=None, size=None, alpha=255) -> ShaderPass

    Subclasses should be sure to call super(Subclass, self).update() in
    their update override. That will end up calling Shader.update, which
    handles update functions and surface-wide transparency, 

    TODO: Pass docs.
    """

    def __init__(self, name, size=None, alpha=255, initImage=True):
        Shader.__init__(self, name, size, alpha=alpha, initImage=initImage)

    def addPass(self, *args, **kwargs):
        raise ParoleError("Shader-pass can't have subpasses")

    def remPass(self, p):
        raise ParoleError("Shader-pass can't have subpasses")
        

#==============================================================================
#{ Shaders
#==============================================================================

class Frame(Shader):

    # arguments are shaders
    def __init__(self, (left, right, top, bottom, tleft, tright, bleft,
        bright), size=None, maxSize=None, alpha=None, contents=None,
        name=None):

        Shader.__init__(self, name or 'Frame', size=size,
                alpha=alpha, passes=contents)

        self.autoSize = not size
        self.maxSize = maxSize
        self.resizing = False

        # Side borders
        self.left = left or Shader('empty border', size=(0,0))
        self.right = right or Shader('empty border', size=(0,0))
        self.top = top or Shader('empty border', size=(0,0))
        self.bottom = bottom or Shader('empty border', size=(0,0))

        # Corner borders
        self.tleft = tleft or Shader('empty border', size=(0,0))
        self.bleft = bleft or Shader('empty border', size=(0,0))
        self.tright = tright or Shader('empty border', size=(0,0))
        self.bright = bright or Shader('empty border', size=(0,0))

    def frameShaders(self):
        return (self.left, self.right, self.top, self.bottom, self.tleft,
                self.tright, self.bleft, self.bright)

    def __fitToContents(self):
        maxSize = self.maxSize or parole.display.getSurface().get_size()
        maxRect = pygame.Rect((0,0), maxSize)
        clippedContentsRect = pygame.Rect((0,0), (0,0))
        clippedContentsRect.unionall_ip([self.childRect(p).clip(maxRect) for p in \
            self.passes])

        #if self.__lastClippedContentsRect == clippedContentsRect:
        #    return
        #self.__lastClippedContentsRect = clippedContentsRect

        #parole.info('Borders: %s', self.frameShaders())
        #parole.debug('clippedContentsRect: %s', clippedContentsRect)
        #parole.debug('left.width: %s, right.width: %s', self.left.width,
        #        self.right.width)
        newSize = (clippedContentsRect.width + self.left.width + \
                self.right.width, clippedContentsRect.height + self.top.height\
                + self.bottom.height)
        if self.size == newSize:
            # Nothing to do
            return False

        #parole.debug('Frame %s: fitting to contents...', self)
        self.size = newSize
        return True

    def update(self, parent=None):
        if not self.dirty:
            return

        super(Frame, self).update()

        # possibly enlarge self.image to accomodate everything (if
        # self.autoSize is true)
        if self.autoSize:
            if self.__fitToContents():
                self.resizing = True
                self.touch()
                parole.pushAnimation()
            elif self.resizing:
                self.resizing = False
                parole.popAnimation()
            # Also shift contents down and right to accommodate top and left
            # frame shaders
            contentsImage = self.image
            self.image = pygame.Surface(self.size).convert_alpha()
            parole.display.clearSurface(self.image, self.image.get_rect())
            self.image.blit(contentsImage, (self.left.size[0], self.top.size[1]))


        # let the frame shaders update. basically the frame shaders are passes
        # that we blit ourselves, rather than using addPass() and letting
        # Shader.update() blit them, so that we can make sure they're always
        # on top, and determine their postions and sizes on the fly
        self.updateFrameShaders()

        # now blit those suckers
        for fs in self.frameShaders():
            if fs:
                self.image.blit(fs.image, self.positionOf[fs])

    def updateFrameShaders(self):
        self.positionOf[self.left] = (0,self.top.size[1])
        self.left.size = (self.left.size[0], self.size[1] -
                self.top.size[1] - self.bottom.size[1])
        self.left.update()

        self.positionOf[self.right] = (self.size[0]-self.right.size[0],
                self.top.size[1])
        self.right.size = (self.right.size[0], self.size[1] -
                self.top.size[1] - self.bottom.size[1])
        self.right.update()

        self.positionOf[self.top] = (0,0)
        self.top.size  = (self.size[0], self.top.size[1])
        self.top.update()

        self.positionOf[self.bottom] = (0, self.size[1] - self.bottom.size[1])
        self.bottom.size = (self.size[0], self.bottom.size[1])
        self.bottom.update()

        # corners
        if self.tleft:
            self.positionOf[self.tleft] = (0,0)
            self.tleft.update()
        if self.tright:
            self.positionOf[self.tright] = (self.size[0] - self.tright.size[1], 0)
            self.tright.update()
        if self.bleft:
            self.positionOf[self.bleft] = (0, self.size[1] - self.bleft.size[1])
            self.bleft.update()
        if self.bright:
            self.positionOf[self.bright] = (self.size[0] - self.bright.size[0], 
                    self.size[1] - self.bright.size[1])
            self.bright.update()

#==============================================================================

class TextFrame(Frame):
    # arguments are text
    def __init__(self, (left, right, top, bottom, tleft, tright, bleft,
        bright), font, fg_rgb, bg_rgb=None, size=None, maxSize=None,
        alpha=None, contents=None, name=None):

        Frame.__init__(self,
                (left and TextLine(font, left, fg_rgb, bg_rgb,
                                   orientation='vertical'),
                 right and TextLine(font, right, fg_rgb, bg_rgb,
                                   orientation='vertical'),
                 top and TextLine(font, top, fg_rgb, bg_rgb,
                                   orientation='horizontal'),
                 bottom and TextLine(font, bottom, fg_rgb, bg_rgb,
                                   orientation='horizontal'),
                 tleft and TextBlockPass(font, fg_rgb, bg_rgb, tleft,
                     wrap='no'),
                 tright and TextBlockPass(font, fg_rgb, bg_rgb, tright,
                     wrap='no'),
                 bleft and TextBlockPass(font, fg_rgb, bg_rgb, bleft,
                     wrap='no'),
                 bright and TextBlockPass(font, fg_rgb, bg_rgb, bright,
                     wrap='no')),
                size=size, maxSize=maxSize, alpha=alpha,
                contents=contents, name=name)


#==============================================================================

class TextureFrame(Frame):
    # arguments texture surfaces or names of texture resources
    def __init__(self, (left, right, top, bottom, tleft, tright, bleft,
        bright), font, fg_rgb, bg_rgb=None, size=None, maxSize=None,
        alpha=None, contents=None, name=None):

        if type(left) is str:
            left = resource.getTexture(left)
        if type(right) is str:
            right = resource.getTexture(right)
        if type(top) is str:
            top = resource.getTexture(top)
        if type(bottom) is str:
            bottom = resource.getTexture(bottom)
        if type(tleft) is str:
            tleft = resource.getTexture(tleft)
        if type(tright) is str:
            tright = resource.getTexture(tright)
        if type(bleft) is str:
            bleft = resource.getTexture(bleft)
        if type(bright) is str:
            bright = resource.getTexture(bright)

        left = TexturePass(left)
        right = TexturePass(right)
        top = TexturePass(top)
        bottom = TexturePass(bottom)
        tleft = TexturePass(tleft)
        tright = TexturePass(tright)
        bleft = TexturePass(bleft)
        bright = TexturePass(bright)

        Frame.__init__(self, (left, right, top, bottom, tleft, tright, bleft,
            bright), font, fg_rgb, bg_rgb=bg_rgb, size=size,
            maxSize=maxSize, alpha=alpha, contents=contents, name=name)

#==============================================================================

class ScrollView(Shader):
    def __init__(self, size, offset=(0,0), vbar=None, hbar=None,
            alpha=255, contents=None, name=None, followY=False):
        Shader.__init__(self, name or 'ScrollView', size, alpha=alpha,
                passes=contents)
        self.__offset = offset
        self.__vbar, self.__hbar = None, None
        self.vbar, self.hbar = vbar, hbar
        self.__contentsImage = self.image
        self.followY = followY
        self.__viewDirty = True
        self.touchView()

    def touchView(self):
        self.__viewDirty = True
        self.touchParents()

    @parole.Property
    def offset():
        def fget(self):
            return self.__offset
        def fset(self, val):
            vx, vy = val
            val = (max(0,vx), max(0,vy))
            if val != self.__offset:
                self.__offset = val
                self.touchView()

    @parole.Property
    def vbar():
        def fget(self):
            return self.__vbar
        def fset(self, val):
            if val != self.__vbar:
                if self.__vbar:
                    self.__vbar.parents.remove(self)
                self.__vbar = val
                if val:
                    self.__vbar.parents.add(self)
                self.touchView()

    @parole.Property
    def hbar():
        def fget(self):
            return self.__hbar
        def fset(self, val):
            if val != self.__hbar:
                if self.__hbar:
                    self.__hbar.parents.remove(self)
                self.__hbar = val
                if val:
                    self.__hbar.parents.add(self)
                self.touchView()

    def contentsSize(self):
        contentsRect = pygame.Rect((0,0), (0,0)).unionall([self.childRect(p) \
            for p in self.passes])
        contentsRect.top = 0
        contentsRect.left = 0
        #parole.debug('ScrollView: contentsSize = %s', contentsRect.size)
        return contentsRect.size

    def visibleRect(self):
        vbarImg = None
        if self.vbar:
            vbarImg = self.renderVBar()
        hbarImg = None
        if self.hbar:
            hbarImg = self.renderHBar()
        viewRegion = pygame.Rect(self.offset,
                (self.width - (vbarImg and vbarImg.get_width() or 0), 
                 self.height - (hbarImg and hbarImg.get_height or 0)))
        viewRegion = viewRegion.clip(self.__contentsImage.get_rect())
        return viewRegion

    def update(self, parent=None, blitDirtyOnly=False):
        time = parole.time()
        if not ((self.dirty and self.dirtyPasses) or self.__viewDirty):
            return
        contentsSize = self.contentsSize()
        if self.dirty and self.dirtyPasses:
            wasDirty = True
            #parole.debug('%s: updating contents...', self)

            super(ScrollView, self).update(updatePasses=True, blitPasses=False)

            if len(self.passes) == 1:
                # We can be significantly faster if we know there's only one
                # pass (so it doesn't need to be blitted along with any
                # others)
                self.__contentsImage = self.passes.sprites()[0].image
            else:
                # TODO: this is probably buggered.
                # Otherwise, if there are multiple passes, we have to blit
                # them all in order to create the new contents image
                parole.debug('multiple passes')
                if (not self.__contentsImage) or contentsSize != \
                        self.__contentsImage.get_size():
                    self.__contentsImage = \
                        pygame.Surface(contentsSize).convert_alpha()

                display.clearSurface(self.__contentsImage,
                        self.__contentsImage.get_rect())
                parole.debug('blitting passes, dirtyOnly=%r', blitDirtyOnly)
                self.blitPasses(dest=self.__contentsImage, dirtyOnly=blitDirtyOnly)
    
        atBottom = (self.offset[1] >= contentsSize[1] - self.size[1])
        if atBottom and self.followY:
            self.scrollPixels(0, self.__contentsImage.get_size()[1])

        #parole.debug('%s: updating view (offset=%s)...',
        #        self, self.offset)

        viewRegion = self.visibleRect()

        vbarImg = None
        if self.vbar:
            vbarImg = self.renderVBar()
        hbarImg = None
        if self.hbar:
            hbarImg = self.renderHBar()

        #parole.debug('viewRegion = %s', viewRegion)
        #parole.debug('contentsSize = %s', self.contentsSize())
        #parole.debug('contents image size = %s',
        #        self.__contentsImage.get_size())
        #parole.debug('contents image rect = %s',
        #        self.__contentsImage.get_rect())

        if not self.vbar and not self.hbar:
            self.image = self.__contentsImage.subsurface(viewRegion)#.copy()
        else:
            #self.image = self.__contentsImage.subsurface(viewRegion).copy()
            self.image = pygame.Surface(self.size).convert_alpha()
            display.clearSurface(self.image, self.image.get_rect())
            self.image.blit(self.__contentsImage.subsurface(viewRegion),
                    (0,0))

        if vbarImg:
            self.image.blit(vbarImg, (self.width - vbarImg.get_width(), 0))

        self.__viewDirty = False
        #parole.debug('ScrollView.update: time = %s', parole.time() - time)

    def scrollPixels(self, dx, dy):
        #parole.debug('ScrollView.scrollPixels(%s, %s)', dx, dy)
        cSize = self.contentsSize()
        newOffset = (min((max((self.offset[0]+dx, 0)),
            max(cSize[0]-self.width, 0))), 
                min((max((self.offset[1]+dy, 0)), cSize[1]-self.height)))
        self.offset = newOffset

    def renderVBar(self):
        viewTop = self.offset[1]
        viewBottom = viewTop + self.size[1]
        contentsHeight = float(self.__contentsImage.get_height())

        viewPercentage = 1.0
        if contentsHeight:
            topPercentage = min((float(viewTop) / contentsHeight, 1.0))
            viewPercentage = min((float(viewBottom - viewTop) / contentsHeight,
                    1.0))

        if viewPercentage == 1.0:
            # no need to draw scroll bar if we can see everything already
            return None

        vbar = self.vbar
        vbar.scrollTop = topPercentage
        vbar.scrollHeight = viewPercentage
        vbar.size = (vbar.size[0], self.size[1])
        vbar.update()
        #self.image.blit(vbar.image, (self.size[0] - vbar.size[0], 0))
        return vbar.image

#==============================================================================

class ReadLineBox(Shader):
    def __init__(self, font, width, prompt="", alpha=255, name="ReadLineBox"):
        size = (width, font.get_linesize())
        Shader.__init__(self, name, size=size, alpha=alpha)

        self.prompt = prompt
        self.scroll = ScrollView(self.size) 
        self.textblock = TextBlockPass(font, (255,255,255), wrap='no',
                ignoreMarkup=True)
        self.textblock.text = self.prompt + '\v'
        self.scroll.addPass(self.textblock, pos=(0,0))
        self.addPass(self.scroll, pos=(0,0))

    def onInput(self, readline):
        self.textblock.text = self.prompt + readline.text[:readline.cursorPos] + '\v' + \
                readline.text[readline.cursorPos:]
        # scroll horizontally so that the cursor is visible
        self.scroll.offset = (0,0)
        if readline.cursorPos > 0:
            while self.textblock.cursorPos[0] > self.scroll.offset[0] + self.width:
                self.scroll.scrollPixels(64, 0)
            while self.textblock.cursorPos[0] < self.scroll.offset[0]:
                self.scroll.scrollPixels(-64, 0)
        
#==============================================================================

class FPS(Frame):

    def __init__(self, font, fg_rgb=(255,255,255), bg_rgb=None,
            precision=2, name='FPS'):

        self.textblock = TextBlockPass(font, fg_rgb, bg_rgb=bg_rgb)
        Frame.__init__(self, (None,)*8, name=name, contents=[self.textblock])
        self.precision = precision

    def update(self):
        self.textblock.text = ('%%.%df' % self.precision) % \
            display.framerate()
        super(FPS, self).update()
        self.touch()

#==============================================================================

class ShaderGrid(Shader):

    def __init__(self, gridSize, tileSize, name='ShaderGrid'):
        super(ShaderGrid, self).__init__(name, (gridSize[0]*tileSize[0],
            gridSize[1]*tileSize[1]))

        self.__gridSize = gridSize
        self.__tileSize = tileSize

        self.resetGrid()

    def __getstate__(self):
        parole.warn('Pickling ShaderGrid!')
        return super(ShaderGrid, self).__getstate__()

    @parole.Property
    def gridSize():
        def fget(self):
            return self.__gridSize

    @parole.Property
    def tileSize():
        def fget(self):
            return self.__tileSize

    def resetGrid(self):
        self.__grid = []
        cols, rows = self.gridSize
        tileWidth, tileHeight = self.tileSize
        posy = 0
        for rowIdx in range(rows):
            row = []
            posx = 0

            for colIdx in range(cols):
                # the grid begins populated by blank tiles, indicated by None
                row.append(None)
                posx += tileWidth

            self.__grid.append(row)
            posy += tileHeight

    def __getitem__(self, coords):
        if type(coords) is int:
            # interpreted as row index
            return self.__grid[coords]
        elif type(coords) is tuple:
            if (not len(coords) == 2) or (type(coords[0]) is not int) or \
                    (type(coords[1]) is not int):
                raise TypeError('coords must be a single int or a tuple of 2 integers')
            # interpreted as col,row
            return self.__grid[coords[1]][coords[0]]
        else:
            raise TypeError('coords must be a single int or a tuple of 2 integers')

    def __setitem__(self, coords, value):
        # interpreted as col,row
        if type(coords) is tuple:
            if (not len(coords) == 2) or (type(coords[0]) is not int) or \
                    (type(coords[1]) is not int):
                raise TypeError('coords must be a a tuple of 2 integers')
            if not (isinstance(value, Shader) or value is None):
                raise TypeError('value must be a Shader object (or None)')

            tileWidth, tileHeight = self.tileSize
            oldPass = self.__grid[coords[1]][coords[0]]
            if oldPass is value:
                return
            if oldPass and oldPass in self.passes:
                self.remPass(oldPass)

            self.__grid[coords[1]][coords[0]] = value

            if value:
                pos = (coords[0]*tileWidth, coords[1]*tileHeight)
                self.addPass(value, pos=pos)

        else:
            raise TypeError('coords must be a a tuple of 2 integers')

    def posOf(self, coords):
        tileWidth, tileHeight = self.tileSize
        return (coords[0]*tileWidth, coords[1]*tileHeight)

    def rectOf(self, coords):
        tileWidth, tileHeight = self.tileSize
        pos = (coords[0]*tileWidth, coords[1]*tileHeight)
        return Rect(pos, self.tileSize)

    def disable(self, x, y):
        xyPass = self[x,y]
        if xyPass and xyPass in self.passes:
            self.remPass(xyPass)

    def enable(self, x, y):
        xyPass = self[x,y]
        if xyPass and xyPass not in self.passes:
            tileWidth, tileHeight = self.tileSize
            pos = (x*tileWidth, y*tileHeight)
            self.addPass(xyPass, pos=pos)

    def update(self):
        time = parole.time()
        super(ShaderGrid, self).update(blitDirtyOnly=True)
        #parole.debug('ShaderGrid.update: time = %s', parole.time() - time)


#==============================================================================
#{ Passes
#==============================================================================

class SurfacePass(Pass):
    def __init__(self, surf):
        Pass.__init__(self, 'SurfacePass', surf.get_size(), initImage=False)
        self.image = surf

#==============================================================================

class ColorField(Pass):
    """
    ColorField(rgb, size, alpha=255) -> ColorField

    The ColorField pass draws a rectangular field of one solid color. rgb should
    be a 3-tuple defining the desired color.
    """
    def __init__(self, rgb, size, alpha=255):
        Pass.__init__(self, 'ColorField', size, alpha)
        self.__rgb = clampRGB(rgb)

    @parole.Property
    def rgb():
        def fget(self):
            return self.__rgb
        def fset(self, val):
            if val != self.__rgb:
                self.__rgb = clampRGB(val)
                self.touch()
        
    def update(self, parent=None):
        if not self.dirty:
            return

        super(ColorField, self).update(parent=parent)
        self.image.fill(self.rgb)

#==============================================================================

class TexturePass(Pass):
    """
    TexturePass(texture, size=None, alpha=255) -> TexturePass

    Creates a pass which draws a texture (or image). If texture is a string,
    it should name a resource which TexturePass will attempt to load from
    the resource module. Otherwise it should be a PyGame Surface object, in 
    case this pass will draw the Surface by reference (i.e., subsequent
    changes to the Surface object will be reflected in what the pass draws,
    and any update functions acting on this pass *will* affect the Surface
    object given).
    If size is specified, the texture will be scaled. If size is None, the
    texture will be drawn at its native size.
    """
    def __init__(self, texture, size=None, alpha=255):
        Pass.__init__(self, 'TexturePass', size, alpha)
        if type(texture) is str:
            self.texture = resource.getTexture(texture)
            if not self.texture:
                raise ValueError, 'Could not load texture: %s' % (texture,)
        elif isinstance(texture, pygame.Surface):
            self.texture = texture
        else:
            raise TypeError, 'texture must be a string or Surface'

        if not size:
            self.size = self.texture.get_size()
        
    def update(self, parent=None):
        if not self.dirty:
            return

        super(TexturePass, self).update(parent=parent)
        
        if self.size != self.texture.get_size():
            self.image.blit(pygame.transform.scale(self.texture, self.size),
                (0,0))
        else:
            self.image.blit(self.texture, (0,0))

#==============================================================================

# Markup symbols at LF
NEWLINE = 1
TAB = 2
CURSOR = 3
OPENSCOPE = 4
CLOSESCOPE = 5
DIRECTIVE = 6
ESCAPE = 7

class TextBlockPass(Pass):

    # The number of space (C{' '}) characters that a tab (C{'\t'}) should be
    # rendered as equivalent to.
    tabWidth = 4

    # Automatically flush the C{TextBlockPass} after this many
    # bytes/characters have been written to it.
    autoFlushLen = 64

    # The rendered text will be broken into independent C{Surface}s or
    # "chunks", each containing this many bytes of text.
    chunkSize = 64 

    # Markup sequences that should be parsed when rendering text.
    # TODO: Support for markup patterns defined by regular expressions.
    markups = {
        NEWLINE:        '\n',
        TAB:            '\t',
        CURSOR:         '\v',
        OPENSCOPE:      '{',    # Pushes a new render state
        CLOSESCOPE:     '}',    # Pops render state
        DIRECTIVE:      '\\',   # Symbol for introducing rendering directives,
                                # as in "\mydirective"
        #ESCAPE:         '\\'    # Any markup symbol following this is
                                # preserved uninterpreted
    }

    # Characters allowed in rendering directive names; the name of a directive
    # is interpreted as ending as soon as a character not among these is
    # encountered
    directiveChars = string.letters + string.digits + \
            ''.join([s for s in string.punctuation if s not in ('{', '}',
                '\\')])
    
    def __init__(self, font, fore_rgb, bg_rgb=None, text=None,
            align='left', wrap='char', wrap_width=None, alpha=255,
            antialias=True, ignoreMarkup=False, bold=False, italic=False,
            underline=False):

        Pass.__init__(self, 'TextBlockPass', None, alpha)

        if text:
            self.__buffer = cStringIO.StringIO(text)
        else:
            self.__buffer = cStringIO.StringIO()
        self.font = font
        self.fore_rgb = clampRGB(fore_rgb)
        self.bg_rgb = clampRGB(bg_rgb)
        if align not in ['left', 'right', 'center']:
            raise ValueError('TextBlockPass "align" parameter must be one of' +
                    + '"left", "right", or "center".')
        self.align = align
        if wrap not in ['char', 'word', 'no', None]:
            raise ValueError('TextBlockPass "wrap" parameter must be one of' +
                    + '"char", "word", "no", or None.')
        self.wrap = wrap
        self.wrap_width = wrap_width
        self.antialias = antialias
        self.cursorPos = None
        self.chunks = []

        self.bold = bold
        self.italic = italic
        self.underline = underline

        self.renderStateStack = [self.RenderState(self)]
        self.ignoreMarkup = ignoreMarkup

    def __len__(self):
        return len(self.text)

    # TODO: use @Property setters for automatic dirty marking

    @parole.Property
    def text():
        def fget(self):
            return self.__buffer.getvalue()
        def fset(self, val):
            self.__buffer.truncate(0)
            self.write(val)
            self.flush()

    def write(self, bytes):
        """
        Append the given bytes of text to this C{TextBlockPass}. Automatically
        flushes the C{TextBlockPass} if C{len(bytes)} >=
        C{TextBlockPass.autoFlushLen}. New text will not be rendered until the
        next C{flush()} and C{update()}.
        """
        self.__buffer.write(bytes)
        if len(bytes) >= self.autoFlushLen:
            self.flush()

    def writelines(self, lines):
        """
        Append the given list of lines of text to this C{TextBlockPass} and
        C{flush()} it.
        """
        self.__buffer.writelines(lines)
        self.flush()

    def flush(self):
        """
        Flush this C{TextBlockPass}, causing the next C{update()} to render
        any new or changed text.
        """
        self.__buffer.flush()
        self.touch()

    def update(self, parent=None):
        if not self.dirty:
            return

        super(TextBlockPass, self).update(parent=parent)

        self.__renderText()
        self.size = self.image.get_size()
        self.last_size = self.size

    #=============================#
    # End public interface mehods #
    #=============================#

    def __renderText(self):
        #parole.debug('render text: %s', self)

        # break text up into its 'logical form' (LF): a sequence of text-spans
        # and markup
        text_LF = self.__parseLogicalForm(self.text)

        #parole.debug('text_LF = %s', text_LF)

        # Render and blit the resulting chunks of text
        self.__renderChunks(text_LF)
        self.__blitChunks()

    class RenderDirective:
        def __init__(self, directive):
            self.directive = directive

        def __repr__(self):
            return "RenderDirective(%s)" % self.directive

        def __str__(self):
            return repr(self)

        def __len__(self):
            return len(self.directive)

    def parse(self, text):
        parole.debug("Parsing: %s", text)
        return self.__parseLogicalForm(text)

    def __parseLogicalForm(self, text):
        #parole.debug("Parsing: %s", text)
        # break text up into its 'logical form' (LF): a sequence of text-spans
        # and markup symbols
        renderState = self.renderStateStack[-1]
        text_LF = [text]
        for markup, pattern in self.markups.items():
            # Don't parse any non-essential markup if we're supposed to ignore
            # markup
            if self.ignoreMarkup and markup not in (NEWLINE, TAB, CURSOR):
                continue

            # TODO: do actual regexp pattern matching for arbitrary markups
            # with arguments, etc.
            new_LF = []
            for span in text_LF:
                if span in self.markups or isinstance(span,
                        self.RenderDirective):
                    new_LF.append(span)
                    continue

                assert type(span) is str

                # split the existing span on the current markup symbol
                newSpans = span.split(pattern)

                # process each new span of text occurring between instances of
                # the current markup symbol
                for (i,s) in enumerate(newSpans):
                    # if the last span was the directive symbol, parse out
                    # the name of the directive
                    if len(new_LF) and new_LF[-1] == DIRECTIVE:
                        directiveName = ''
                        for c in s:
                            if c not in self.directiveChars:
                                break
                            directiveName += c
                        if len(directiveName):
                            new_LF.append(TextBlockPass.RenderDirective(\
                                    directiveName))
                        else:
                            parole.error('TextBlockPass: Parse error: ' + \
                                    'Empty render directive in text.')
                        # chop the directive name off the front of s,
                        # consuming a space if one's there
                        if len(s) == len(directiveName):
                            s = ''
                        elif s[len(directiveName)] == ' ':
                            # consume space
                            if len(s) > len(directiveName) + 1:
                                s = s[len(directiveName)+1:]
                            else:
                                s = ''
                        else:
                            s = s[len(directiveName):]

                    # add text to the LF
                    if len(s):
                        new_LF.append(s)

                    # and add the current markup symbol to LF if we're not at
                    # the last new span
                    if i != len(newSpans) - 1:
                        new_LF.append(markup)

            text_LF = new_LF

        #parole.debug("LF: %s", text_LF)
        return text_LF

    class RenderState:
        def __init__(self, parent):
            self.fore_rgb = parent.fore_rgb
            self.bg_rgb = parent.bg_rgb
            self.font = parent.font
            self.antialias = parent.antialias
            self.cursorColor = (255,255,0)
            self.italic = parent.italic
            self.bold = parent.bold
            self.underline = parent.underline

        def __str__(self):
            return 'RenderState<fore_rgb=%s>' % (repr(self.fore_rgb),)

        def __repr__(self):
            return str(self)

        def getColor(self, color):
            for knownColor in colornames.colors:
                if knownColor.lower() == color.lower():
                    return colornames.colors[knownColor]
            try:
                r, g, b = [int(x) for x in color.split(',')]
            except ValueError:
                return None
            
            return (r,g,b)

        def handleDirective(self, dir):
            dl = dir.directive.lower()
            # Foreground colors
            c = self.getColor(dir.directive)
            if c:
                self.fore_rgb = c
                return
            elif dir.directive.startswith('fg'):
                c = self.getColor(dir.directive[2:])
                if c:
                    self.fore_rgb = c
                else:
                    parole.error('TextBlockPass: Unknown fg color: "%s"',
                            dir.directive)
                return
            # Background colors
            elif dir.directive.startswith('bg'):
                c = self.getColor(dir.directive[2:])
                if c:
                    self.bg_rgb = c
                elif dir.directive[2:].lower() == 'none':
                    self.bg_rgb = None
                else:
                    parole.error('TextBlockPass: Unknown bg color: "%s"',
                            dir.directive)
                return
            # Antialias toggles
            elif dl == 'antialias':
                self.antialias = True
                return
            elif dl == 'noantialias':
                self.antialias = False
                return

            # bold, it, ul
            elif dl == 'bold':
                self.bold = True
                return
            elif dl == 'it':
                self.italic = True
                return
            elif dl == 'ul':
                self.underline = True
                return

            # TODO: general font selection

            parole.error('TextBlockPass: Unknown render directive "%s"' +\
                    ' in text.', dir.directive)

        def renderSpanText(self, text):
            self.font.set_bold(self.bold)
            self.font.set_italic(self.italic)
            self.font.set_underline(self.underline)

            if self.bg_rgb:
                return self.font.render(text, self.antialias, self.fore_rgb,
                        self.bg_rgb)
            else:
                return self.font.render(text, self.antialias, self.fore_rgb)

        def fontSize(self, text):
            sz = self.font.size(text)
            #parole.debug('renderState.fontSize(): %s', sz)
            return sz

        def fontLineSize(self):
            return self.font.get_linesize()

    def __breakSpan(self, span, xpos, renderState, wrapWidth):
        if self.wrap is None or self.wrap == 'no' or not self.wrap_width:
            return [span]

        wrapped_LF = []
        #wrapWidth = self.size[0]
        #wrapWidth = self.wrap_width
        span = span.strip()
        #parole.debug('wrapWidth = %d', wrapWidth)

        parole.debug('Wrapping span: %r', span)
        spanWidth = renderState.fontSize(span)[0]
        if xpos + spanWidth <= wrapWidth:
            parole.debug('1')
            wrapped_LF.append(span)
        else:
            parole.debug('2')
            # we need to find the rightmost point at which to split the span
            units = (self.wrap == 'word' and span.split() or list(span))
            if len(units) == 1:
                # the span is only one word, so we have to force
                # character-wrapping
                units = list(span)
                wrapType = 'char'
            else:
                wrapType = self.wrap
            parole.debug('units = %s', units)
            subspan = ''
            sep = ''

            # any units that are themselves bigger than wrapWidth should be
            # broken up into individual characters
            toBreak = []
            noSpaceIdxs = []
            for u in units:
                if renderState.fontSize(u)[0] > wrapWidth:
                    toBreak.append(u)
            for u in toBreak:
                idx = units.index(u)
                units.remove(u)
                noSpaceIdxs += range(idx, len(u))
                for char in reversed(list(u)):
                    units.insert(idx, char)

            for idx, u in enumerate(units):
                parole.debug('subspan = %r', subspan)
                parole.debug('f')
                if xpos + renderState.fontSize(subspan + sep + u)[0] <= wrapWidth:
                    parole.debug('f1')
                    subspan += sep + u
                else:
                    parole.debug('f2')
                    #print 'Breaking subspan: %s' % subspan
                    wrapped_LF += [subspan, NEWLINE]
                    span = span[len(subspan):]#.strip()
                    while span[0] == ' ':
                        span = span[1:]
                    break
                if wrapType == 'word':
                    parole.debug('f3')
                    if idx in noSpaceIdxs:
                        parole.debug('f3a')
                        sep = ''
                    else:
                        parole.debug('f3b')
                        sep = ' '
            parole.debug('g')
            parole.debug('subspan = %r, span = %r', subspan, span)
            #assert(span.strip() != subspan)
            wrapped_LF.append(span)

        return wrapped_LF

    def __renderSpans(self, text_LF):
        renderedSpans = [] # list of ((x, y), surface) tuples

        # Initial positions and sizes
        xpos = 0
        ypos = 0
        self.cursorPos = None
        wrapWidth = self.wrap_width or 0xFFFFFF

        # We start with the render state at the top of the stack
        renderState = self.renderStateStack[0]
        #parole.debug('Initial render state: %s', renderState)

        i = 0
        while i < len(text_LF):
            #parole.debug('renderSpans: i = %d, len(text_LF) = %d', i,
            #        len(text_LF))
            span = text_LF[i]
            i += 1 # i now points to the next span
            # Handle positional markups
            # NEWLINE
            if span == NEWLINE:
                #parole.debug('NEWLINE')
                xpos = 0
                ypos += renderState.fontLineSize()
                continue

            # TAB
            elif span == TAB:
                #parole.debug('TAB')
                # calculate nearest tab location
                spaceWidth = renderState.fontSize(' ')[0]
                tabWidth = spaceWidth * self.tabWidth
                tabPos = int(math.ceil(float(xpos) / float(tabWidth))) \
                        * tabWidth
                if tabPos == xpos:
                    xpos += tabWidth
                else:
                    xpos = tabPos

                if xpos > wrapWidth:
                    ypos += renderState.fontLineSize()
                    xpos = tabWidth
                continue

            # CURSOR
            elif span == CURSOR:
                #parole.debug('CURSOR')
                self.cursorPos = (xpos, ypos)
                # The cursor gets drawn after everything else (see below)
                continue

            elif span == OPENSCOPE:
                renderState = TextBlockPass.RenderState(renderState)
                #parole.debug('PUSHING new render state: %s', renderState)
                self.renderStateStack.insert(0, renderState)
                continue

            elif span == CLOSESCOPE:
                self.renderStateStack.pop(0)
                renderState = self.renderStateStack[0]
                #parole.debug('POPPING render state: %s', renderState)
                continue

            elif isinstance(span, TextBlockPass.RenderDirective):
                #parole.debug('Stack before command: %s',
                #        self.renderStateStack)
                renderState.handleDirective(span)
                #parole.debug('Stack after command: %s',
                #        self.renderStateStack)
                continue

            elif span == DIRECTIVE:
                continue

            # Handle an actual span of text
            spanSize = renderState.fontSize(span)

            if xpos + spanSize[0] > wrapWidth:
                # wrap it
                #parole.debug('WRAP')
                newSpanLF = self.__breakSpan(span, xpos, renderState, wrapWidth)
                for s in reversed(newSpanLF):
                    text_LF.insert(i, s)
            else:
                #parole.debug('NO WRAP: %s', span)
                # no wrapping
                img = renderState.renderSpanText(span)

                renderedSpans.append(((xpos, ypos), img))
                xpos += img.get_width()

            #parole.debug('xpos: %s, ypos: %s', xpos, ypos)

        # add a span for the cursor
        if self.cursorPos:
            cursorImg = \
                pygame.Surface((1,renderState.fontLineSize())).convert_alpha()
            cursorImg.fill(renderState.cursorColor)
            renderedSpans.append((self.cursorPos, cursorImg))

        #parole.debug('renderedSpans: %s', renderedSpans)
        return renderedSpans

    def __blitSpans(self, renderedSpans):
        # create a big surface and blit all of the lines to it

        #parole.debug('blitSpans')
        totalRect = Rect((0,0),(0,0)).unionall([Rect(pos, span.get_size()) \
            for pos, span in renderedSpans])
        #parole.debug('totalRect: %s', totalRect)
        totalSize = totalRect.size
        surf = pygame.Surface(totalSize).convert_alpha()
        surf.fill((0,1,1,0))

        for pos, span in renderedSpans:
            surf.blit(span, pos)
        return surf

    class Chunk:
        def __init__(self, start, end, LF, surface=None):
            # where start and end are indices into text_LF.
            self.start, self.end = start, end
            self.LF, self.surface = LF, surface

        def __str__(self):
            return '<%s>' % ', '.join([str(x) for x in self.LF])

        def __repr__(self):
            return '<%s>' % ', '.join([str(x) for x in self.LF])

    def __renderChunks(self, text_LF):
        #parole.debug('renderChunks')
        # self.chunks tracks our text chunks. 
        # Every chunk must end with a newline if another chunk follows it.
        
        # break text_LF into chunks of length at least self.chunkSize. Each
        # must end with a newline unless it is the last chunk.
        newChunks = []
        bytes = 0
        curChunk = TextBlockPass.Chunk(0, 0, [])
        for i, item in enumerate(text_LF):
            if item == NEWLINE or item == TAB:
                bytes += len(self.markups[item])
            elif item not in self.markups:
                bytes += len(item)

            curChunk.LF.append(item)

            if (bytes >= self.chunkSize and item == NEWLINE) \
                    or i == len(text_LF)-1:
                curChunk.end = i
                newChunks.append(curChunk)
                curChunk = TextBlockPass.Chunk(0, 0, [])
                bytes = 0
        newChunks.append(curChunk)

        # compare newChunks to the old self.chunks. render any new chunks or
        # chunks that have changed.
        for chunk in newChunks:
            # check the old self.chunks for any chunk with the same Lf as this
            # one so that we can reuse its surface
            # TODO: this won't always work since same LF doesn't always mean
            # same render state(s).
            for oldChunk in self.chunks:
                if oldChunk.LF == chunk.LF:
                    # Steal the old chunk's surface
                    chunk.surface = oldChunk.surface
                    #parole.debug('Reusing chunk!')
                    break

            # if no old chunk had the same LF, we need to render this chunk's
            # surface ourselves
            if (not chunk.surface) and chunk.LF:
                #parole.debug('Rendering chunk!')
                renderedSpans = self.__renderSpans(chunk.LF)
                chunk.surface = self.__blitSpans(renderedSpans)

        self.chunks = newChunks
        #parole.debug('Chunks: %s', self.chunks)

    def __blitChunks(self):
        #parole.debug('blitChunks')
        totalWidth, totalHeight = 0, 0
        for chunk in self.chunks:
            if chunk.surface:
                totalHeight += chunk.surface.get_height()
                totalWidth = max((totalWidth, chunk.surface.get_width()))

        #parole.debug('total size of chunks: %s', (totalWidth, totalHeight))
        self.image = pygame.Surface((totalWidth, totalHeight)).convert_alpha()
        self.image.fill((0,1,1,0))

        ypos = 0
        for chunk in self.chunks:
            if chunk.surface:
                self.image.blit(chunk.surface, (0,ypos))
                ypos += chunk.surface.get_height()

#==============================================================================

class VerticalScrollbar(Pass):
    def __init__(self, rgb, bg_rgb, width, alpha=255):
        Pass.__init__(self, 'VerticalScrollbar', size=(width,0), alpha=alpha)
        self.__rgb = clampRGB(rgb)
        self.__bg_rgb = clampRGB(bg_rgb)

        self.__scrollTop = 0.0
        self.__scrollHeight = 0.0

    @parole.Property
    def rgb():
        def fget(self):
            return self.__rgb
        def fset(self, val):
            if val != self.__rgb:
                self.__rgb = clampRGB(val)
                self.touch()
        
    @parole.Property
    def bg_rgb():
        def fget(self):
            return self.__bg_rgb
        def fset(self, val):
            if val != self.__bg_rgb:
                self.__bg_rgb = clampRGB(val)
                self.touch()
        
    @parole.Property
    def scrollTop():
        def fget(self):
            return self.__scrollTop
        def fset(self, val):
            if val != self.__scrollTop:
                self.__scrollTop = float(val)
                self.touch()
        
    @parole.Property
    def scrollHeight():
        def fget(self):
            return self.__scrollHeight
        def fset(self, val):
            if val != self.__scrollHeight:
                self.__scrollHeight = float(val)
                self.touch()
        
    def update(self, parent=None):
        if not self.dirty:
            return

        super(VerticalScrollbar, self).update(parent=parent)

        self.image.fill(self.bg_rgb)

        shuttleHeight = int(self.scrollHeight * float(self.size[1]))
        shuttleTop = int(self.scrollTop * float(self.size[1]))
        if shuttleTop + shuttleHeight > self.size[1]:
            shuttleTop = self.size[1] - shuttleHeight

        shuttleRect = pygame.Rect((0, shuttleTop), (self.size[0],
            shuttleHeight))
        self.image.subsurface(shuttleRect).fill(self.rgb)

#==============================================================================

class VerticalBevel(Pass):
    def __init__(self, left_rgb, center_rgb, right_rgb, left_width,
            center_width, right_width, alpha=None):
        s = (left_width + center_width + right_width, 0)
        Pass.__init__(self, 'VerticalBevel', size=s, alpha=alpha)
        self.__left_width, self.__right_width, self.__center_width = 0,0,0
        self.left_rgb, self.center_rgb, self.right_rgb = left_rgb, center_rgb, right_rgb
        self.left_width, self.center_width, self.right_width = left_width, center_width, right_width

    @parole.Property
    def left_rgb():
        def fget(self):
            return self.__left_rgb
        def fset(self, val):
            self.__left_rgb = val
            self.touch()

    @parole.Property
    def center_rgb():
        def fget(self):
            return self.__center_rgb
        def fset(self, val):
            self.__center_rgb = val
            self.touch()

    @parole.Property
    def right_rgb():
        def fget(self):
            return self.__right_rgb
        def fset(self, val):
            self.__right_rgb = val
            self.touch()

    @parole.Property
    def left_width():
        def fget(self):
            return self.__left_width
        def fset(self, val):
            self.__left_width = val
            self.size = (self.left_width + self.center_width +
                    self.right_width, self.height)

    @parole.Property
    def center_width():
        def fget(self):
            return self.__center_width
        def fset(self, val):
            self.__center_width = val
            self.size = (self.left_width + self.center_width +
                    self.right_width, self.height)

    @parole.Property
    def right_width():
        def fget(self):
            return self.__right_width
        def fset(self, val):
            self.__right_width = val
            self.size = (self.left_width + self.center_width +
                    self.right_width, self.height)

    def update(self, parent=None):
        super(VerticalBevel, self).update()
        self.image.subsurface(Rect((0,0), (self.left_width,
            self.height))).fill(self.left_rgb)
        self.image.subsurface(Rect((self.left_width,0), (self.center_width,
            self.height))).fill(self.center_rgb)
        self.image.subsurface(Rect((self.left_width+self.center_width,0),
            (self.right_width, self.height))).fill(self.right_rgb)

#==============================================================================

class HorizontalBevel(Pass):
    def __init__(self, top_rgb, center_rgb, bottom_rgb, top_height,
            center_height, bottom_height, alpha=None):
        s = (0, top_height + center_height + bottom_height)
        Pass.__init__(self, 'HorizontalBevel', size=s, alpha=alpha)
        self.__top_height, self.__bottom_height, self.__center_height = 0,0,0
        self.top_rgb, self.center_rgb, self.bottom_rgb = top_rgb, center_rgb, bottom_rgb
        self.top_height, self.center_height, self.bottom_height = top_height, center_height, bottom_height

    @parole.Property
    def top_rgb():
        def fget(self):
            return self.__top_rgb
        def fset(self, val):
            self.__top_rgb = val
            self.touch()

    @parole.Property
    def center_rgb():
        def fget(self):
            return self.__center_rgb
        def fset(self, val):
            self.__center_rgb = val
            self.touch()

    @parole.Property
    def bottom_rgb():
        def fget(self):
            return self.__bottom_rgb
        def fset(self, val):
            self.__bottom_rgb = val
            self.touch()

    @parole.Property
    def top_height():
        def fget(self):
            return self.__top_height
        def fset(self, val):
            self.__top_height = val
            self.size = (self.width, self.top_height + self.center_height +
                    self.bottom_height)

    @parole.Property
    def center_height():
        def fget(self):
            return self.__center_height
        def fset(self, val):
            self.__center_height = val
            self.size = (self.width, self.top_height + self.center_height +
                    self.bottom_height)

    @parole.Property
    def bottom_height():
        def fget(self):
            return self.__bottom_height
        def fset(self, val):
            self.__bottom_height = val
            self.size = (self.width, self.top_height + self.center_height +
                    self.bottom_height)

    def update(self, parent=None):
        super(HorizontalBevel, self).update()

        self.image.subsurface(Rect((0,0), (self.width,
            self.top_height))).fill(self.top_rgb)
        self.image.subsurface(Rect((0,self.top_height), (self.width,
            self.center_height))).fill(self.center_rgb)
        self.image.subsurface(Rect((0,self.top_height+self.center_height),
            (self.width, self.bottom_height))).fill(self.bottom_rgb)

#==============================================================================

class TextLine(Pass):
    # TODO: support color/font/etc markup in pattern via TextBlockPass

    def __init__(self, font, pattern, fg_rgb, bg_rgb=None,
            orientation='horizontal', size=None):
        if orientation not in ('horizontal', 'vertical'):
            raise ValueError('orientation must be one of "horizontal" or ' + \
                '"vertical"')
        Pass.__init__(self, 'AsciiLine')
        self.pattern = pattern
        self.font = font
        self.orientation = orientation
        self.fg_rgb = fg_rgb
        self.bg_rgb = bg_rgb
        self.textblock = TextBlockPass(font, fg_rgb, bg_rgb, wrap='no')

    def update(self, parent=None):
        if (not self.dirty) or (not len(self.pattern)):
            return

        self.textblock.text = self.pattern
        self.textblock.update()

        if self.orientation == 'horizontal':
            self.size = (self.width, self.textblock.height)
            renderPattern = self.pattern * (self.width / \
                    self.textblock.width)
            #renderPos = ((self.width - self.font.size(renderPattern)[0]) / 2, 0)
        elif self.orientation == 'vertical':
            self.size = (self.textblock.width, self.height)
            renderPattern = self.pattern * (self.height / \
                    self.textblock.height)
            #renderPos = (0, (self.height - self.font.get_linesize()) / 2)

        self.textblock.text = renderPattern.strip()
        self.textblock.update()

        super(TextLine, self).update()

        self.image.blit(self.textblock.image, (0,0))

#==============================================================================

class Line(Pass):
    """
    A line of pixels at any angle, rendered by the Bresenham method.
    """
    def __init__(self, startPos, endPos, rgb, thickness=1, alpha=None):
        size = (max(abs(startPos[0]-endPos[0]), thickness), 
                max(abs(startPos[1]-endPos[1]), thickness))
        topleft = (min(startPos[0], endPos[0]), min(startPos[1], endPos[1]))
        self.defaultPos = topleft
        #parole.info('line default pos: %s', topleft)
        super(Line, self).__init__("Line", size=size, alpha=alpha)
        self.rgb = rgb
        self.thickness = thickness
        if thickness < 1:
            raise ValueError("Line thickness must be at least 1, got %s." % \
                    thickness)
        try:
            #slope = (endPos[0] - startPos[0]) / (endPos[1] - startPos[1])
            slope = float(endPos[1] - startPos[1]) / (endPos[0] - startPos[0])
        except ZeroDivisionError:
            #parole.info('line vertical')
            self.negSlope = True
        else:
            #parole.info('line slope: %s', slope)
            self.negSlope = slope >= 0.0 # backwards because y is inverted

    def update(self, parent=None):
        super(Line, self).update(parent=parent)
        r = pygame.draw.line(self.image, self.rgb, 
                self.negSlope and (0,0) or (0, self.size[1]-1),
                self.negSlope and (self.size[0]-1, self.size[1]-1) or \
                        (self.size[1]-1, 0),
                self.thickness)
        #parole.info('Line rect: %s, neg slope = %s', r, self.negSlope)
