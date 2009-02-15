#Parole Advanced Roguelike Engine
#Copyright (C) 200-2009 Max Bane
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
Provides an in-game interactive python interpreter. Simply request the
C{"console"} module on engine startup, and your users will be able to press the
console key (C{"~"} by default; controlled by the C{console.consoleKey}
configuration variable) at any time to call up the console. Once active, it will
handle all input, providing an interactive python interpreter with a command
history and scrollable text display.

The interpreter runs with the C{console} module's C{globals()} as its namespace.
The C{parole} package will be available for interactive use automatically, and
you may expose your own objects to the intepreter via L{parole.console.interpreter},
which is an instance of the standard library C{code.InteractiveConsole} class.
"""

import code, sys, traceback, logging, cStringIO
import parole, config, input, resource, shader, display

#==============================================================================

consoleKey = '~'
"""
The key that the engine listens for to show/hide the console. Updated by changes
to C{parole.conf.console.consoleKey}.
"""

frame = None
"""
The L{Frame} shader responsible for displaying the console.
"""

stdout = None
"""
The console will redirect C{sys.stdout} to itself; this module variable will be
set to refer to the original C{sys.stdout} object.
"""

interpreter = None
"""
The actual interpreter object, an instance of C{code.InteractiveConsole}.
"""

historyFile = 'console.hst'
"""
The console will keep a list of previously entered commands, so that the user
may quickly retrieve them. This variable names the file in which the console
should store this list, so that it persists across executions of the engine.
Updated automatically by C{parole.conf.console.historyFile}.
"""

history = None
"""
The actual history maintained by the console as a C{list} of C{string}s.
"""

historyPos = 0
"""
The current position in the L{history} list, used by the console as the user
cycles through previous commands.
"""

logFile = 'console.log'
"""
The console keeps a textual log of the interpreter's session; this variable
names the file where that log is written.
Updated automatically by C{parole.conf.console.logFile}.
"""

logHandler = None
"""
In addition to output from the interpreter, the console also writes all engine log
messages of level C{INFO} or higher to its text display; this variable will
refer to the object that handles these messages.
"""

#==============================================================================

def __onConfigChange(conf):
    global consoleKey, ps1, ps2, font, lowerbound, conShader, historyFile, \
        logFile

    parole.info('Console key: %s', conf.console.consoleKey)
    consoleKey = conf.console.consoleKey

    parole.info('Console PS1: "%s"', conf.console.ps1)
    if frame:
        frame.ps1 = conf.console.ps1

    parole.info('Console PS2: "%s"', conf.console.ps2)
    if frame:
        frame.ps2 = conf.console.ps2

    parole.info('Console history file: "%s"', conf.console.historyFile)
    historyFile = conf.console.historyFile

    parole.info('Console log file: "%s"', conf.console.logFile)
    logFile = conf.console.logFile

    # TODO: changing the console font

#==============================================================================

class ConsoleInterpreter(code.InteractiveConsole):
    """
    A subclass of the standard library's C{code.InteractiveConsole} that
    implements the interactive Python interpreter of Parole's console. This is
    basically just a thin wrapper around C{code.InteractiveConsole} that
    redirects its output to the active L{ConsoleFrame} instance (the
    L{parole.console.frame} variable). The currently executing file will
    appear as C{"<parole console>"} in stack traces, and the C{quit} hint
    string is replaced with something more appropriate to the Parole console.
    """
    def __init__(self):
        """
        Constructs a C{ConsoleInterpreter} instance. The current C{globals()}
        will be incorporated in the interactive interpreter.
        """
        code.InteractiveConsole.__init__(self, globals(), '<parole console>')
        self.runsource("quit = 'Use parole.shutdown() to quit.'")

    def raw_input(self, prompt):
        """
        Currently the C{raw_input} function is not supported within the Parole
        console; this always returns the empty string.

        @return: "" (empty string)
        """
        # not supported!
        parole.warn('Parole Interactive Console: raw_input() not supported!')
        return ''

    def write(self, bytes):
        """
        Simply writes the given byts to C{frame}, the current C{ConsoleFrame}
        instance, and flushes it. 
        """
        frame.write(bytes)
        frame.flush()

#==============================================================================

class ConsoleFrame(shader.Frame):
    """
    A L{Frame} shader for displaying the interactive console. It is also the
    writable object to which all console output is sent. An instance of this
    class is created (L{parole.console.frame}) on engine startup if the console
    module was requested.
    """

    def __init__(self, height, font, ps1, ps2):
        borders = (None,None,None, shader.HorizontalBevel((200,200,0),
            (128,128,0), (64,64,0), 1, 3, 1), None, None, None, None)

        shader.Frame.__init__(self, borders, alpha=255, name="ConsoleFrame")

        try:
            self.log = open(logFile, 'w')
        except:
            parole.warn('Unable to open console log file "%s" for writing.',
                    logFile)
            self.log = cStringIO.StringIO()

        try:
            self.histf = open(historyFile, 'a')
        except:
            parole.warn('Unable to open console history file "%s" for writing.',
                    logFile)
            self.histf = cStringIO.StringIO()

        self.ps1, self.ps2 = ps1, ps2
        self.__font = font

        screenWidth = display.getSurface().get_width()
        self.readLineBox = shader.ReadLineBox(font, screenWidth-5,
                prompt=self.ps1)
        self.scroll = shader.ScrollView((screenWidth, height - \
            self.readLineBox.height),
            vbar=shader.VerticalScrollbar((128,128,0), (64,64,0), 10),
            followY=True)
        self.textblock = shader.TextBlockPass(font, (255,255,255),
                wrap_width=screenWidth-20, ignoreMarkup=True)
        self.background = shader.ColorField((0,0,128,220), (screenWidth,
            height))

        self.addPass(self.background)
        self.scroll.addPass(self.textblock, pos=(5,0))
        self.addPass(self.scroll)

        self.addPass(self.readLineBox, pos=(5, height -
            self.readLineBox.height))

        self.active = False

        self.cmdMap = input.CommandMap(parole.conf.console.commands,
                self.handleCommand, peek=True)
        self.readLine = input.ReadLine(self.onNewline, 
                self.readLineBox.onInput)

    def write(self, bytes):
        self.textblock.write(bytes)
        self.log.write(bytes)

    def writelines(self, lines):
        self.textblock.writelines(lines)
        self.log.writelines(lines)

    def flush(self):
        self.textblock.flush()
        self.log.flush()

    def toggleActive(self):
        """
        Toggles whether the console is visible and accepting input.
        """
        if not self.active:
            display.scene.add(self)
            parole.pushUIEventHandler((self.cmdMap, self.readLine))
            self.active = True
            parole.info('Console activated.')
        else:
            display.scene.remove(self)
            parole.popUIEventHandler()
            self.active = False
            parole.info('Console deactivated.')

    def handleCommand(self, cmd):
        """
        Handles console interface commands that aren't text-input. Available
        commands are C{"scroll up"}, C{"scroll down"}, C{"previous"}, and
        C{"next"}. Their keybindings are controlled by the
        C{console.commands.keypresses} configuration variables.
        """
        global historyPos

        if cmd == "scroll up":
            ls = self.__font.get_linesize()
            self.scroll.scrollPixels(0, -(self.height / \
                ls-3)*ls)

        elif cmd == "scroll down":
            ls = self.__font.get_linesize()
            self.scroll.scrollPixels(0, (self.height / \
                ls-3)*ls)

        elif cmd == "previous" and history:
            historyPos = max((0, historyPos-1))   
            text = history[historyPos]
            self.readLine.text = text
            self.readLine.cursorPos = len(text)
            self.readLine.notify()

        elif cmd == "next" and history:
            historyPos = min((len(history), historyPos+1))
            if historyPos == len(history):
                self.readLine.reset()
            else:
                text = history[historyPos]
                self.readLine.text = text
                self.readLine.cursorPos = len(text)
                self.readLine.notify()

    def onNewline(self, readline):
        """
        Handles the user pressing enter in the readline box; reads the contents
        of the readline box and sends them to the interpreter.
        """
        global historyPos

        # append the line of input onto the command history
        if len(readline.text.strip()):
            history.append(readline.text)
            self.histf.write(readline.text + '\n')
            self.histf.flush()
            historyPos = len(history)

        # echo the line on the console
        self.write('%s%s\n' % (self.readLineBox.prompt, readline.text))
        self.flush()

        # send the line to the interpreter
        if interpreter.push(readline.text):
            self.readLineBox.prompt = self.ps2
        else:
            self.readLineBox.prompt = self.ps1

        # anything the interpreter wrote to its stdout should have been
        # written to the console. flush to make sure it shows up
        self.flush()

        # reset the input buffer
        readline.reset()


#==============================================================================

banner = \
"""
Parole %s 
Copyright (C) 2006-2009 Max Bane.

Python %s on %s
Type "help", "copyright", "credits" or "license" for more information.

This is an interactive Python interpreter. Use it wisely!
=========================================================

""" % (parole.versionStr, sys.version, sys.platform)

def __init():
    """
    Initializes the console module. Automatically called during engine 
    startup - user code shouldn't need to use this function.
    """
    global frame, stdout, stderr, logHandler, interpreter, history, historyPos
    
    parole.conf.notify(__onConfigChange, True)

    # Initialize the console command history
    history = []
    historyPos = 0

    # Create the console frame shader. 
    frame = ConsoleFrame(parole.conf.console.height,
            resource.getFont('fonts/monaco.ttf', 10), parole.conf.console.ps1,
            parole.conf.console.ps2)

    # Write the intro banner to the console
    frame.write(banner)
    frame.flush()

    # Start logging to the console (INFO level)
    parole.info('Begin logging to console...')
    logHandler = logging.StreamHandler(frame)
    logHandler.setLevel(logging.INFO)
    logHandler.setFormatter(logging.Formatter(\
        '%(levelname)s: %(message)s'))
    logging.getLogger().addHandler(logHandler)

    # Create the actual interpreter
    #stderr = sys.stderr
    #sys.stderr = frame
    stdout = sys.stdout
    sys.stdout = frame
    parole.info('Setting up console Python interpreter...')
    interpreter = ConsoleInterpreter()

    parole.info('Loading console history file...')
    try:
        hf = open(historyFile, 'r')
        history = [l[:len(l)-1] for l in hf.readlines() if len(l) > 1]
        historyPos = len(history)
        hf.close()
    except:
        parole.warn('Unable to open/load history file "%s".', historyFile)

    
def __unload():
    global history

    parole.conf.notify(__onConfigChange, False)

    if stdout:
        sys.stdout = stdout

#==============================================================================

#def addConfigOptions():
#    """
#    addConfigOptions() -> None
#    
#    Registers the console module's config options. Handled by the engine - most
#    user code shouldn't need to call this.
#    """
#    config.categories.append('console')
#    config.addOption('console.ps1', '>>> ', 'The console PS1')
#    config.addOption('console.ps2', '... ', 'The console PS2')
#    config.addOption('console.font', 'Courier', 'The console font')
#    config.addOption('console.fontsize', '12', 'The console font size',
#            config.validateInt)
#    config.addOption('console.fontbold', 'false', 'The console font size')
#    config.addOption('console.fontitalic', 'false', 'The console font size')
#    config.addOption('console.lowerbound', '320', 
#            "The y-coordinate of the console's lower bound when active",
#            config.validateInt)

#==============================================================================

def update():
    """
    Updates the state of the console. This is where the console gets the
    chance to listen for console activation key (C{"~"} by default; controlled
    by the C{console.consoleKey} configuration variable).  Automatically called
    by the engine each frame.
    """

    # If the console's not active, listen for the console key to activate it   
    peek = input.peekKeyPresses()
    if consoleKey in peek:
        peek.remove(consoleKey)
        input.setKeyPresses(peek)
        frame.toggleActive()

#==============================================================================

