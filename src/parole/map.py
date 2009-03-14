#Python Advanced Roguelike Engine (Parole)
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
TODO: Map library docs.
"""

import parole, shader, resource, pygame
from pygame import Rect
from colornames import colors
import gc, random, math, random, pprint
import fov, perlin
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
    parole.info('Map default annotation text RGB: %s',
            conf.map.annotationTextRGB)
    MapFrame.defaultAnnoteTextRGB = tuple(conf.map.annotationTextRGB)
    parole.info('Map default annotation text background RGBA: %s',
            conf.map.annotationTextBgRGBA)
    if conf.map.annotationTextBgRGBA:
        MapFrame.defaultAnnoteTextBgRGBA = tuple(conf.map.annotationTextBgRGBA)
    else:
        MapFrame.defaultAnnoteTextBgRGBA = None

def __init():
    """
    Initializes the map module. Automatically called during engine 
    startup - user code shouldn't need to use this function.
    """
    parole.conf.notify(__onConfigChange, True)
    
def __unload():
    """
    Unloads the map module during engine shutdown.
    """
    parole.conf.notify(__onConfigChange, False)

#==============================================================================
#{ Representation and implementation of 2D maps

class MapObject(object):
    """
    Any game object contained within a L{Tile} must be an instance of
    C{MapObject}.
    
    @type    layer: C{int}
    @param   layer: Determines either the order in which the objects in a tile
                    should be drawn, or determines which object in a tile gets
                    drawn alone (the one with the highest layer),
                    depending on the Map's options.
    @type shader: L{Shader}
    @param shader: The shader to use for drawing this object on the map. All
                   MapObjects on the same Map must have the same sized shaders.
                   TODO: C{MapShader} class? must provide C{applyLight} and
                   C{bgShader}.
    @type blocksLOS: C{bool}
    @param blocksLOS: Whether this object blocks line of sight through the
                      tile containing it. This affects both FOV and LOS
                      calculations performed by the L{Map2D} containing the
                      object.
    @type blocksMove: C{bool}
    @param blocksMove: Whether this object blocks movement through the
                      tile containing it. No engine code is affected by this,
                      but it is included as most user code will want something
                      like it for their L{MapObject}s.
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
        """
        The display layer of this L{MapObject}. Setting this property
        automatically updates any containing L{Tile}'s display of the
        L{MapObject}.
        """
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
        """
        The display L{Shader} of this L{MapObject}. Setting this property
        automatically updates any containing L{Tile}'s display of the
        L{MapObject}.
        """
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
    A L{Tile} is simultaneously a container of L{MapObject}s located at the same
    position in some L{Map2D}, and a L{Shader} that implements a method of
    displaying the map position, given what objects are located there. The
    default method provided by the L{Tile} class is to display the C{shader}
    attribute of the L{MapObject} with the highest C{layer}, and possibly, if
    the highest L{MapObject} does not have a C{bgShader} attribute, the
    C{bgShader} attribute of the highest-layer object that does have one. User
    code display L{Tile} contents in a different way by subclassing L{Tile} and
    overriding the L{resetPasses} method (the C{tileType} argument to
    L{Map2D.__init__} allows you to create L{Map2D} instances with your custom
    L{Tile} subclass).

    A L{Tile} instance is fully picklable, assuming that all of its contents
    are.

    @ivar contents: Contains the L{MapObject}s located in this L{Tile}.
    @type contents: C{set}
    @ivar map: A reference to the L{Map2D} instance containing this L{Tile}.
    @type map: L{Map2D}
    @ivar row: The row-coordinate of this L{Tile}'s location within its
    L{Map2D}.
    @type row: C{int}
    @ivar col: The column-coordinate of this L{Tile}'s location within its
    L{Map2D}.
    @type row: C{int}
    @ivar availLight: The total light available at this L{Tile}. Set by
    L{addLight}, L{removeLight}, L{clearLight}.
    @type availLight: C{(r,g,b)}-tuple
    """
    
    def __init__(self, map, (col, row), contents=None):
        """
        Creates a L{Tile} to track the contents and display of position C{(col,
        row)} in some L{Map2D}. If C{contents} is given, it should be a sequence
        of L{MapObject}s that the L{Tile} will begin populated by.

        The user should not normally have to worry about creating new L{Tile}
        instances; the L{Tile}s of a L{Map2D} are all created by the
        L{Map2D}'s constructor.
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
        """
        Returns the state of a L{Tile} instance for pickling. Overlays and the
        current frozen shader (if any) will not be preserved.
        """
        # Returns the state of an instance for pickling
        state = super(Tile, self).__getstate__()
        state['overlays'] = {}
        state['_Tile__frozenShader'] = None
        #del state['map']
        #parole.debug('Tile.__getstate__: %r', state)
        return state

    def __setstate__(self, state):
        """
        Sets the state of a new L{Tile} instance while unpickling.
        """
        super(Tile, self).__setstate__(state)
        self.resetPasses()

    def __iter__(self):
        """
        Iterates through the L{MapObject}s contained here, in arbitrary order.
        """
        for obj in self.contents:
            yield obj

    def __contains__(self, obj):
        """
        Tests whether the L{Tile} contains a given L{MapObject}.
        """
        return obj in self.contents

    #@parole.Property
    def getHighestLayer(self):
        """
        Returns the layer of the highest-layer L{MapObject} contained by this
        L{Tile}, or C{None} if the L{Tile} is empty.
        """
        try:
            return self._highestObject.layer
        except AttributeError:
            return None
        
    #@parole.Property
    def getHighestShader(self):
        """
        Returns the C{shader} attribute of the highest-layer L{MapObject}
        contained by this L{Tile}, or C{None} if the L{Tile} is empty.
        """
        try:
            return self._highestObject.shader
        except AttributeError:
            return None
        
    @parole.Property
    def highestObject():
        """
        A L{Property} attribute that references the highest-layer L{MapObject}
        contained by this L{Tile}. Setting this property causes the L{Tile}
        to recompute how it is displayed. The set value must be a L{MapObject}
        contained by the C{Tile}. If the L{MapObject}'s C{layer} attribute is
        not actually the highest present in this L{Tile}, it will nonetheless be
        displayed as though it were, though strange things may eventually result
        from this inconsistency.

        Whenever a L{MapObject} is added to or removed from a L{Tile}, this
        property is automatically determined and set.
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
            self.resetPasses()

    def resetPasses(self):
        """
        Calculates how the L{Tile} should be displayed. The L{Tile} is a
        L{Shader} instance, and this method is expected to arrange its passes
        for display. The base implementation first clears all passes (via
        L{Shader.clearPasses}, then, if the highest object has a null C{bg_rgb}
        attribute, adds the C{bgShader} attribute (assumed to be a L{Shader}
        instance) of the C{shader} attribute of the highest-layer object with
        non-null C{bg_rgb}; in any case, it then adds the C{shader} attribute
        (assumed to be a L{Shader} instance) of the highest object. Finally, any
        overlays that have been applied to this L{Tile} (see L{addOverlay}) are
        added.

        @bug: Should get called whenever potential sources of backgrounds change
        in the tile.
        @bug: Does not respect the order in which overlays were added.
        """
        # FIXME: this should also get called when potential sources of
        # backgrounds change in the tile
        self.clearPasses()

        # kind of hacky. if this object doesn't have a background
        # color, find the next highest one that does, and add a colorfield
        # with that color, so that backgrounds show through higher objects
        # with no backgrounds.
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
        # FIXME: does not respect the order in which overlays were added
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
        obj.parentTile = None
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
        Clears the contents of this L{Tile}.
        """
        for obj in list(self.contents):
            self.remove(obj)
        
    def updateContents(self, otherSet):
        """
        Updates the contents of the L{Tile} to be the union of its contents with
        those of the given sequence of L{MapObject}s.
        """
        #set.update(self, otherSet)
        self.contents.update(otherSet)

    def hasLOSBlocker(self):
        """
        Returns C{True} iff the tile contains a L{MapObject} whose
        C{blocksLOS} attribute is C{True}.
        """
        for obj in self:
            if obj.blocksLOS:
                return True
        return False

    def hasMoveBlocker(self):
        """
        Returns C{True} iff the tile contains a L{MapObject} whose
        C{blocksMove} attribute is C{True}.
        """
        for obj in self:
            if obj.blocksMove:
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
        Equivalent to C{Tile.addLight(rgb, -intensity)}.
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
        """
        Get a "frozen" L{Shader} of this tile's appearance. For use, e.g., when
        displaying an out-of-FOV tile as it was last remembered. The result is
        memoized until L{clearFrozenShader} is called.

        @return: A L{Shader} object.
        """
        if self.__frozenShader:
            return self.__frozenShader
        self.update()
        self.__frozenShader = shader.SurfacePass(self.image)
        return self.__frozenShader

    def clearFrozenShader(self):
        """
        Clear the cached L{Shader} returned by L{frozenShader}.
        """
        self.__frozenShader = None

    def addOverlay(self, sdr, pos=None):
        """
        Adds a L{Shader} to be displayed as an overlay on this tile. It will
        appear on top of the shaders of any contained L{MapObject}s, unless
        L{resetPasses} has been overridden to do something else with overlays.
        The order in which overlays are added is significant.

        @param sdr: The L{Shader} to add as an overlay.
        @param pos: The positional offset at which to display the overlay
                    shader.
        @type pos:  C{(x,y)}-tuple.
        """
        self.overlays[sdr] = pos
        self.addPass(sdr, pos=pos)

    def removeOverlay(self, sdr):
        """
        Removes a previously added overlay L{Shader}.
        """
        del self.overlays[sdr]
        self.remPass(sdr)

    def clearOverlays(self):
        """
        Removes all previously added overlay L{Shader}s.
        """
        self.remPass(self.overlays)
        self.overlays.clear()

    def overlayShader(self):
        """
        Returns a L{Shader} containing all of the overlays on this L{Tile}.
        """
        s = parole.shader.Shader('overlayShader', self.size)
        for p in self.passes:
            if p in self.overlays:
                s.addPass(p, pos=self.overlays[p])
        return s
        
#==============================================================================

class Map2D(object):
    """
    A two-dimensional array of L{Tile} objects, along with varioius utility
    methods for common tasks related to geometry, distance, field-of-view, and
    line-of-sight. Individual tiles can be retrieved via C{__getitem__}, e.g.::

        mapObject = Map2D('mapObject', (32,32))
        x, y = 2, 16
        xyTile = mapObject[x,y]

    A L{Map2D} object can also be iterated over, which has the effect of
    iterating through all the L{Tile}s contained in it, in column-major order.
    """
    def __init__(self, name, (cols, rows), tileType=Tile):
        """
        Create a L{Map2D} instance with the given name and dimenions.

        @param name: The name of this map, used for C{str} and C{repr}.
        @type name: C{str}
        @param cols: The number of columns of L{Tile}s to be
        contained by this map.
        @type cols : C{int}
        @param rows: The number of rows of L{Tile}s to be
        contained by this map.
        @type rows: C{int}
        @param tileType: A C{callable} object to be used to construct the
        L{Tile} objects in this map. It should accept two arguments -- this
        L{Map2D} instance and a C{(col, row)} position tuple -- just like
        L{Tile.__init__}, and it should return an instance of L{Tile} or a
        subclass.
        """
        self.name = name

        if cols < 1 or rows < 1:
            raise ValueError('Map2D must have nonzero dimensions.')
        self.rows, self.cols = rows, cols

        self.tiles = [[tileType(self, (col,row)) for \
                col in range(cols)] for row in range(rows)]
        if not isinstance(self.tiles[0][0], Tile):
            raise TypeError('tileType should be a subclass of Tile.')
            
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

    def __getitem__(self, (x,y)):
        return self.tiles[y][x]

    def __iter__(self):
        return self.iterTiles()

    def __contains__(self, tile):
        for t in self:
            if t is tile:
                return True
        return False

    def rect(self):
        """
        Returns a pygame C{Rect} object whose dimensions are that of this map,
        in tiles.
        """
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

    def iterTiles(self):
        """
        Returns a generator yielding a sequence of all the L{Tile} objects in
        this map, in column-major order. If you just need to iterate through the
        tiles, C{for tile in mapObject} is equivalent to C{for tile in
        mapObject.iterTiles()}.
        """
        for x in xrange(self.cols):
            for y in xrange(self.rows):
                yield self[x,y]

    def getRow(self, y):
        """
        Returns a list of the C{Tiles} in the given row of this map.
        """
        return self.tiles[y]
        
    def tileAt(self, (x,y)):
        """
        Returns the L{Tile} object located in this map at the given coordinates.
        Equivalent to C{self[x,y]}.

        @param x: The x-coordinate (column) of the L{Tile} to return.
        @type x: C{int}
        @param y: The y-coordinate (row) of the L{Tile} to return.
        @type y: C{int}.
        """
        return self.tiles[y][x]
    
    def add(self, (x,y), *objs):
        """
        Adds one or more L{MapObject}s to the L{Tile} at the given coordinates.
        Equivalent to:::

            for obj in objs:
                self[x,y].add(obj)

        @param x: The x-coordinate (column) of the L{Tile} to add to.
        @type x: C{int}
        @param y: The y-coordinate (row) of the L{Tile} to add to.
        @type y: C{int}.
        """
        tile = self[x,y]
        for obj in objs:
            tile.add(obj)
        return tile

    def remove(self, (x,y), *objs):
        """
        Removes one or more L{MapObject}s from the L{Tile} at the given
        coordinates. Equivalent to:::

            for obj in objs:
                self[x,y].remove(obj)

        @param x: The x-coordinate (column) of the L{Tile} to remove from.
        @type x: C{int}
        @param y: The y-coordinate (row) of the L{Tile} to remove from.
        @type y: C{int}.
        """
        tile = self[x,y]
        for obj in objs:
            tile.remove(obj)    
        return tile

    def onAdd(self, tile, obj):
        self.notifyMonitors(obj)
    
    def onRemove(self, tile, obj):
        self.notifyMonitors(obj)
    
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
            for obj in self[x,y]:
                if obj.blocksLOS:
                    return True
            return False

        fov.fieldOfView(pos[0], pos[1], self.cols, self.rows, radius,
                visitFunc, isBlocked or defaultIsBlocked, quadrants=quadrants)
        #parole.debug('fieldOfView: time = %sms', parole.time() - time)

    def monitorNearby(self, obj, dist, callback, condition=None):
        # TODO: let user specify callback as an object and the name of a method
        # to bind.
        # User had better make sure callback and condition are pickleable
        if (not isinstance(obj, Tile) and not isinstance(obj, MapObject)) \
                or (isinstance(obj, MapObject) and obj.parentTile not in self) \
                or (isinstance(obj, Tile) and obj not in self):
            raise ValueError('obj must be a Tile or MapObject contained '
                             'by this Map.')

        self.distMonObjs[obj] = (dist, callback, condition)
        self.dirtyDistMonObjs[obj] = set()

    def notifyMonitors(self, obj):
        for (monObj, (dist, callback, condition)) in \
                self.distMonObjs.iteritems():
            #parole.debug('remove: checking %s nearby %s', obj, monObj)
            condition = condition or (lambda x: True)
            monObjPos = isinstance(monObj, Tile) and (monObj.col, monObj.row) \
                    or monObj.pos
            if condition(obj) and self.dist(obj.pos, monObjPos) <= dist:
                self.dirtyDistMonObjs[monObj].add((obj, obj.pos))

    def unmonitorNearby(self, obj):
        if obj in self.distMonObjs:
            del self.distMonObjs[obj]
            del self.dirtyDistMonObjs[obj]

    def updateDirtyMonitors(self):
        #parole.debug('updateDirtyMonitors: %s', self.dirtyDistMonObjs)
        #parole.debug('distMonObjs: %s', self.distMonObjs)
        for monObj, objsPos in self.dirtyDistMonObjs.iteritems():
            if objsPos:
                callback = self.distMonObjs[monObj][1]
                callback(monObj, objsPos)
                objsPos.clear()

    def updateDirtyLight(self):
        for t in self.tilesWithDirtyLight:
            t.applyLight()
        self.tilesWithDirtyLight.clear()

    def update(self, updateDirtyMonitors=True, updateDirtyLight=True):
        if updateDirtyMonitors:
            self.updateDirtyMonitors()
        if updateDirtyLight:
            self.updateDirtyLight()

    def traceRay(self, p1, p2, callback):
        """
        Traces a Bresenham ray from one tile to another, calling C{callback} on
        each tile along the way (including start and end).  C{p1} and C{p2} can
        either be the C{Tile} objects (in this C{Map2D}) themselves, or
        C{(col,row)}-tuples. C{callback} should be a callable object accepting a
        C{Tile} as an argument, and should return C{True} if tracing should
        continue past this C{Tile}, or C{False} if the trace should stop.
        C{traceLOS} returns the last C{Tile} object reached by the trace.
        """
        if isinstance(p1, Tile):
            t1 = p1
            p1 = (t1.col, t1.row)
        else:
            t1 = self[p1]
        if isinstance(p2, Tile):
            t2 = p2
            p2 = (t2.col, t2.row)
        else:
            t2 = self[p2]

        if not (t1 in self and t2 in self):
            raise ValueError('Tiles not in this Map2D instance.')

        bp = list(bresenhamPoints(p1, p2))
        if bp[-1] == p1:
            # points reversed
            bp.reverse()
        for currentP in bp:
            if not callback(self[currentP]):
                break

        return self[currentP]

    def traceLOS(self, p1, p2, callback):
        """
        Traces a Bresenham ray like C{Map2D.traceRay}, but automatically stops
        when it encounters a C{Tile} containing a C{MapObject} whose member
        C{blocksLOS} is C{True}. The first C{Tile} in the ray does not count
        toward blocking LOS, and callback will always be invoked on the last
        C{Tile} visited.
        """
        def cb(tile):
            if (callback) and (not callback(tile)):
                return False
            for obj in tile:
                if obj.blocksLOS:
                    return False
            return True

        return self.traceRay(p1, p2, cb)

    def testLOS(self, p1, p2):
        """
        Tests whether a Bresenham ray can be cast from one tile to another.
        C{p1} and C{p2} can either be the C{Tile} objects (in this C{Map2D})
        themselves, or C{(col,row)}-tuples.
        """
        if isinstance(p2, Tile):
            destT = p2
        else:
            destT = self[p2]
        return self.traceLOS(p1, p2, None) is destT

#==============================================================================

class LightSource(object):
    minIntensity = 0.03

    def __init__(self, rgb, intensity, fallOff=1.0, blockTest=None):
        self.rgb = rgb
        self.intensity = intensity
        self.radius = 0
        self.distIntensities = {}
        self.fallOff = fallOff
        self.appliedTiles = {}
        self.pos = None
        self.blockTest = blockTest or objectBlocksLOS
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
        """
        Be sure to remove before changing intensity!
        """
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

        def tileBlocked(x,y):
            t = map[x,y]
            for obj in t:
                if self.blockTest(obj):
                    return True
            return False

        map.fieldOfView(pos, self.radius, visit, isBlocked=tileBlocked)
        map.monitorNearby(map[pos], self.radius, self, self.blockTest)
        self.pos = pos
        #parole.debug('LightSource.apply: time = %sms', parole.time() - time)

    def remove(self, map):
        time = parole.time()
        if self.pos:
            map.unmonitorNearby(map[self.pos])
            self.pos = None
        else:
            parole.warn("Removing LightSource that wasn't previously added")
        for pos, intensity in self.appliedTiles.iteritems():
            t = map[pos]
            t.removeLight(self.rgb, intensity)
            #t.applyLight()
        self.appliedTiles = {}
        #parole.debug('LightSource.remove: time = %sms', parole.time() - time)

    def __call__(self, tile, objsPos):
        # Handle something that blocks light moving through our radius.
        # Basically just remove then re-add ourselves, so that shadows get
        # recalculated.
        # FIXME: does this interact strangely with changing the intensity/color
        # of the light source between calls?
        self.remove(tile.map)
        self.apply(tile.map, (tile.col, tile.row))

#==============================================================================
#{ Displaying 2D maps

class MapFrame(shader.Frame):
    """
    A L{Frame} for displaying a view of a L{Map2D}. Provides a scrollable grid of
    shaders for displaying the tiles of the map. The tile size must be known
    in advance, when the C{MapFrame} is created, and must agree with the actual
    size of the shaders offered by the tiles of the map.
    """

    defaultAnnoteLineRGB = (255, 255, 0)
    defaultAnnoteReticleRGB = (255, 255, 0)
    defaultAnnoteFont = None
    defaultAnnoteTextRGB = (255, 255, 255)
    defaultAnnoteTextBgRGB = None

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
        self.fovObj = None
        self.fovRad = None
        self.__dirtyFovQuads = None
        self.visibleTiles = set()
        self.__rememberSeenTiles = False
        self.rememberedTiles = set()
        self.__annotationsAt = {} # Tile -> (Annotation, Rect)

        # public attributes
        self.selectedTile = None
        self.reticle = ReticleOverlayShader(self.__tileSize)

        if map:
            self.setMap(map)

    def __getstate__(self):
        parole.warn('MapFrame is being pickled!')
        return super(MapFrame, self).__getstate__()

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
                if tile in self.__grid.passes:
                    self.__grid.remPass(tile)
                self.__grid[tile.col, tile.row] = None
        if not map:
            self.bindVisibilityToFOV(None, None)
        self.__map = map
        self.fovObj = None
        self.fovRad = None
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

        if self.__grid:
            self.__grid.clearPasses()

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
        vx, vy = (cx-self.width/2, cy-self.height/2)
        if vx + self.width > self.__grid.width:
            vx = self.__grid.width - self.width
        if vy + self.height > self.__grid.height:
            vy = self.__grid.height - self.height
        self.__scroll.offset = (vx, vy)

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
        TODO: viewRectTiles()
        """
        pass

    def bindVisibilityToFOV(self, obj, radius, remember=True,
            inFOVCallback=None, leaveFOVCallback=None, fovCondition=None):
        """
        Causes the L{MapFrame} to only display L{Tile}s of the map that are within
        the field of view of the given L{MapObject}, which must be located
        somewhere in the currently displayed map. 

        @param obj: The L{MapObject} to whose field of view to bind the
                   display. Pass C{None} to deactivate any current binding.
        @param radius: The radius to use in calculating the object's field of view.
        @param remember: Whether to continue displaying tiles that were at one
        time in C{obj}'s field of view but are no longer. TODO: a way to
        display remembered tiles differently than currently visible ones.
        @param inFOVCallback: An optional C{callable} object to be invoked
        whenever the field-of-view is updated. It should accept a C{set} of
        the C{Tile}s found to be visible.
        @param leaveFOVCallback: An optional C{callable} object to be invoked
        whenever the field-of-view is updated. It should accept a C{set} of
        the previously visible C{Tile}s that have left the field-of-view.
        @param leaveFOVCallback: An optional C{callable} object that must return
        C{True} on a L{Tile} object in order for that location to be considered
        visible, even if it is otherwise within FOV.
        """
        self.__map.unmonitorNearby(self.fovObj)

        self.fovObj = obj
        self.fovRad = (obj and radius) or None
        self.__dirtyFovQuads = set()
        self.visibleTiles.clear()
        self.rememberedTiles.clear()
        self.__rememberSeenTiles = remember
        if obj:
            self.__disableAll()
            self.__map.monitorNearby(obj, radius, self.__touchFOVQuadrant,
                    self.__blocksLOS)
            self.__touchFOVQuadrant(obj, [(obj, obj.pos)])
        else:
            self.__enableAll()
        self.inFOVCallback = inFOVCallback
        self.leaveFOVCallback = leaveFOVCallback
        self.fovCondition = fovCondition

    def __disableAll(self):
        if self.__map:
            for x in xrange(self.__map.cols):
                for y in xrange(self.__map.rows):
                    #self.__grid.disable(x, y)
                    self.__grid[x,y] = self.__map[x,y].overlayShader()

    def __enableAll(self):
        if self.__map:
            for x in xrange(self.__map.cols):
                for y in xrange(self.__map.rows):
                    #self.__grid.enable(x, y)
                    self.__grid[x,y] = self.__map[x,y]

    def __blocksLOS(self, obj):
        #parole.debug('checking if blocks los')
        return obj.blocksLOS or obj is self.fovObj

    def __touchFOVQuadrant(self, monObj, objsPos):
        assert(monObj is self.fovObj)
        for (obj, pos) in objsPos:
            if monObj is obj:
                # the fov object has moved
                self.__dirtyFovQuads = set(['ne', 'se', 'sw', 'nw'])
            else:
                self.__dirtyFovQuads.add(self.__map.quadrant(pos, monObj.pos))

        #parole.debug('MapFrame.__touchQuadrant: dirty quads = %s',
        #        self.__dirtyFovQuads)

    def touchFOV(self):
        """
        Marks all FOV quadrants as dirty.
        """
        self.__dirtyFovQuads = set(['ne', 'se', 'sw', 'nw'])

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
            tile = self.__map[x,y]
            if self.fovCondition and not self.fovCondition(tile):
                return
            if (x,y) not in self.visibleTiles:
                self.__grid[x,y] = tile
                if self.__rememberSeenTiles:
                    self.rememberedTiles.add((x,y))
            newVisibleTiles.add((x,y))

        self.__map.fieldOfView(self.fovObj.pos, self.fovRad, fovVisit,
                quadrants=self.__dirtyFovQuads)

        formerlyVisibleTiles = self.visibleTiles - newVisibleTiles
        if self.leaveFOVCallback:
            self.leaveFOVCallback(formerlyVisibleTiles)

        for (x,y) in formerlyVisibleTiles:
            if self.__rememberSeenTiles:
                self.__map[x,y].clearFrozenShader()
                self.__grid[x,y] = self.__map[x,y].frozenShader()
            else:
                # but what about overlays?
                #self.__grid.disable(x, y)
                self.__grid[x,y] = self.__map[x,y].overlayShader()

        self.visibleTiles = newVisibleTiles
        self.__dirtyFovQuads.clear()

        if self.inFOVCallback:
            self.inFOVCallback(self.visibleTiles)

    def inFOV(self, tile):
        """
        If the view is currently bound to a field of view (see
        L{bindVisibilityToFOV}, returns C{True} if the given tile is currently
        visible. If the view is not bound, returns C{True} always.
        """
        if self.fovObj:
            return (tile.col, tile.row) in self.visibleTiles
        return True

    def remembered(self, tile):
        """
        If the view is currently bound to a field of view (see
        L{bindVisibilityToFOV}, returns C{True} if the given tile is
        "remembered". If a tile is in FOV (L{inFOV}) it is also remembered.
        If the view is not bound, returns C{True} always.
        """
        if self.fovObj:
            return self.__rememberSeenTiles and \
                   (tile.col, tile.row) in self.rememberedTiles
        return True

    def selectTile(self, posOrX, y=None):
        """
        A convenience function that applies self.reticle as an overlay at the
        given position. Only one tile may be selected at a time in this way, and
        subsequent calls to C{selectTile} will automatically remove the overlay
        from the previously selected tile. To select no tile call
        C{selectTile(None)}.
        """
        #parole.debug('select: %s,%s', posOrX, y)
        if self.selectedTile:
            self.selectedTile.removeOverlay(self.reticle)
        if posOrX is not None:
            self.selectedTile = self.__map[type(posOrX) is tuple and posOrX\
                    or (posOrX,y)]
            self.selectedTile.addOverlay(self.reticle)
        else:
            self.selectedTile = None
        #parole.debug('selectedTile = %s', self.selectedTile)

    def annotate(self, tile, shaderOrText, ann=None, lineRGB=None,
            reticleRGB=None, textFont=None, textRGB=None, textBgRGBA=None,
            textWidth=150):
        """
        Annotates the given L{Tile} of this L{MapFrame}'s current L{Map2D}.
        There are three ways to use this method: 
            1. By supplying an L{Annotation} object (C{ann}) to use directly.
               Pass C{None} for C{shaderOrText}.
            2. By giving a L{Shader} object (C{shaderOrText}) from which to
               construct an L{Annotation}. Pass C{None} for C{ann} (its
               default).
            3. By simply giving some text (C{shaderOrText}) from which to
               construct a basic text-displaying L{Annotation}. Pass C{None} for
               C{ann} (its default).

        If method 2 or 3 is being used, the remaining keyword arguments
        (C{lineRGB, reticleRGB, textFont, textWidth}) may be specified to
        control the appearance of the L{Annotation} that is built. If method 1
        is used, the L{Annotation} object (C{ann}) overrides any values for
        these arguments.

        @param tile:         The L{Tile} to annotate. Must be contained in this
                             L{MapFrame}'s current L{Map2D}.
        @type tile:          L{Tile}
        @param shaderOrText: The shader or text from which to construct an
                             L{Annotation} if one is not being provided through
                             C{ann}.
        @type shaderOrText:  L{Shader} or C{str} or C{None}.
        @param ann:          The L{Annotation} object to place, if one is not
                             being constructed through the other arguments.
        @type ann:           L{Annotation} or C{None}.
        @param lineRGB:      The color of the line linking the annotated L{Tile}
                             to it's L{Annotation}, if being constructed from a
                             shader or text.
        @type lineRGB:       C{(red,green,blue)}-tuple or C{None}.
        @param reticleRGB:   The color of the reticle overlay place on the
                             annotated L{Tile} if the annotation is being
                             constructed from a shader or text.
        @type reticleRGB:    C{(red,green,blue)}-tuple or C{None}.
        @param textFont:     The font to render the text in if the L{Annotation}
                             is being created from text (method 3).
        @type textFont:      C{pygame.Font}.
        @param textWidth:    Text wrap-width if the L{Annotation} is being
                             created from text (method 3).
        @type textRGB:       C{(red,green,blue)}-tuple or C{None}.
        @param textRGB:      Text color if the L{Annotation} is being created
                             from text (method 3). Default is white.
        @type textBgRGBA:    C{(red,green,blue,alpha)}-tuple or C{None}.
        @param textBgRGBA:   Color of background field behind text if the
                             L{Annotation} is begin created from text (method
                             3). Default is C{(0,0,0,0)}.
        @return:             The L{Annotation} object placed, whether it was
                             constructed by methods 1 or 2, or specified as in
                             method 1.
        """
        # tile may be a Tile instance or a coordinate tuple -- figure which
        # Tile we're referring to
        if type(tile) is tuple and len(tile)==2:
            tile = self.getMap()[tile]
        if not isinstance(tile, Tile) or tile not in self.getMap():
            raise TypeError('tile must be a Tile instance in my Map2D')

        textRGB = textRGB or self.defaultAnnoteTextRGB
        textBgRGBA = textBgRGBA or self.defaultAnnoteTextBgRGBA

        # Generally, shaderOrText can be any Shader, but for convenience, if
        # it is a string, we create a TextBlock containing that string in a
        # default font.
        if isinstance(shaderOrText, parole.shader.Shader):
            sdr = shaderOrText
        elif type(shaderOrText) is str:
            txt = shader.TextBlockPass(textFont or self.defaultAnnoteFont,
                    textRGB, #bg_rgb = textBgRGBA,
                    text=shaderOrText, wrap='word', wrap_width=textWidth)
            txt.update()
            if textBgRGBA:
                sz = (txt.size[0] + 4, txt.size[1] + 4)
                sdr = shader.Shader('textAnnote', size=sz,
                        passes=[shader.ColorField(textBgRGBA, sz)])
                sdr.addPass(txt, pos=(2,2))
            else:
                sdr = txt
            sdr.update()
        elif not ann:
            # if the user didn't specify an Annotation, he has to give us some
            # text to make one with.
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
                #for annote in self.__annotationsAt[tile]:
                for annote in sum(self.__annotationsAt.values(), []):
                    annoteRect = annote.prefRect
                    if rect.colliderect(annoteRect):
                        rectFree = False
                        break
                if rectFree and visibleRect.contains(rect):
                    self.__placeAnnotation(tile, ann, rect)
                    ann.prefRect = rect
                    #parole.debug('ann: %r', ann)
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
        #parole.debug('ann: %r', ann)
        return ann

    def removeAnnotation(self, annotation):
        """
        Remove a previously added (via L{annotate}) L{Annotation}.

        @param annotation: The L{Annotation} to remove. This should be the value
                           returned by L{annotate}.
        @type annotation: L{Annotation}.
        """
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
        # make sure the reticle disappears from unseen but remembered tiles
        tile = annotation.tile
        if not self.inFOV(tile):
            if self.__rememberSeenTiles and self.remembered(tile):
                tile.clearFrozenShader()
                self.__grid[tile.col,tile.row] = tile.frozenShader()
            else:
                self.__grid[tile.col,tile.row] = tile.overlayShader()

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

        # handle out of view tiles
        if not self.inFOV(tile):
            if self.__rememberSeenTiles and self.remembered(tile):
                # make sure the reticle appears on unseen but remembered tiles
                tile.clearFrozenShader()
                self.__grid[tile.col,tile.row] = tile.frozenShader()
            else:
                self.__grid[tile.col,tile.row] = tile.overlayShader()

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

class ReticleOverlayShader(shader.Shader):
    """
    A shader that draws a 1-pixel wide border around its rectangle area, used by
    default by L{MapFrame.selectTile} as the overlay placed on the selected
    tile. 

    @param size: The rectangular extents of the box to draw.
    @type size: C{(width,height)}-tuple
    @param rgb: The color in which to draw the box/border.
    @type rgb: C{(r,g,b)}-tuple
    """
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

class Annotation(shader.Shader):
    """
    An C{Annotation} is a message (or any kind of) window/shader linked to a
    particular L{Tile} of a L{Map2D} that can be displayed in an associated
    L{MapFrame}. The C{Annotation} is display placing an overlay reticle on the
    annotated L{Tile}, and drawing a line from the reticle to the
    C{Annotation}'s shader, which is automatically positioned near the annotated
    L{Tile}. Annotated tiles not currently visible in the L{MapFrame} have their
    shaders placed at the nearest edge of the screen, with a line extending in
    the direction of the L{Tile}.
    
    @param tile: The L{Tile} to annotate.
    @type tile: L{Tile}.
    @param shader: The L{Shader} with which to annotate the tile.
    @type shader: L{Shader}.
    @param lineRGB: The color of the line linking the tile to the annotation
                    shader. Pass C{None} for the default color
                    (L{MapFrame.defaultAnnoteLineRGB}).
    @type lineRGB: C{(red,green,blue)}-tuple or C{None}.
    @param reticleRGB: The color of the reticle overlay to apply to the
                       annotated tile. Pass C{None} for the default color
                       (L{MapFrame.defaultAnnoteReticleRGB}).
    @type reticleRGB: C{(red,green,blue)}-tuple or C{None}.
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

class AsciiTile(shader.Pass):
    
    font = None
    antialias = True
    makeSquare = False
    
    @classmethod
    def characterSize(cls):
        """
        Returns the dimensions of a single AsciiTile. Assumes that
        AsciiTile.font has been set to a monospaced font, and returns the
        dimensions of a "#" character rendered in that font.
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

        if self.reflRGB != prevReflRGB or self.reflBgRGB != prevReflBgRGB:
            self.bgShader.rgb = self.reflBgRGB or (0,255,255)            
            self.touch()

#==============================================================================
#{ Generic map content generators

class Generator(object):
    """
    A base clase for objects that generate content for, or apply changes to, a
    portion of a L{Map2D}. Various generators can be applied one after
    another to different, possibly overlapping regions of a map. 
    """
    def __init__(self, name, clearFirst=False):
        self.name = name
        self.clearFirst = clearFirst

    def __repr__(self):
        return "Generator(%s)" % (repr(self.name),)

    def apply(self, map, rect=None):
        """
        Subclasses override this to apply the generator to the given region
        of the given map, or to the whole thing if unspecified.
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
    def __init__(self, name, template, legend, backgroundGen=None,
            clearFirst=False, extend="clip"):
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
        self.backgroundGen = backgroundGen

    def __repr__(self):
        return "TemplateGenerator(%s, '...', ...)" % (repr(self.name),)

    def apply(self, map, rect=None, parentRect=None):
        rect = (rect or (parentRect or map.rect())).clip(parentRect or map.rect())
        #super(TemplateGenerator, self).apply(map, rect)

        if self.backgroundGen:
            self.backgroundGen.apply(map, rect)

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
        #parole.debug('%s: applying to %r', self, rect)
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

# FIXME: forceFullConnectivity
class RoomsAndCorridorsGenerator(Generator):
    def __init__(self, name, rockAreaGenerator, roomBill, diggerClass,
            floorFunc, connectAdjacent=True, minConnectDist=1,
            maxConnectDist=14, forceFullConnectivity=True, clearFirst=True):
        super(RoomsAndCorridorsGenerator, self).__init__(name, clearFirst)
        self.roomBill = roomBill
        self.rockAreaGenerator = rockAreaGenerator
        self.diggerClass = diggerClass
        self.floorFunc = floorFunc
        self.connectAdjacent = connectAdjacent
        self.minConnectDist = minConnectDist
        self.maxConnectDist = maxConnectDist
        self.forceFullConnectivity = forceFullConnectivity

    def apply(self, map, rect=None):
        rect = (rect or map.rect()).clip(map.rect())
        self.rockAreaGenerator.apply(map, rect)

        # Lay the requested rooms
        totalRequestedRooms = sum([num for (room, num) in self.roomBill])
        rooms = []
        for roomType, nRooms in self.roomBill:
            for n in xrange(nRooms):
                self.layRoom(map, rect, roomType, rooms)
        parole.debug('Laid %d of %d requested rooms.', len(rooms),
                totalRequestedRooms)

        # Connect the rooms
        self.connectRooms(map, rooms, self.diggerClass,
                self.minConnectDist, self.maxConnectDist, self.connectAdjacent)

        return rooms

    def layRoom(self, map, rect, roomType, rooms, tries=100):
        # Keep choosing a random location and size for the room until we find one
        # that doesn't intersect with existing rooms, then place it and return
        while tries:
            tries -= 1
            roomPos = (random.randint(0, rect.right-1),
                       random.randint(0, rect.bottom-1))
            room = roomType(roomPos)
    
            if not rect.contains(room.rect):
                # we generated a rectangle not completely enclosed by the map
                continue
    
            if room.rect.collidelist([r.rect for r in rooms]) != -1:
                # the generated rectangle overlaps with an existing one
                continue
    
            rooms.append(room)
            room.apply(map)
            return
    
    def __corners(self, rect):
        return (rect.topleft,
                (rect.topright[0]-1, rect.topright[1]),
                (rect.bottomleft[0], rect.bottomleft[1]-1),
                (rect.bottomright[0]-1, rect.bottomright[1]-1))

    def __adjacent(self, room1, room2):
        return room1.rect.inflate(2,2).colliderect(room2.rect.inflate(2,2))
    
    def __perimeter(self, rect):
        for y in (rect.top, rect.bottom-1):
            for x in xrange(rect.left, rect.left+rect.w):
                yield x,y
        for x in (rect.left, rect.right-1):
            for y in xrange(rect.top+1, rect.top+rect.h):
                yield x,y

    def connectRooms(self, map, rooms, diggerClass, minDist, maxDist,
            adjacents=True):
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
    
                    if self.__adjacent(room1, room2):
                        connectedPairs.append(pair1)
                        connectedPairs.append(pair2)
                        #parole.debug('adjacent: %r, %r', room1, room2)
                        self.__connectAdjacent(map, room1, room2)
    
        for room1 in rooms:
            otherRooms = [r for r in rooms if r is not room1]
            otherRects = [r.rect for r in rooms if r is not room1]
            for inflation in xrange(minDist, maxDist+1):
                #parole.debug('inflation %s', inflation)
                inflRoom1 = room1.rect.inflate(inflation, inflation)
                for otherIdx in inflRoom1.collidelistall(otherRects):
                    room2 = otherRooms[otherIdx]
                    pair1 = (room1, room2)
                    pair2 = (room2, room1)
                    if pair1 in connectedPairs or pair2 in connectedPairs:
                        continue
    
                    self.connectDistant(map, room1, room2, rooms, diggerClass())
                    connectedPairs.append(pair1)
                    connectedPairs.append(pair2)

#        if self.forceFullConnectivity:
#            # first find each connected component
#            components = []
#            
#            def visit(pair, currentComponent):
#                r1, r2 = pair
#                currentComponent.append((r1,r2))
#                currentComponent.append((r2,r1))
#                for otherPair in connectedPairs:
#                    if r1 in otherPair and r2 in otherPair:
#                        continue
#                    if (r1 in otherPair or r2 in otherPair) \
#                            and (otherPair not in currentComponent) \
#                            and (tuple(reversed(otherPair)) not in \
#                            currentComponent):
#                        visit(otherPair, currentComponent)
#
#            for cpair in connectedPairs:
#                # if cpair is not in a known connected component, visit it
#                # and add the resulting component to our list
#                inKnownComponent = False
#                for comp in components:
#                    if cpair in comp:
#                        inKnownComponent = True
#                        break
#                if not inKnownComponent:
#                    currentComponent = []
#                    visit(cpair, currentComponent)
#                    components.append(list(currentComponent))
#
#            # add singleton rooms to the components list
#            for r in rooms:
#                inAPair = False
#                for p in connectedPairs:
#                    if r in p:
#                        inAPair = True
#                        break
#                if not inAPair:
#                    components.append([(r,r)])
#
#            parole.debug('*** JOINING %d CONNECTED COMPONENTS ***',
#                    len(components))
#            parole.debug('Components:\n%s', pprint.pformat(components))
#
#            # find the largest component
#            targetComp = components[0]
#            for comp in components:
#                if len(comp) > len(targetComp):
#                    targetComp = comp
#
#            # for each other component, find a room closest to a room in the
#            # largest component, and connect them
#            for comp in components:
#                if comp is targetComp:
#                    continue
#                closestPair = (targetComp[0][0], comp[0][0])
#                closestDist = map.dist(closestPair[0].rect.center,
#                                       closestPair[1].rect.center)
#                for pairInComp in comp:
#                    for pairInTarget in targetComp:
#                        for i,j in [(0,0),(0,1),(1,0),(1,1)]:
#                            d = map.dist(pairInComp[i].rect.center,
#                                         pairInTarget[j].rect.center)
#                            if d < closestDist:
#                                closestPair = (pairInComp[i], pairInTarget[j])
#                                closestDist = d
#
#                # connect them
#                parole.debug('Connecting across components: %r -> %r',
#                        closestPair[0], closestPair[1])
#                self.connectDistant(map, closestPair[0], closestPair[1], rooms,
#                        diggerClass())
#                connectedPairs.append(closestPair)
#                connectedPairs.append(tuple(reversed(closestPair)))
                # add singleton rooms to the components list
                #singletons = []
                #for r in rooms:
                #    inAPair = False
                #    for p in connectedPairs:
                #        if r in p:
                #            inAPair = True
                #            break
                #    if not inAPair:
                #        singletons.append(r)
                #for r in singletons:
                #    rooms.remove(r)



    def __connectAdjacent(self, map, room1, room2):
        perim = list(self.__perimeter(room1.rect))
        random.shuffle(perim)
        rm2Infl = room2.rect.inflate(2,2)
        for x,y in perim:
            if rm2Infl.collidepoint(x,y):
                if (x,y) not in self.__corners(room1.rect) and (x,y) not in self.__corners(rm2Infl):
                    map[x,y].clear()
                    map[x,y].add(self.floorFunc(room1))
                    for (x2,y2) in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                        if room2.rect.collidepoint(x2,y2):
                            map[x2,y2].clear()
                            map[x2,y2].add(self.floorFunc(room1))
                            if (x2,y2) in self.__corners(room2.rect):
                                for (x3,y3) in ((x2+1,y2),(x2-1,y2),(x2,y2+1),(x2,y2-1)):
                                    if room2.rect.collidepoint(x3,y3):
                                        map[x3,y3].clear()
                                        map[x3,y3].add(self.floorFunc(room1))
                            return
                    return

    def __sign(self, x):
        if x > 0:
            return 1
        if x < 0:
            return -1
        return 0
    
    def __neighbors(self, (x,y)):
        yield x+1, y
        yield x-1, y
        yield x, y+1
        yield x, y-1
        yield x+1, y+1
        yield x+1, y-1
        yield x-1, y+1
        yield x-1, y-1

    def connectDistant(self, map, room1, room2, allRooms, digger):
        #parole.debug('Connecting distant rooms: %r, %r', room1, room2)
        p1 = room1.diggableOut()
        p2 = room2.diggableIn()
    
        ntries = 100
        while ntries:
            ntries -= 1
            startPos = random.choice(p1)
            endPos = random.choice(p2)
            dPos = (self.__sign(endPos[0]-startPos[0]),
                    self.__sign(endPos[1]-startPos[1]))
            if room1.rect.collidepoint(startPos[0] + dPos[0], 
                                       startPos[1] + dPos[1]):
                continue
            else:
                break

        if not ntries:
            return
    
        x, y = startPos
        try:
            digger.digTile(map, map[x,y], room1, room2, allRooms)
        except IndexError:
            return

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
    
            try:
                if not digger.digTile(map, map[nx,ny], room1, room2, allRooms):
                    break
            except IndexError:
                return

            x, y = nx, ny
            if x == endPos[0] and y != endPos[1]:
                movingX = False
            elif x != endPos[0] and y == endPos[1]:
                movingX = True

#==============================================================================
#{ Utility functions

def bresenhamPoints((x0, y0), (x1, y1)):
    """
    Generator yielding the sequence of integer points on the line segment from
    C{(x0,y0)} to C{(x1,y1)} as traced by the Bresenham algorithm.
    """
    # Basically lifted right from Wikipedia.
    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        # swap(x0,y0)
        t = x0; x0 = y0; y0 = t

        #swap(x1,y1)
        t = x1; x1 = y1; y1 = t
    if x0 > x1:
        # swap(x0,x1)
        t = x0; x0 = x1; x1 = t

        # swap(y0,y1)
        t = y0; y0 = y1; y1 = t
    deltax = x1 - x0
    deltay = abs(y1 - y0)
    error = deltax / 2
    y = y0
    ystep = (y0 < y1) and 1 or -1
    for x in xrange(x0, x1+1):
        if steep:
            yield (y,x)
        else:
            yield (x,y)
        error -= deltay
        if error < 0:
            y += ystep
            error += deltax

#==============================================================================

def objectBlocksLOS(obj):
    return obj.blocksLOS

