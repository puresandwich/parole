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
Implements perlin noise. Provides a line-for-line Python transcription of Kevin
Perlin's reference implementation (Java) of improved Perlin noise.
"""
import math

def noise(x, y, z):
    """
    Returns the perlin noise at the given floating point coordinates.
    """
    # Find unit cube that contains point
    X = int(x) & 255
    Y = int(y) & 255
    Z = int(z) & 255
    
    # Find relative x,y,z of point in cube
    x -= math.floor(x)
    y -= math.floor(y)
    z -= math.floor(z)

    # Compute fade curves for each of x,y,z
    u = __fade(x)
    v = __fade(y)
    w = __fade(z)

    # Hash coordinates of the 8 cube corners...
    A, B = __p[X]+Y, __p[X+1]+Y
    AA, AB = __p[A]+Z, __p[A+1]+Z
    BA, BB = __p[B]+Z, __p[B+1]+Z

    # ... and add blended results from 8 corners of cube
    return __lerp(w, __lerp(v, __lerp(u, __grad(__p[AA  ], x  , y  , z   ),
                                         __grad(__p[BA  ], x-1, y  , z   )),
                               __lerp(u, __grad(__p[AB  ], x  , y-1, z   ),
                                         __grad(__p[BB  ], x-1, y-1, z   ))),
                     __lerp(v, __lerp(u, __grad(__p[AA+1], x  , y  , z-1 ), 
                                         __grad(__p[BA+1], x-1, y  , z-1 )),
                               __lerp(u, __grad(__p[AB+1], x  , y-1, z-1 ),
                                         __grad(__p[BB+1], x-1, y-1, z-1 ))))

def __fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def __lerp(t, a, b):
    return a + t * (b - a)

def __grad(hash, x, y, z):
    # Conver low 4 bits of hash code into 12 gradient directions
    h = hash & 15
    u = h < 8 and x or y
    v = h < 4 and y or ((h==12 or h==14) and x or z)
    return ((h&1) == 0 and u or -u) + ((h&2) == 0 and v or -v)

__p = range(512)
__permutation = [ 151,160,137,91,90,15,
   131,13,201,95,96,53,194,233,7,225,140,36,103,30,69,142,8,99,37,240,21,10,23,
   190, 6,148,247,120,234,75,0,26,197,62,94,252,219,203,117,35,11,32,57,177,33,
   88,237,149,56,87,174,20,125,136,171,168, 68,175,74,165,71,134,139,48,27,166,
   77,146,158,231,83,111,229,122,60,211,133,230,220,105,92,41,55,46,245,40,244,
   102,143,54, 65,25,63,161, 1,216,80,73,209,76,132,187,208, 89,18,169,200,196,
   135,130,116,188,159,86,164,100,109,198,173,186, 3,64,52,217,226,250,124,123,
   5,202,38,147,118,126,255,82,85,212,207,206,59,227,47,16,58,17,182,189,28,42,
   223,183,170,213,119,248,152, 2,44,154,163, 70,221,153,101,155,167, 43,172,9,
   129,22,39,253, 19,98,108,110,79,113,224,232,178,185, 112,104,218,246,97,228,
   251,34,242,193,238,210,144,12,191,179,162,241, 81,51,145,235,249,14,239,107,
   49,192,214, 31,181,199,106,157,184, 84,204,176,115,121,50,45,127, 4,150,254,
   138,236,205,93,222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180
   ]

for i in xrange(256):
    __p[i] =  __p[256+i] = __permutation[i]

