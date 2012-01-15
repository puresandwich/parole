#Parole Advanced Roguelike Engine
#Copyright (C) 2006-2012 Max Bane
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
A small framework for discrete, event-driven simulations. Currently
unimplemented.
@todo 0.6.0: Will be implemented for version 0.6.0.
"""

import logging
import parole, config

#==============================================================================

def init():
    """
    Initializes the C{sim} module. Automatically called during engine startup -
    most user code shouldn't need this function.
    """
    def onConfChange(key, val):
        pass

    config.conf.notify(onConfChange, True)

#==============================================================================
