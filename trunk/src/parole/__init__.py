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
Parole is the Python Advanced Roguelike Engine, a framework in 
U{Python<http://www.python.org>} for use with U{PyGame<http://www.pygame.org>}
to create graphical, discrete event, agent-based simulations in the 
U{Roguelike<http://roguebasin.roguelikedevelopment.org>} genre.

Introduction
============
TODO.

Modules
=======

L{parole.base}
--------------
TODO.

@author: Max Bane
@contact: C{max.bane@gmail.com}
@newfield web: Website, Websites
@web: Project home: U{http://parole.googlecode.com}
@web: Online API Docs: U{http://maxbane.com/parole_api} [TODO]
@copyright: Copyright 2006-2009 Max Bane.

@license:
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version. Distribution
of software written to use this program need not necessarily be
governed by the same license. 

"""

from parole.base import *
import parole.config
import parole.input
import parole.display
import parole.resource
import parole.shader
from parole.shader import Shader, Pass
import parole.sim
import parole.map
import parole.fov

__version__ = versionStr

# Clean up namespace
#del parole, base
# Keep base, otherwise pydocs get screwed up
del parole
