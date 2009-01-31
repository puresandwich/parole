#Python Agentive Roguelike Engine (Parole)
#Copyright (C) 2007 Max Bane
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

from decorator import decorator
import parole
import traceback, sys

firstUpdate = True
failed = {}

#@decorator
#def test(updateFunc):
#    global firstUpdate
#    firstUpdate = True
#    parole.startup('test.cfg', updateFunc, updateFunc.__name__)
    
def test(cfg='test.cfg'):
    @decorator
    def startTest(updateFunc):
        global firstUpdate
        firstUpdate = True
        parole.startup(cfg, updateFunc, updateFunc.__name__)
        
    return startTest
    
def runTests(tests):
    for t in tests:
        failed[t] = False
        print '----------\nTest %s\n----------' % (t.__name__)
        try:
            t()
        except Exception, e:
            traceback.print_exception(e.__class__, e, sys.exc_traceback)
            print 'Test "%s" failed.' % (t.__name__,)
            failed[t] = True
            continue
        print 'Test "%s" passed.' % (t.__name__,)

def summary(tests=None):
    print '\nSummary'
    print 'Pass | Fail | Test'
    for t in (tests and tests or failed.keys()):
        if failed[t]:
            print '[ ]  | [X]  |', t.__name__
        else:
            print '[X]  | [ ]  |', t.__name__
            
