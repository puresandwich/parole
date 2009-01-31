#Parole Artful Roguelike Engine
#Copyright (C) 2006 Max Bane
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
Input module pydocs.
"""

import pygame, parole, logging, config

__keypresses = []

__downUpListeners = []

#==============================================================================
def __onConfigChange(conf):
        r = int(conf.input.repeat)
        if r != 0:
            pygame.key.set_repeat(r, r)
        else:
            pygame.key.set_repeat()
        logging.info('Keyboard repeat delay: %sms', r)

        logging.info('Use shiftmap: %s', conf.input.useShiftmap)
        logging.info('Shiftmap: %s', conf.input.shiftmap.name)
        
def init():
    """
    init() -> None
    
    Initializes the input module. Automatically called during engine startup -
    most user code shouldn't need this function.
    """
    
        
    parole.conf.notify(__onConfigChange, True)

    # push the ui event handler for the input module
    #parole.pushUIEventHandler(handleKeyDown)
    
def unload():
    parole.conf.notify(__onConfigChange, False)

#==============================================================================

def listenKeysDownUp(listener):
    if listener not in __downUpListeners:
        __downUpListeners.append(listener)

def unlistenKeysDownUp(listener):
    if listener in __downUpListeners:
        __downUpListeners.remove(listener)
    
#==============================================================================

def keyRepr(key, mod):
    """
    Returns a nicely stringified representation of a keypress, possibly
    shiftmapped, depending on config.
    """
    str = pygame.key.name(key)
    shift = ''
    ctrl, alt = (mod & pygame.KMOD_CTRL) and 'ctrl ' or '', \
                (mod & pygame.KMOD_ALT) and 'alt ' or ''
    
    if mod & pygame.KMOD_SHIFT:
        if parole.conf.input.useShiftmap and len(str) == 1 and str.isalpha():
            str = str.upper()
        elif parole.conf.input.useShiftmap and str in parole.conf.input.shiftmap:
            str = parole.conf.input.shiftmap[str]
        else:
            shift = 'shift '
            
    result = '%s%s%s%s' % (ctrl, alt, shift, str)
    return result

#==============================================================================

def handleKeyDown(event):
    """
    handleKeyDown(event) -> None
    
    Instructs the input module to handle a PyGame keypress event. This is
    automatically invoked by the engine. Most user code shouldn't need to call
    this function unless it wants to artificially inject keypresses (for a
    game replay, perhaps?), in which case it should be careful to ensure that
    the given event is well formed according to PyGame convention.
    """
    if event.type != pygame.KEYDOWN:
        return
    key, mod = event.key, event.mod
    
    # ignore lone modifier keypresses
    if key in [pygame.K_LALT, pygame.K_RALT, pygame.K_LCTRL, 
               pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT,
               pygame.K_LMETA, pygame.K_RMETA]:
        return
    
    # append a nicely stringified representation of this keypress to the list
    result = keyRepr(key, mod)
    __keypresses.append(result)
    logging.debug('Key down: %s. Queue: %s', result, __keypresses)

    # notify any listeners of a keydown event
    for listener in __downUpListeners:
        listener.handleKeyDown(result)

#==============================================================================

def handleKeyUp(event):
    """
    handleyKeyUp(event) -> None

    Instructs the input module to handle a PyGame key release event. This is
    automatically invoked by the engine. Most user code shouldn't need to call
    this function unless it wants to artificially inject key releases, in
    which case it should be careful to ensure that the given event is well
    formed according to PyGame convention.
    """
    if event.type != pygame.KEYUP:
        return
    key, mod = event.key, event.mod
    
    # ignore lone modifier keypresses
    if key in [pygame.K_LALT, pygame.K_RALT, pygame.K_LCTRL, 
               pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT,
               pygame.K_LMETA, pygame.K_RMETA]:
        return
    
    result = keyRepr(key, mod)

    logging.debug('Key up: %s', result)

    # notify any listeners of a keyup event
    for listener in __downUpListeners:
        listener.handleKeyUp(result)

#==============================================================================

def getKeyPresses():
    """
    getKeyPresses -> [str1, str2, ...]
    
    Returns a list of keypresses which have occurred since the last time 
    getKeyPresses was called. The members of the list are strings of the format
    '[ctrl] [alt] [shift] keyname', possibly shift-mapped (so that, for example,
    'shift e' comes out as 'E') according to the current config. Keynames
    enclosed in square brackets represent numpad keypresses (e.g., [7] = 
    number pad 7).
    """
    global __keypresses
    #parole.debug('getKeyPresses()')
    k = __keypresses
    __keypresses = []
    return k

#==============================================================================

def peekKeyPresses():
    """
    peekKeyPresses -> [str1, str2, ...]
    
    Returns a list of keypresses which have occurred since the last time 
    getKeyPresses() was called. This differs from getKeyPresses() in that it
    does not clear the buffer of key presses.
    """
    return list(__keypresses)

#==============================================================================

def setKeyPresses(presses):
    global __keypresses
    __keypresses = list(presses)

#==============================================================================

def clearKeyPresses():
    """
    clearKeyPresses() -> None
    
    Causes the input module to disregard any keypresses which have occurred
    since the last time getKeyPresses() was called.
    """
    global __keypresses
    logging.debug('clearKeyPresses()')
    __keypresses = []

#==============================================================================

# A useful ui event handler
class CommandMap:
    def __init__(self, confMap, handler, peek=False):
        self.map = confMap
        self.handler = handler
        self.peek = peek
        
    def __call__(self, event):
        # we are a ui event handler
        if event.type == pygame.QUIT:
            try:
                command = self.map.system.QUIT
            except AttributeError:
                return
            parole.debug('CommandMap: %s', command)
            self.handler(command)
        else:
            keys = self.peek and peekKeyPresses() or getKeyPresses()
            for keypress in keys:
                try:
                    command = self.map.keypresses[keypress]
                except (AttributeError, KeyError):
                    continue
                parole.debug('CommandMap: %s', command)
                self.handler(command)

#==============================================================================

class ReadLine:
    def __init__(self, onNewline, onInput=None, text=None, cursorPos=0):
        self.text = text or ''
        self.cursorPos = cursorPos
        self.onNewline = onNewline
        self.onInput = onInput

        self.numpad = ['[1]', '[2]', '[3]', '[4]', '[5]', '[6]', '[7]',
                    '[8]', '[9]', '[0]', '[.]', '[/]', '[*]', '[+]', '[-]']

    def notify(self):
        if self.onInput:
            self.onInput(self)

    def reset(self):
        self.cursorPos = 0
        self.text = ''
        self.notify()

    def __call__(self, event):
        for keypress in getKeyPresses():
            if keypress in ['return', 'enter']:
                #self.text += '\n'
                self.onNewline(self)
                return

            if keypress == 'tab':
                self.text = self.text[:self.cursorPos] + '\t' + \
                    self.text[self.cursorPos:]
                self.cursorPos += 1

            elif keypress == 'left':
                self.cursorPos = max((0, self.cursorPos-1))

            elif keypress == 'right':
                self.cursorPos = min((len(self.text), self.cursorPos+1))

            elif keypress == 'home':
                self.cursorPos = 0

            elif keypress == 'end':
                self.cursorPos = len(self.text)

            elif keypress == 'backspace' and self.cursorPos > 0:
                self.text = self.text[:self.cursorPos-1] + \
                    self.text[self.cursorPos:]
                self.cursorPos = max((0, self.cursorPos-1))

            elif keypress == 'delete' and self.cursorPos < len(self.text):
                self.text = self.text[:self.cursorPos] + \
                    self.text[self.cursorPos+1:]
                self.cursorPos = max((0, self.cursorPos))

            elif keypress == 'space':
                self.text = self.text[:self.cursorPos] + ' ' + \
                    self.text[self.cursorPos:]
                self.cursorPos += 1

            elif len(keypress) == 1:
                # Assuming shiftmapping is on, this should be a printable
                # character
                self.text = self.text[:self.cursorPos] + keypress + \
                    self.text[self.cursorPos:]
                self.cursorPos += 1

            elif keypress in self.numpad:
                self.text = self.text[:self.cursorPos] + keypress[1] + \
                    self.text[self.cursorPos:]
                self.cursorPos += 1

            else:
                continue

            self.notify()
