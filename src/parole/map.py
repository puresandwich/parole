#Python Advanced Roguelike Engine (Parole)
#Copyright (C) 2007, 2008 Max Bane
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
TODO: Map library docs.
"""

import parole, shader, resource, pygame
from pygame import Rect
from colornames import colors
import gc, random, math
import fov, perlin
from Numeric import array
from shader import clampRGB

#==============================================================================

def __onConfigChange(conf):
    """
    Applies any changes to the engine configuration that are relevant to the
    Map module (any configuration property under conf.map).
    """
    AsciiTile.antialias = bool(conf.map.antialias)
    AsciiTile.font = resource.getFont(conf.map.font,
                                      conf.map.fontSize)
    AsciiTile.makeSquare = bool(conf.map.makeSquare)
    parole.info('Ascii map font: %s', conf.map.font)
    parole.info('Ascii map font size: %s', conf.map.fontSize)
    parole.info('Ascii map antialiasing: %s', conf.map.antialias)
    parole.info('Ascii map font makeSquare: %s', conf.map.makeSquare)
    if not AsciiTile.font:
        parole.error('Unable to load specified map font.')
    parole.info('Map annotation font: %s', conf.map.annotationFont)
    parole.info('Map annotation font size: %s', conf.map.annotationFontSize)
    MapFrame.defaultAnnoteFont = resource.getFont(conf.map.annotationFont, 
            conf.map.annotationFontSize)
    if not MapFrame.defaultAnnoteFont:
        parole.error('Unable to load specified map annotation font.')
    parole.info('Map default annotation line RGB: %s',
            conf.map.annotationLineRGB)
    MapFrame.defaultAnnoteLineRGB = tuple(conf.map.annotationLineRGB)
    parole.info('Map default reticle RGB: %s',
            conf.map.annotationReticleRGB)
    MapFrame.defaultAnnoteReticleRGB = tuple(conf.map.annotationReticleRGB)

def init():
    """
    Initializes the map module. Automatically called during engine 
    startup - user code shouldn't need to use this function.
    """
    parole.conf.notify(__onConfigChange, True)
    
def unload():
    """
    Unloads the map modules during engine shutdown.
    """
    parole.conf.notify(__onConfigChange, False)

#==============================================================================

class MapFrame(shader.Frame):
    """
    A Frame for displaying a view of a Map2D. Provides a scrollable grid of
    shaders for displaying the tiles of the map. The tile size must be known
    in advance, when the MapFrame is created, and must agree with the actual
    size of the shaders offered by the tiles of the map.
    """

    defaultAnnoteLineRGB = (255, 255, 0)
    defaultAnnoteReticleRGB = (255, 255, 0)
    defaultAnnoteFont = None

    def __init__(self, size, tileSize=None, map=None, borders=(None,)*8,
            name=None):
        """
        Creates a new, empty MapFrame. Use the setMap() method to then display
        a map in this Frame.
        """
        super(MapFrame, self).__init__(borders, size=size, name=name)
        # private attributes
        self.__grid = None
        self.__map = None
        self.__tileSize = tileSize or AsciiTile.characterSize()
        self.__scroll = None
        self.__lastScrollOffset = None
        self.__fovObj = None
        self.__fovRad = None
        self.__dirtyFovQuads = None
        self.__visibleTiles = set()
        self.__rememberSeenTiles = False
        self.__annotationsAt = {} # Tile -> (Annotation, Rect)

        # public attributes
        self.selectedTile = None
        self.reticle = ReticleOverlayShader(self.__tileSize)

        if map:
            self.setMap(map)

    @parole.Property
    def tileSize():
        """
        The expected size in pixels of the Tile shaders of the Map2D instance
        displayed in this MapFrame. Setting this automatically invokes
        resetGrid().
        """
        def fget(self):
            return self.__tileSize
        def fset(self, val):
            self.__tileSize = val
            self.resetGrid()

    def setMap(self, map):
        """
        Set the Map2D instance to be displayed in this MapFrame. Automatically
        invokes self.resetGrid(), dirtying the Frame so that it is ready to be
        rendered on the next update. Pass None to stop displaying anything.
        """
        if self.__map and self.__grid:
            for tile in self.__map:
                self.__grid.remPass(tile)
                self.__grid[tile.col, tile.row] = None

        self.__map = map
        self.__fovObj = None
        self.__fovRad = None
        self.__dirtyFovQuads = None
        self.resetGrid()

    def getMap(self):
        """
        Returns the Map2D instance that this MapFrame is currently displaying a
        view of, or None if no map has been set.
        """
        return self.__map

    def resetGrid(self):
        """
        Rebuilds the shader grid used to display the currently set Map2D
        instance. This is done automatically when setting the map, and should
        only need to be called manually if you've somehow modified what the
        MapFrame is rendering, and you want to reset it. Has no effect if the
        current map is not set.
        """
        if self.__scroll in self.passes:
            if self.__grid:
                self.__scroll.remPass(self.__grid)
            self.remPass(self.__scroll)

        if not self.__map:
            return

        self.__grid = shader.ShaderGrid((self.__map.cols, self.__map.rows),
                self.tileSize)
        self.__scroll = shader.ScrollView(self.size)
        self.__lastScrollOffset = None
        
        for x in range(self.__map.cols):
            for y in range(self.__map.rows):
                tile = self.__map[x,y]
                tile.size = self.tileSize
                tile.touch()
                self.__grid[x,y] = tile

        self.__scroll.addPass(self.__grid, pos=(0,0))
        self.addPass(self.__scroll, pos=(0,0))
        self.__annotationsAt = {}

    def scrollPixels(self, dx, dy):
        """
        Translates the view of the map by the given displacement in pixels.
        """
        if self.__scroll:
            self.__scroll.scrollPixels(dx, dy)

    def scrollTiles(self, dx, dy):
        """
        Translates the view of the map by the given displacement in tiles.
        """
        if self.__scroll:
            self.__scroll.scrollPixels(dx*self.__tileSize[0],
                                     dy*self.__tileSize[1])

    def pixelPosToTile(self, posOrX, y=None):
        """
        Returns the (col, row) location of the tile containing the map pixel
        at the given position. Does no bounds checking to ensure that the
        given point is actually within the bounds of the map.
        """
        x, y = type(posOrX) is tuple and posOrX or (x,y)
        return x / self.__tileSize[0], y / self.__tileSize[1]

    def tilePosToPixel(self, posOrCol, row=None):
        """
        Returns the map pixel corresponding to the upper left corner of the
        tile at the given location.
        """
        col, row = type(posOrCol) is tuple and posOrCol or (posOrCol, row)
        tw, th = self.tileSize
        return tw*col, th*row

    def setViewOriginToTile(self, posOrCol, row=None):
        """
        Set the upper left corner of the view to be the upper left corner of
        the given tile location.
        """
        col, row = type(posOrCol) is tuple and posOrCol or (posOrCol, row)
        self.__scroll.offset = self.tilePosToPixel(col,row)

    def centerAtTile(self, posOrCol, row=None):
        """
        Center the view at the given tile position.
        """
        col, row = type(posOrCol) is tuple and posOrCol or (posOrCol, row)
        cx, cy = self.tilePosToPixel(col, row)
        tw, th = self.tileSize
        cx, cy = cx + tw/2, cy + th/2
        self.__scroll.offset = (cx-self.width/2, cy-self.height/2)

    def viewRectPixels(self):
        """
        Returns the rectangle of map pixels currently contained in the Frame's
        view. 
        """
        return self.__scroll.visibleRect()

    def viewRectTiles(self):
        """
        Returns the (ceiling of the) rectangle of map tiles currently
        contained in the Frame's view.  
        TODO
        """
        pass

    def bindVisibilityToFOV(self, obj, radius, remember=True):
        """
        Causes the L{MapFrame} to only display L{Tile}s of the map that are within
        the field of view of the given L{MapObject}, which must be located
        somewhere in the currently displayed map.

        @param obj The L{MapObject} to whose field of view to bind the
        display.
        @param radius The radius to use in calculating the object's field of view.
        @param remember Whether to continue displaying tiles that were at one
        time in C{obj}'s field of view but are no longer. TODO: a way to
        display remembered tiles differently than currently visible ones.
        """
        self.__map.unmonitorNearby(self.__fovObj)

        self.__fovObj = obj
        self.__fovRad = radius
        self.__dirtyFovQuads = set()
        self.__visibleTiles.clear()
        self.__rememberSeenTiles = remember
        if obj:
            self.__disableAll()
            self.__map.monitorNearby(obj, radius, self.__touchQuadrant,
                    self.__blocksLOS)
            self.__touchQuadrant(obj, obj, obj.pos)

    def __disableAll(self):
        for x in xrange(self.__map.cols):
            for y in xrange(self.__map.rows):
                self.__grid.disable(x, y)

    def __blocksLOS(self, obj):
        #parole.debug('checking if blocks los')
        return obj.blocksLOS or obj is self.__fovObj

    def __touchQuadrant(self, monObj, obj, pos):
        assert(monObj is self.__fovObj)
        if monObj is obj:
            # the fov object has moved
            self.__dirtyFovQuads = set(['ne', 'se', 'sw', 'nw'])
        else:
            self.__dirtyFovQuads.add(self.__map.quadrant(pos, monObj.pos))

        #parole.debug('MapFrame.__touchQuadrant: dirty quads = %s',
        #        self.__dirtyFovQuads)

    def update(self, *args, **kwargs):
        if self.__dirtyFovQuads:
            t = parole.time()
            self.__updateFOV()
            parole.debug('update fov time = %sms', parole.time()-t)
        if self.__scroll and self.__annotationsAt and \
                self.__scroll.offset != self.__lastScrollOffset:
            self.__updateAnnotations()
        if self.__scroll:
            self.__lastScrollOffset = self.__scroll.offset
        super(MapFrame, self).update(*args, **kwargs)

    def __updateFOV(self):
        #parole.debug('dirty fov quads: %s', self.__dirtyFovQuads)
        newVisibleTiles = set()
        def fovVisit(x, y):
            if (x,y) not in self.__visibleTiles:
                if self.__rememberSeenTiles:
                    self.__grid[x,y] = self.__map[x,y]
                else:
                    self.__grid.enable(x, y)
            newVisibleTiles.add((x,y))

        self.__map.fieldOfView(self.__fovObj.pos, self.__fovRad, fovVisit,
                quadrants=self.__dirtyFovQuads)

        for (x,y) in self.__visibleTiles - newVisibleTiles:
            if self.__rememberSeenTiles:
                self.__grid[x,y] = self.__map[x,y].frozenShader()
            else:
                self.__grid.disable(x, y)

        self.__visibleTiles = newVisibleTiles
        self.__dirtyFovQuads.clear()

    def selectTile(self, posOrX, y=None):
        parole.debug('select: %s,%s', posOrX, y)
        if self.selectedTile:
            self.selectedTile.removeOverlay(self.reticle)
        if posOrX is not None:
            self.selectedTile = self.__map[type(posOrX) is tuple and posOrX\
                    or (posOrX,y)]
            self.selectedTile.addOverlay(self.reticle)
        else:
            self.selectedTile = None
        parole.debug('selectedTile = %s', self.selectedTile)

    def annotate(self, tile, shaderOrText, ann=None, lineRGB=None,
            reticleRGB=None, textFont=None, textWidth=150):
        # tile may be a Tile instance or a coordinate tuple -- figure which
        # Tile we're referring to
        if type(tile) is tuple and len(tile)==2:
            tile = self.getMap()[tile]
        if not isinstance(tile, Tile) or tile not in self.getMap():
            raise TypeError('tile must be a Tile instance in my Map2D')

        # Generally, shaderOrText can be any Shader, but for convenience, if
        # it is a string, we create a TextBlock containing that string in a
        # default font.
        if isinstance(shaderOrText, parole.shader.Shader):
            sdr = shaderOrText
        elif type(shaderOrText) is str:
            sdr = shader.TextBlockPass(textFont or self.defaultAnnoteFont,
                    (255,255,255), text=shaderOrText, wrap='word',
                    wrap_width=textWidth)
            sdr.update()
        else:
            raise TypeError('shaderOrText must be a Shader instance or '
                            'a string.')

        # Create the Annotation object, which will track information about how
        # we're displaying this annotation
        ann = ann or Annotation(tile, sdr, lineRGB or
                self.defaultAnnoteLineRGB, reticleRGB or
                self.defaultAnnoteReticleRGB)

        # Prepare the annotations list for this tile if necessary
        if tile not in self.__annotationsAt:
            self.__annotationsAt[tile] = []

        # Now figure out where to display the annotation...
        visibleRect = self.__scroll.visibleRect()
        tileRect = self.__grid.rectOf((tile.col, tile.row))
        if visibleRect.contains(tileRect):
            # tile is on screen; find a free cardinal direction around the
            # tile to place the annotation at
            for rect in self.__annoteRects(tile, sdr.size):
                rectFree = True
                for annote in self.__annotationsAt[tile]:
                    annoteRect = Rect(self.positionOf[annote],
                            annote.size)
                    if rect.colliderect(annoteRect):
                        rectFree = False
                        break
                if rectFree and visibleRect.contains(rect):
                    self.__placeAnnotation(tile, ann, rect)
                    ann.prefRect = rect
                    parole.debug('ann: %r', ann)
                    return ann
            #raise "Too many annotations on %r" % tile

        # tile is off screen, or no free cardinal direction was on screen.
        # TODO: if it's the latter, make sure we don't place the annote on top
        # of an existing one
        rect = Rect((0,0), ann.size)
        rect.center = tileRect.center
        bufferRect = Rect(rect)
        bufferRect.size = (rect.w + 2*tileRect.w, rect.h + 2*tileRect.h)
        bufferRect.center = rect.center
        bufferRect.clamp_ip(visibleRect)
        rect.center = bufferRect.center
        self.__placeAnnotation(tile, ann, rect)
        ann.prefRect = rect
        parole.debug('ann: %r', ann)
        return ann

    def removeAnnotation(self, annotation):
        # stop drawing it
        self.__annotationsAt[annotation.tile].remove(annotation)
        if not self.__annotationsAt[annotation.tile]:
            del self.__annotationsAt[annotation.tile]
        self.remPass(annotation)
        if annotation.line and annotation.line in self.passes:
            self.remPass(annotation.line)
        if annotation.reticle and annotation.reticle in \
                annotation.tile.overlays:
            annotation.tile.removeOverlay(annotation.reticle)

    def __placeAnnotation(self, tile, ann, rect):
        # Prepare the annotations list for this tile if necessary
        if tile not in self.__annotationsAt:
            self.__annotationsAt[tile] = []

        # Since we add the annotation to our own passes (rather than to the
        # scroll or grid), we need to account for the scroll offset
        ox, oy = self.__scroll.offset
        annRect = rect.move(-ox, -oy)

        # place the annotation
        self.addPass(ann, pos=annRect.topleft)
        self.__annotationsAt[tile].append(ann)

        # add a reticle to the tile
        reticle = ReticleOverlayShader(tile.size, rgb=ann.reticleRGB)
        tile.addOverlay(reticle)
        ann.reticle = reticle

        # and a line linking the annotation to the tile 
        tileRect = self.__grid.rectOf((tile.col, tile.row)).move(-ox, -oy)
        # annote above tile
        if annRect.bottom < tileRect.top:
            lineTileY = tileRect.top
            lineAnnY = annRect.bottom
            linePosY = annRect.bottom
        # annote below tile
        elif annRect.top > tileRect.bottom:
            lineTileY = tileRect.bottom
            lineAnnY = annRect.top
            linePosY = tileRect.bottom
        else:
            lineTileY = tileRect.centery
            lineAnnY = annRect.centery
            linePosY = annRect.centery

        # annote left of tile
        if annRect.right < tileRect.left:
            lineTileX = tileRect.left
            lineAnnX = annRect.right
            linePosX = annRect.right
        # annote right of tile
        elif annRect.left > tileRect.right:
            lineTileX = tileRect.right
            lineAnnX = annRect.left
            linePosX = tileRect.right
        else:
            lineTileX = tileRect.centerx
            lineAnnX = annRect.centerx
            linePosX = annRect.centerx

        #if not (lineAnnY == annRect.centery and lineAnnX == annRect.centerx):
        line = parole.shader.Line((lineAnnX, lineAnnY), (lineTileX, lineTileY),
                ann.lineRGB)

        #line = parole.shader.Line(annRect.center, tileRect.center,
        #        self.annoteLineRGB)
        ann.line = line
        self.addPass(line, line.defaultPos)
        #parole.info('line size: %s', line.size)
        #else:
        #    ann.line = None

    def __updateAnnotations(self):
        parole.debug('annotations: %r', self.__annotationsAt)
        visibleRect = self.__scroll.visibleRect()
        for tile, anns in self.__annotationsAt.iteritems():
            for ann in anns:
                self.removeAnnotation(ann)
                if visibleRect.contains(ann.prefRect):
                    self.__placeAnnotation(tile, ann, ann.prefRect)
                else:
                    self.annotate(tile, ann.shader, ann)

    def __annoteRects(self, tile, shaderSize):
        dist = 10.0
        diagComp = int(math.sqrt((dist**2)/2))
        dist = int(dist)
        tileRect = self.__grid.rectOf((tile.col, tile.row))
        annoteRect = Rect((0,0), shaderSize)

        annoteRect.bottomright = tileRect.topleft
        yield annoteRect.move(-diagComp, -diagComp)

        annoteRect.midbottom = tileRect.midtop
        yield annoteRect.move(0, -diagComp)

        annoteRect.bottomleft = tileRect.topright
        yield annoteRect.move(diagComp, -diagComp)

        annoteRect.midleft = tileRect.midright
        yield annoteRect.move(diagComp, 0)

        annoteRect.topleft = tileRect.bottomright
        yield annoteRect.move(diagComp, diagComp)

        annoteRect.midtop = tileRect.midbottom
        yield annoteRect.move(0, diagComp)

        annoteRect.topright = tileRect.bottomleft
        yield annoteRect.move(-diagComp, diagComp)

        annoteRect.midright = tileRect.midleft
        yield annoteRect.move(-diagComp, 0)

#==============================================================================

class Annotation(shader.Shader):
    """
    An Annotation is a message (or any kind of) window/shader linked to a
    particular Tile of a Map that can be displayed in an associated MapFrame.
    """

    def __init__(self, tile, shader, lineRGB=(255,255,255),
            reticleRGB=(255,255,255)):
        super(Annotation, self).__init__('Annotation', shader.size)
        self.prefRect = None
        self.line = None
        self.tile = tile
        self.shader = shader
        self.reticle = None
        self.lineRGB = lineRGB
        self.reticleRGB = reticleRGB
        self.addPass(shader)

    def __repr__(self):
        return "Annotation(%r, %r, prefRect=%r, line=%r)" % (self.tile, self.shader,
                self.prefRect, self.line)

#==============================================================================

class MapObject(object):
    """
    Creates a new MapObject, of which anything in a map Tile must be a 
    subclass.
    
    @type    layer: number
    @param   layer: Determines either the order in which the objects in a tile
                    should be drawn, or determines which object in a tile gets
                    drawn alone (e.g., the one with the highest layer),
                    depending on the Map's options.
    @type shader: parole.shader.Shader
    @param shader: The shader to use for drawing this object on the map. All
                   MapObjects on the same Map must have the same sized shaders.
    @type blocksLOS: bool
    @param blocksLOS: Whether this object blocks line of sight through the
    tile containing it.
                 
    """
    
    layer = 0
    shader = None
    
    def __init__(self, layer, shader, blocksLOS=False, blocksMove=False):
        self._layer = layer
        self._shader = shader
        self.pos = None
        self.parentTile = None
        self.blocksLOS = blocksLOS
        self.blocksMove = blocksMove
        
    def __repr__(self):
        return "MapObject(%s, %s)" % (self.layer, self.shader)
        
    @parole.Property
    def layer():
        def fget(self):
            return self._layer
        
        def fset(self, val):
            # Ensure that the parent tile updates itself with
            # our new layer. Stupidly inefficient method #1.
            parent = self.parentTile
            if parent:
                parent.remove(self)
            self._layer = val
            if parent:
                parent.add(self)
        
    @parole.Property
    def shader():
        def fget(self):
            return self._shader
        
        def fset(self, val):
            # Ensure that the parent tile updates itself with
            # our new shader. Stupidly inefficient method #1.
            parent = self.parentTile
            if parent:
                parent.remove(self)
            self._shader = val
            if parent:
                parent.add(self)

    def applyLight(self, availLight):
        self.shader.applyLight(availLight)
            
#==============================================================================

class Tile(shader.Shader):
    """
    TODO: rewrite this doc - we're no longer a set.
    A C{Tile} is simultaneously a C{set} of C{MapObject}s located at the same
    position in some C{Map2D}, and a C{Shader} that implements some method of
    displaying the map position, given what objects are located there. The
    default method provided by the C{Tile} class is to display the C{shader}
    attribute of the C{MapObject} with the highest layer, and possibly, if the
    highest C{MapObject} does not have a C{bgShader} attribute, the
    C{bgShader} attribute of the highest-layer object that does have one.

    A C{Tile} also has a user readable/writable C{luminosities} attribute,
    which is a list of C{Luminosity} objects that should be applied to the
    display of the C{Tile} when its C{applyLuminosities} method is called.
    """
    
    def __init__(self, map, (col, row), contents=None):
        """
        Creates a C{Tile} to track the contents and display of position C{(col,
        row)} in some C{Map2D}. If C{contents} is given, it should be a sequence
        of C{MapObject}s that the C{Tile} will begin populated by.

        The user should not normally have to worry about creating new C{Tile}
        instances; the C{Tile}s of a C{Map2D} are all created by the
        C{Map2D}'s constructor.
        """
        self.contents = set()
        self.map = map
        self.row, self.col = row, col
        shader.Shader.__init__(self, "Tile")   
        self._highestObject = None
        self.last_highestObject = None
        self.overlays = {}
        
        if contents is not None:
            for obj in contents:
                self.add(obj)

        self.availLight = (0,0,0)
        self.__frozenShader = None
                
#    def __hash__(self):
#        """
#        C{Tile} objects hash as C{Shader}s (not as C{set}s).
#        """
#        # We need to hash as a shader, not as a set
#        return shader.Shader.__hash__(self)
        
    def __str__(self):
        """
        Returns a human-readable string representation of the C{Tile},
        indicating its position and contents.
        """
        return 'Tile (%s,%s) {%s}' % (self.col, self.row, 
            ', '.join([obj is self.highestObject and '*'+str(obj) or str(obj)\
                    for obj in self]))
        
    def __repr__(self):
        """
        Returns a programmer-readable string representation of the C{Tile}.
        """
        return 'Tile((%r,%r, contents=%r)' % (self.col, self.row, 
                                              [repr(obj) for obj in self])

    def __getstate__(self):
        # Returns the state of an instance for pickling
        state = super(Tile, self).__getstate__()
        state['overlays'] = {}
        #del state['map']
        #parole.debug('Tile.__getstate__: %r', state)
        return state

    def __setstate__(self, state):
        super(Tile, self).__setstate__(state)
        self.__resetPasses()

    def __iter__(self):
        for obj in self.contents:
            yield obj

    def __contains__(self, obj):
        return obj in self.contents

    #@parole.Property
    def getHighestLayer(self):
        """
        Returns the layer of the highest-layer C{MapObject} contained by this
        C{Tile}, or C{None} if the C{Tile} is empty.
        """
        try:
            return self._highestObject.layer
        except AttributeError:
            return None
        
    #@parole.Property
    def getHighestShader(self):
        """
        Returns the C{shader} attribute of the highest-layer C{MapObject}
        contained by this C{Tile}, or C{None} if the C{Tile} is empty.
        """
        try:
            return self._highestObject.shader
        except AttributeError:
            return None
        
    @parole.Property
    def highestObject():
        """
        A C{Property} attribute that references the highest-layer C{MapObject}
        contained by this C{Tile}. Setting this C{Property} causes the C{Tile}
        to recompute how it is displayed. The set value must be a C{MapObject}
        contained by the C{Tile}.
        """
        def fget(self):
            return self._highestObject
        
        def fset(self, val):
            if val and val not in self:
                raise ValueError('val must be contained in this Tile!')

            #self.last_highestObject = self._highestObject
            #try:
            #    #self.remPass(self._highestObject.shader)
            #    self.clearPasses()
            #except AttributeError:
            #    pass
            
            self._highestObject = val
            self.__resetPasses()

    def __resetPasses(self):
        self.clearPasses()

        # FIXME: kind of hacky. if this object doesn't have a background
        # color, find the next highest one that does, and add a colorfield
        # with that color, so that backgrounds show through higher objects
        # with no backgrounds
        if hasattr(self._highestObject, 'shader') and not \
                self._highestObject.shader.bg_rgb:

            highestBgRGB = None
            highestLayer = None
            highestBgObj = None
            for obj in self:
                if hasattr(obj, 'shader') and obj.shader.bg_rgb\
                        and obj.layer > highestLayer:
                    highestBgRGB = obj.shader.bg_rgb
                    highestLayer = obj.layer
                    highestBgObj = obj
            if highestBgRGB:
                self.addPass(highestBgObj.shader.bgShader)

        # add the top object's shader to our passes
        try:
            self.addPass(self._highestObject.shader)
        except AttributeError:
            pass

        # overlays
        for overlay, pos in self.overlays.iteritems():
            self.addPass(overlay, pos=pos)

        
    def add(self, obj):
        """
        Adds a C{MapObject} to this C{Tile}.
        """
        if not isinstance(obj, MapObject):
            raise TypeError, "Only a MapObject may be added to a Tile."
        
        #super(Tile, self).add(obj)
        self.contents.add(obj)
        obj.parentTile = self
        obj.pos = (self.col, self.row)

        self.applyLight(obj)
        
        if obj.layer > self.getHighestLayer():
            self.highestObject = obj

        self.map.onAdd(self, obj)
        #parole.debug('Added %r to %s', obj, self)
        return self
        
    def remove(self, obj):
        """
        Removes a C{MapObject} from this C{Tile}.
        """
        self.map.onRemove(self, obj)

        #super(Tile, self).remove(obj)
        self.contents.remove(obj)
        obj.pos = None
        # recompute highest layer/object
        highestObject = None
        self.highestObject = None
        for x in self:
            if x.layer > self.getHighestLayer():
                highestObject = x
        self.highestObject = highestObject

        #parole.debug('Removed %r from %s', obj, self)
        return self

    def clear(self):
        """
        Clears the contents of this C{Tile}.
        """
        for obj in list(self.contents):
            self.remove(obj)
        
    def update(self, parent=None):
        """
        Implements C{Shader.update}. For C{set.update}, use C{Tile.updateSet}.
        """
        # avoids name conflict with set.update
        if self.dirty:
            shader.Shader.update(self, parent=parent)
            self.__frozenShader = None

    def updateContents(self, otherSet):
        """
        Updates the contents of the C{Tile} to be the union of its contents with
        those of another C{set}.
        """
        #set.update(self, otherSet)
        self.contents.update(otherSet)

    def hasLOSBlocker(self):
        """
        Returns C{True} iff the tile contains a L{MapObject} whose
        C{blocksLOS} attribute is C{True}.
        """
        for obj in self:
            if self.blocksLOS:
                return True
        return False

    def hasMoveBlocker(self):
        """
        Returns C{True} iff the tile contains a L{MapObject} whose
        C{blocksMove} attribute is C{True}.
        """
        for obj in self:
            if self.blocksMove:
                return True
        return False

    def addLight(self, (r,g,b), intensity):
        aR, aG, aB = self.availLight
        self.availLight = (aR + int(intensity*r), 
                           aG + int(intensity*g),
                           aB + int(intensity*b))
        self.map.tilesWithDirtyLight.add(self)

    def removeLight(self, rgb, intensity):
        """
        Equivalend to C{Tile.addLight(rgb, -intensity)}.
        """
        self.addLight(rgb, -intensity)

    def clearLight(self):
        """
        Remove all available light at this L{Tile}.
        """
        self.availLight = (0,0,0)
        self.map.tilesWithDirtyLight.add(self)

    def applyLight(self, obj=None):
        availRGB = shader.clampRGB(self.availLight)
        for o in obj and [obj] or self:
            o.applyLight(availRGB)

    def frozenShader(self):
        if self.__frozenShader:
            return self.__frozenShader
        self.__frozenShader = shader.SurfacePass(self.image)
        return self.__frozenShader

    def addOverlay(self, sdr, pos=None):
        self.overlays[sdr] = pos
        self.addPass(sdr, pos=pos)

    def removeOverlay(self, sdr):
        del self.overlays[sdr]
        self.remPass(sdr)

    def clearOverlays(self):
        self.remPass(self.overlays)
        self.overlays.clear()
        
#==============================================================================

class Map2D(object):
    def __init__(self, name, (cols, rows)):
        self.name = name
        self.rows, self.cols = rows, cols
        
        self.tiles = array([array([Tile(self, (col,row)) for \
                col in range(cols)]) for row in range(rows)])
            
        self.ambientRGB = (0,0,0)
        self.ambientIntensity = 0
        self.distMonObjs = {}
        self.dirtyDistMonObjs = {}
        self.tilesWithDirtyLight = set() # Tiles add themselves to this
        
    def __str__(self):
        return 'Map2D "%s" %sx%s' % \
            (self.name, self.cols, self.rows)
    
    def __repr__(self):
        return 'Map2D(%r, (%r,%r))' % (self.name, self.cols, self.rows) 

    #def __getstate__(self):
    #    state = self.__dict__.copy()
    #    #parole.debug('Map2D.__getstate__: %r' , sc)
    #    return state

    def __getitem__(self, (x,y)):
        return self.tiles[y][x]

    def iterTiles(self):
        for x in xrange(self.cols):
            for y in xrange(self.rows):
                yield self[x,y]

    def __iter__(self):
        return self.iterTiles()

    def __contains__(self, tile):
        for t in self:
            if t is tile:
                return True
        return False

    def rect(self):
        return pygame.Rect(0, 0, self.cols, self.rows)

    def dist(self, (x0,y0), (x1,y1)):
        """
        Returns the Euclidean distance between two points.
        """
        return math.sqrt(float((x1-x0)**2 + (y1-y0)**2))

    def quadrant(self, (x0,y0), (x1,y1)):
        """
        Returns which quadrant (one of C{'ne', 'se, 'sw', 'nw'}) the point
        C{(x0,y0)} is in relative to C{(x1,y1)}.
        """
        return (y0 <= y1 and 'n' or 's') + (x0 >= x1 and 'e' or 'w')

    def getRow(self, y):
        return self.tiles[y]
        
    def tileAt(self, (x,y)):
        return self.tiles[y][x]
    
    def add(self, (x,y), *objs):
        tile = self[x,y]
        for obj in objs:
            tile.add(obj)
        return tile

    def onAdd(self, tile, obj):
        for (monObj, (dist, callback, condition)) in \
                self.distMonObjs.iteritems():
            #parole.debug('add: checking %s nearby %s', obj, monObj)
            if condition(obj) and self.dist(obj.pos, monObj.pos) <= dist:
                self.dirtyDistMonObjs[monObj].add((obj, obj.pos))
    
    def remove(self, (x,y), *objs):
        tile = self[x,y]
        for obj in objs:
            tile.remove(obj)    
        return tile

    def onRemove(self, tile, obj):
        for (monObj, (dist, callback, condition)) in \
                self.distMonObjs.iteritems():
            #parole.debug('add: checking %s nearby %s', obj, monObj)
            if condition(obj) and self.dist(obj.pos, monObj.pos) <= dist:
                self.dirtyDistMonObjs[monObj].add((obj, obj.pos))
    
    def applyGenerator(self, generator, rect=None):
        """
        Applies a map generator to the given region of this map, or to the
        whole thing if unspecified.
        """
        generator.apply(self, rect)

    def setAmbientLight(self, rgb, intensity):
        for x in range(self.cols):
            for y in range(self.rows):
                t = self[x,y]
                t.removeLight(self.ambientRGB, self.ambientIntensity)
                t.addLight(rgb, intensity)
                #t.applyLight()
        self.ambientRGB, self.ambientIntensity = rgb, intensity

    def fieldOfView(self, pos, radius, visitFunc, isBlocked=None,
            quadrants=None):
        time = parole.time()
        def defaultIsBlocked(x, y):
            return bool([o for o in self[x,y] if o.blocksLOS])

        fov.fieldOfView(pos[0], pos[1], self.cols, self.rows, radius,
                visitFunc, isBlocked or defaultIsBlocked, quadrants=quadrants)
        #parole.debug('fieldOfView: time = %sms', parole.time() - time)

    def monitorNearby(self, obj, dist, callback, condition=None):
        if obj.parentTile not in self:
            raise ValueError('obj must be a MapObject contained by this Map.')

        self.distMonObjs[obj] = (dist, callback, condition or (lambda x: True))
        self.dirtyDistMonObjs[obj] = set()

    def unmonitorNearby(self, obj):
        if obj in self.distMonObjs:
            del self.distMonObjs[obj]
            del self.dirtyDistMonObjs[obj]

    def updateDirtyMonitors(self):
        #parole.debug('updateDirtyMonitors: %s', self.dirtyDistMonObjs)
        #parole.debug('distMonObjs: %s', self.distMonObjs)
        for monObj, objs in self.dirtyDistMonObjs.iteritems():
            if objs:
                callback = self.distMonObjs[monObj][1]
                for obj,pos in objs:
                    callback(monObj, obj, pos)
                objs.clear()

    def updateDirtyLight(self):
        for t in self.tilesWithDirtyLight:
            t.applyLight()
        self.tilesWithDirtyLight.clear()

    def update(self, updateDirtyMonitors=True, updateDirtyLight=True):
        if updateDirtyMonitors:
            self.updateDirtyMonitors()
        if updateDirtyLight:
            self.updateDirtyLight()

#==============================================================================

# TODO: Eventually move this to something equivalent in sim?
class LightSource(object):
    def __init__(self, rgb, intensity, fallOff=1.0):
        self.rgb = rgb
        self.intensity = intensity
        self.radius = 0
        self.distIntensities = {}
        self.fallOff = fallOff
        self.minIntensity = 0.03
        self.appliedTiles = {}
        self.calcRadius()

    def copy(self):
        return LightSource(self.rgb, self.intensity, self.fallOff)

    def calcRadius(self):
        self.radius = int(math.sqrt(self.intensity / (self.fallOff * \
            self.minIntensity)))
        #parole.debug('LightSource: intensity = %, fallOff = %s, radius = %s',
        #        self.intensity, self.fallOff, self.radius)

    def setRGB(self, rgb):
        for pos, intensity in self.appliedTiles.iteritems():
            t = map[pos]
            t.removeLight(self.rgb, intensity)
            t.addLight(rgb, intensity)
        self.rgb = rgb

    def setIntensity(self, intensity):
        self.intensity = intensity
        self.calcRadius()
        self.distIntensities = {}

    def apply(self, map, pos):
        time = parole.time()
        def visit(x, y):
            t = map[x,y]
            if pos == (x,y):
                if pos not in self.appliedTiles:
                    self.appliedTiles[pos] = 0.0
                self.appliedTiles[pos] += self.intensity
                t.addLight(self.rgb, self.intensity)
                #t.applyLight()
                return

            dist = map.dist(pos, (x,y))
            if dist not in self.distIntensities:
                intensity = self.intensity / (self.fallOff * (dist)**2)
                self.distIntensities[dist] = intensity
            intensity = self.distIntensities[dist]

            if (x,y) not in self.appliedTiles:
                self.appliedTiles[(x,y)] = 0.0
            self.appliedTiles[(x,y)] += intensity
            t.addLight(self.rgb, intensity)
            #t.applyLight()

        map.fieldOfView(pos, self.radius, visit)
        parole.debug('LightSource.apply: time = %sms', parole.time() - time)

    def remove(self, map):
        time = parole.time()
        for pos, intensity in self.appliedTiles.iteritems():
            t = map[pos]
            t.removeLight(self.rgb, intensity)
            #t.applyLight()
        self.appliedTiles = {}
        parole.debug('LightSource.remove: time = %sms', parole.time() - time)

#==============================================================================

class AsciiTile(shader.Pass):
    
    font = None
    antialias = True
    makeSquare = False
    
    @classmethod
    def characterSize(cls):
        """
        Oh God, assumes monospaced font!
        """
        fsz = cls.font.size('#')
        if cls.makeSquare:
            return (fsz[1],fsz[1])
        return fsz
    
    def __init__(self, char, rgb, bg_rgb=None, alpha=255):
        self.char = char[0]
        self.rgb = clampRGB(rgb)
        self.bg_rgb = clampRGB(bg_rgb)
        shader.Pass.__init__(self, "AsciiTile", size=AsciiTile.characterSize(),
                alpha=alpha)        
        
        self.reflRGB = self.rgb
        self.reflBgRGB = self.bg_rgb
        self.__render()
        self.bgShader = shader.ColorField(self.reflBgRGB or (0,255,255),
                self.size)
        
    def __repr__(self):
        return 'AsciiTile("%s", %s, %s, %s)' % (self.char, self.rgb,
                self.bg_rgb, self.alpha)

    def __str__(self):
        return repr(self)

    def __getstate__(self):
        # Returns instance state for pickling
        #state = self.__dict__.copy()
        state = super(shader.Pass, self).__getstate__()
        del state['bgShader']
        #parole.debug('AsciiTile.__getstate__: %s', state)
        return state

    def __setstate__(self, state):
        # Restores instance state for unpickling
        #parole.debug('__setstate__: %s', state)
        self.__dict__.update(state)
        self.bgShader = shader.ColorField(self.reflBgRGB or (0,255,255),
                self.size)
        self.__render()

    def __render(self):
        if self.reflBgRGB:
            charimage = AsciiTile.font.render(self.char[0], AsciiTile.antialias,
                                           self.reflRGB, self.reflBgRGB)
        else:
            charimage = AsciiTile.font.render(self.char[0], AsciiTile.antialias,
                                           self.reflRGB)
        if AsciiTile.makeSquare:
            sqSz = AsciiTile.characterSize()
            chSz = charimage.get_size()
            self.image = pygame.Surface(sqSz).convert_alpha()
            if self.reflBgRGB:
                self.image.fill(self.reflBgRGB)
            else:
                self.image.fill((0,0,0,0))
            self.image.blit(charimage, ((sqSz[0]-chSz[0])/2,
                (sqSz[1]-chSz[1])/2))
        else:
            self.image = charimage

        #self.size = self.image.get_size()
        
    def update(self, parent=None):
        super(AsciiTile, self).update(parent=parent)
        
        self.__render()
        self.char = self.char[0]

    def applyLight(self, availLight):
        prevReflRGB = self.reflRGB
        prevReflBgRGB = self.reflBgRGB

        def reflection(objectRGB, availRGB):
            availR, availG, availB = availRGB
            oR, oG, oB = objectRGB
            reflRGB =  (int((oR/255.0)*availR),
                        int((oG/255.0)*availG),
                        int((oB/255.0)*availB))
            #parole.debug('%s: Object rgb %s reflects %s (avail %s).' % (repr(self),
            #    repr(objectRGB), repr(reflRGB), repr((availR, availG, availB))))
            return reflRGB

        self.reflRGB = reflection(self.rgb, availLight)
        if self.bg_rgb:
            self.reflBgRGB = reflection(self.bg_rgb, availLight)
        else:
            self.reflBgRGB = None

        #if self.reflRGB != prevReflRGB or self.reflBgRGB != prevReflBgRGB:
        self.bgShader.rgb = self.reflBgRGB or (0,255,255)            
        self.touch()

#==============================================================================

class Generator(object):
    """
    Generates content for maps. Various generators can be applied one after
    another to different, possibly overlapping regions of a map. 
    """
    def __init__(self, name, clearFirst=False):
        self.name = name
        self.clearFirst = clearFirst

    def __repr__(self):
        return "Generator(%s)" % (repr(self.name),)

    def apply(self, map, rect=None):
        """
        Applies this generator to the given region of the given map, or to the
        whole thing if unspecified.
        """
        pass

#==============================================================================

class MapObjectGenerator(Generator):
    """
    A simple C{Generator} that adds the return value of a given function-like
    object to each tile in the region it is applied to.
    """
    def __init__(self, name, makeObj, clearFirst=False):
        super(MapObjectGenerator, self).__init__(name, clearFirst)
        self.makeObj = makeObj

    def __repr__(self):
        return "MapObjectGenerator(%s, %s)" % (repr(self.name), repr(self.makeObj))

    def apply(self, map, rect=None):
        rect = (rect or map.rect()).clip(map.rect())
        super(MapObjectGenerator, self).apply(map, rect)

        for x in range(rect.x, rect.x + rect.w):
            for y in range(rect.y, rect.y + rect.h):
                obj = self.makeObj()
                if obj and isinstance(obj, MapObject):
                    if self.clearFirst:
                        map[x,y].clear()
                    map[x,y].add(obj)

#==============================================================================

class MapObjectAtGenerator(Generator):
    """
    TODO
    """
    def __init__(self, name, makeObjAt, clearFirst=False):
        super(MapObjectAtGenerator, self).__init__(name, clearFirst)
        self.makeObjAt = makeObjAt

    def __repr__(self):
        return "MapObjectAtGenerator(%s, %s)" % (repr(self.name),
                repr(self.makeObjAt))

    def apply(self, map, rect=None):
        rect = (rect or map.rect()).clip(map.rect())
        super(MapObjectAtGenerator, self).apply(map, rect)

        for x in range(rect.x, rect.x + rect.w):
            for y in range(rect.y, rect.y + rect.h):
                obj = self.makeObjAt(map[x,y])
                if obj and isinstance(obj, MapObject):
                    if self.clearFirst:
                        map[x,y].clear()
                    map[x,y].add(obj)

#==============================================================================

class PerlinGenerator(Generator):

    def __init__(self, name, makeObjAt, pX, pY, pZ, clearFirst=False):
        super(PerlinGenerator, self).__init__(name, clearFirst)
        self.makeObjAt = makeObjAt
        self.pX, self.pY, self.pZ = pX, pY, pZ

    def apply(self, map, rect=None):
        rect = (rect or map.rect()).clip(map.rect())
        super(PerlinGenerator, self).apply(map, rect)

        for x in range(rect.x, rect.x + rect.w):
            for y in range(rect.y, rect.y + rect.h):
                t = map[x,y]
                pX, pY, pZ = self.pX(t, rect), self.pY(t, rect), \
                             self.pZ(t, rect)
                noise = perlin.noise(pX, pY, pZ)
                obj = self.makeObjAt(t, noise)
                if obj and isinstance(obj, MapObject):
                    if self.clearFirst:
                        map[x,y].clear()
                    map[x,y].add(obj)

#==============================================================================

class TemplateGenerator(Generator):
    # TODO: Area effects
    def __init__(self, name, template, legend, clearFirst=False, extend="clip"):
        super(TemplateGenerator, self).__init__(name, clearFirst)
        # TODO: extend = "scale", "tile"
        self.extend = extend
        if type(template) is str:
            #self.templateRows = [row for row in template.splitlines() if row]
            self.templateRows = template.splitlines()
        else:
            try:
                templateStr = template.read()
            except AttributeError:
                raise TypeError('template must be a string or a file-like'
                        ' obj.')
            #self.templateRows = [row for row in templateStr.splitlines() if row]
            self.templateRows = templateStr.splitlines()

        #rowLen = 0
        #for row in self.templateRows:
        #    if not rowLen:
        #        rowLen = len(row)
        #    elif len(row) != rowLen:
        #        raise ValueError('Template rows must all have equal length.')

        self.legend = legend

    def __repr__(self):
        return "TemplateGenerator(%s, '...', ...)" % (repr(self.name),)

    def apply(self, map, rect=None, parentRect=None):
        rect = (rect or (parentRect or map.rect())).clip(parentRect or map.rect())
        #super(TemplateGenerator, self).apply(map, rect)

        y = rect.y
        for templateRow in self.templateRows:
            #parole.debug('templateRow: %s', templateRow)
            # Assume clip
            if y >= rect.y + rect.h:
                break
            x = rect.x
            for templateChar in templateRow:
                # Assume clip
                if x >= rect.x + rect.w:
                    break
                if templateChar == ' ':
                    pass
                elif templateChar in self.legend:
                    generator = self.legend[templateChar]
                    if self.clearFirst:
                        map[x,y].clear()
                    generator.apply(map, pygame.Rect((x, y), (1, 1)))
                else:
                    parole.warn("Unknown template character %s.",
                        repr(templateChar))

                x += 1
            y += 1

    def applyTiled(self, map, rect=None, parentRect=None):
        rect = (rect or (parentRect or map.rect())).clip(parentRect or map.rect())

        tw = max([len(row) for row in self.templateRows])
        th = len(self.templateRows)

        y = rect.y
        while y <= rect.y + rect.h:
            x = rect.x
            while x <= rect.x + rect.w:
                self.apply(map, pygame.Rect((x,y), (tw,th)), parentRect=rect)
                x += tw
            y += th

#==============================================================================

class CellularAutomataGenerator(Generator):
    def __init__(self, name, seedProb, conditions, clearFirst=False,
            seedEdges=False):
        super(CellularAutomataGenerator, self).__init__(name, clearFirst)
        self.seedProb = seedProb
        self.conditions = conditions
        self.seedEdges = seedEdges

    def neighborsOf(self, row, col, seedArray):
        h = len(seedArray)
        w = len(seedArray[0])

        ul = (max(0,row-1), max(0,col-1)) 
        br = (min(h-1,row+1), min(w-1, col+1))
        neighbors = 0
        i = ul[0]
        while i <= br[0]:
            j = ul[1]
            while j <= br[1]:
                if seedArray[i][j]:
                    neighbors += 1
                j += 1
            i += 1
        return neighbors

    def apply(self, map, rect=None):
        rect = (rect or map.rect()).clip(map.rect())
        #super(CellularAutomataGenerator, self).apply(map, rect)
        seedArray = [[random.random() <= self.seedProb for j in \
            range(rect.w + 2*int(self.seedEdges))] for i in range(rect.h +\
                2*int(self.seedEdges))]

        y = rect.y
        for i in range(int(self.seedEdges), rect.h + int(self.seedEdges)):
            x = rect.x
            for j in range(int(self.seedEdges), rect.w + int(self.seedEdges)):
                numNeighbors = self.neighborsOf(i, j, seedArray)
                if numNeighbors in self.conditions:
                    gen = self.conditions[numNeighbors]
                    if gen:
                        if self.clearFirst:
                            map[x,y].clear()
                        gen.apply(map, pygame.Rect((x,y), (1,1)))
                x += 1
            y += 1

#==============================================================================

class ReticleOverlayShader(shader.Shader):
    def __init__(self, size, rgb=colors['Gold']):
        super(ReticleOverlayShader, self).__init__("ReticleOverlay", size=size)
        # left vertical bevel
        vbl = shader.VerticalBevel(rgb, rgb, rgb, 1, 0, 0)
        vbl.size = (vbl.size[0], size[1])
        self.addPass(vbl, pos=(0,0))
        # right vertical bevel
        vbr = shader.VerticalBevel(rgb, rgb, rgb, 1, 0, 0)
        vbr.size = (vbr.size[0], size[1])
        self.addPass(vbr, pos=(size[0]-vbr.size[0],0))
        # top horizontal bevel
        hbt = shader.HorizontalBevel(rgb, rgb, rgb, 1, 0, 0)
        hbt.size = (size[0], hbt.size[1])
        self.addPass(hbt, pos=(0,0))
        # bottom horizontal bevel
        hbb = shader.HorizontalBevel(rgb, rgb, rgb, 1, 0, 0)
        hbb.size = (size[0], hbb.size[1])
        self.addPass(hbb, pos=(0,size[1]-hbb.size[1]))

#==============================================================================