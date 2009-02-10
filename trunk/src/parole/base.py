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
Provides the core functionality of the engine. This includes facilities for
loading other engine modules, reading and applying engine configurations, and
for starting and stopping the main game loop, which performs the rendering and
event-handling of each frame, and invokes a user callback implementing the
game's frame-by-frame logic.

Note that everything contained in the L{base} module is automatically imported
into the top-level namespace of the L{parole} package, so, for instance, user
code can simply call C{parole.startup(...)} rather than
C{parole.base.startup(...)}.  
"""

import logging, sys
import config
import parole 

# Version info
developmentVersion = True
"""
True if this is not a released branch version of Parole.
"""

version = (0, 5, 0) # (major, minor, revision)
"""
The version number of this installation of Parole, expressed as a tuple of the
C{(major, minor, revision)} integers.
"""

versionStr = '%s.%s.%s%s' % (version[0], version[1], version[2],
        developmentVersion and 'dev' or '')
"""
A human readable version string derived from L{version} and
L{developmentVersion}.
"""

# Set up the root logger
logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s [%(module)-10s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S', filename="full.log")

# The engine-wide configuration object
conf = None
"""
The engine-wide configuration object, instantiated by L{startup} upon reading
the configuration file passed to it.
"""

__paroleShutdown = False
__logFrameTime = False
__printFrameTime = False

#==============================================================================
#{ Utilities

# Engine log output functions, one for each log level.
debug = logging.debug
info = logging.info
warn = logging.warn
error = logging.error
# unfortunately these don't show up in epydoc this way

#def debug(*args, **kwargs):
#    """
#    Logs a message at level C{DEBUG}. Arguments work exactly as they do for the
#    standard library's C{logging.debug}.
#    """
#    logging.debug(*args, **kwargs)
#def info(*args, **kwargs):
#    """
#    Logs a message at level C{INFO}. Arguments work exactly as they do for the
#    standard library's C{logging.info}.
#    """
#    logging.info(*args, **kwargs)
#def warn(*args, **kwargs):
#    """
#    Logs a message at level C{WARN}. Arguments work exactly as they do for the
#    standard library's C{logging.warn}.
#    """
#    logging.warn(*args, **kwargs)
#def error(*args, **kwargs):
#    """
#    Logs a message at level C{ERROR}. Arguments work exactly as they do for the
#    standard library's C{logging.error}.
#    """
#    logging.error(*args, **kwargs)

#==============================================================================

havePyGame = False
"""
C{True} if pygame was successfully imported; if C{False}, engine startup will
fail.
"""

try:
    import pygame
    havePyGame = True
except:
    warn('PyGame unavailable. Engine will fail to start.')

#==============================================================================

def time():
    """
    Returns the time in milliseconds since Parole startup. If L{startup} has
    not yet been called, this always returns 0.
    """

    return pygame.time.get_ticks()

#==============================================================================
    
class ParoleError(Exception):
    """
    Base class for Parole-related exceptions.
    """

    def __init__(self, *args):
        Exception.__init__(self, *args)
        
#==============================================================================
# Some useful decorators

def Property(function):
    """
    A decorator for turning methods into properties (attributes whose 
    set/get/del behaviors are programmatic). To be used thus::

        class SomeClass:
            @parole.Property
            def someProperty():
                def fget(self):
                    print 'getting!'
                    return 'castlevaniaRL'
                    
                def fset(self, val):
                    print 'setting!'
                    
                def fdel(self):
                    print 'deleting!'
                    
        obj = SomeClass()
        obj.someProperty = 42
        print 'playing ' + obj.someProperty
        del obj.someProperty
        
    which would produce::
        
        setting!
        getting!
        playing castlevaniaRL
        deleting!
    """
    keys = 'fget', 'fset', 'fdel'
    func_locals = {'doc':function.__doc__}
    
    def probeFunc(frame, event, arg):
        if event == 'return':
            locals = frame.f_locals
            func_locals.update(dict((k,locals.get(k)) for k in keys))
            sys.settrace(None)
        return probeFunc
    
    sys.settrace(probeFunc)
    function()
    return property(**func_locals)
        
#==============================================================================

class NotifyingConfig(config.Config):
    '''
    A C{Config} object as in L{parole.config}, with the additional ability to 
    register listeners for changes to the state of the configuration.
    '''
    def notify(self, func, add=True):
        '''
        Registers or unregisters a function to be invoked when the config
        changes. If registering, the function will be called immediately,
        and then at any subsequent time that this C{NotifyingConfig}'s C{changed}
        method is invoked.
        
        @param func: The function to register or unregister. Should accept this
                     C{NotifyingConfig} object as its first unnamed argument.
        @param add: Whether to register the function (C{add=True}), or unregister
                    it (C{add=False}).
        '''
        try:
            catlick = len(self.listeners)
        except AttributeError:
            self.listeners = []
            
        if add:
            self.listeners.append(func)
            func(self)
        else:
            self.listeners.remove(func)
            
    def changed(self):
        '''
        Calls all registered listener functions with this C{NotifyingConfig} 
        object as the single parameter.
        '''
        try:
            catlick = len(self.listeners)
        except AttributeError:
            self.listeners = []
            
        for func in self.listeners:
            func(self)

    touch = changed

#==============================================================================

GeneralUpdateEvent = pygame.USEREVENT

#==============================================================================
#{ Engine Startup and Shutdown

allModules = ['display', 'input', 'resource', 'shader', 'console', 'map']
"""
A list of the names of all engine modules that are available. The list of 
requested modules passed to L{startup} must contain only names present in this.
"""

haveModule = dict(zip(allModules, (False,)*len(allModules)))
"""
A dictionary from module names to C{bool}s, indicating which modules were
requested and intitialized on engine startup.
"""

def startup(configFile, updateFunc, caption='Parole', icon=None,
        modules=allModules, gen=False):
    """
    Starts continuous execution of the Parole engine. 
    
    @param configFile: 
    the path to the configuration file to use (see the L{parole} package
    documentation for a description of the config file format). 

    @type configFile: C{str}
    
    @param caption: 
    the string that will appear as the title of the window used for parole's
    display. C{'Parole'} is the default. 

    @type caption: C{str}

    @param modules: 
    a list of parole submodules which the user intends to use. It defaults to
    the global L{allModules}, which requests all submodules to be available. Upon
    startup, the engine intializes each requested submodule.  An exception will
    be raised if C{configFile} tries to configure a module not requested in
    C{modules}, and engine behavior is undefined if any user code attempts to use
    an uninitialized module. After startup,  the global L{haveModule} dictionary
    indicates which submodules have been intialized.

    @type modules: C{list} of C{str}s

    @param updateFunc:
    After initializing requested submodules, the engine enters its main frame
    loop, which processes events, updates the display and other submodules, and
    invokes the user-supplied C{updateFunc} once per frame.  The implementation
    of updateFunc is the entry point for user code in the engine, and is where
    all application-specific behavior originates.  
    
    C{updateFunc} can be supplied in one of three ways:
        1. C{updateFunc} is a python callable object (with no required
           arguments); it will be called once each frame.

        2. C{updateFunc} is a string that names a script resource (see
           L{parole.resource}) which defines a callable object C{updateFunc} in
           its global namespace (again, with no required arguments). This object
           will be called each frame. The resource submodule must be requested. 

        3. C{updateFunc} is a generator object. Each frame, the engine will step
           once through it (i.e., call its C{next()} method), rather than
           calling it as a function. The engine pays no attention to the values,
           if any, yielded by the generator. If the generator is ever exhausted
           (raises C{StopIteration}), the engine will log a warning and proceed
           to shut down.
    """

    global __paroleShutdown
    info('Parole %s startup', versionStr)

    # Make sure we have PyGame
    if not havePyGame:
        error('Unable to start Parole without PyGame!')
        info('Parole shutting down.')
        return

    # Try to start psyco
    try:
        import psyco
        psyco.full()
        info('Psyco initialized.')
    except:
        info('Psyco unavailable.')

    info('Requested modules: %s', ', '.join(modules))
    # Notify user of any strangeness in requested modules
    for m in modules:
        if m not in allModules:
            warn('Unknown module requested: %s', m)

    # Game loop will continue until this is true
    __paroleShutdown = False

    # Make sure the stack of ui event handlers is cleared
    del uiEventHandlers[:]
    
    info('Reading config: %s...', configFile)
    try:
        f = open(configFile, 'r')
    except Exception, e:
        error('Failed to read configuration from %r: %s', configFile, e)
        warn('Falling back on default configuration.')
        try:
            import pkg_resources
        except:
            panic('Unable to fall back on default config: no pkg_resources')
            f = pkg_resources.resource_stream(__name__, 'data/default.cfg')
    parole.conf = NotifyingConfig(f)
    f.close()
    
    parole.conf.notify(__onConfigChange, True)
    
    info('Base up')
    
    # Init PyGame
    sdlver = pygame.get_sdl_version()
    info('Using PyGame %s on SDL %s.%s.%s', pygame.version.ver, sdlver[0],
        sdlver[1], sdlver[2])
    numUp, numFail = pygame.init()
    if numFail > 0:
        warn('%s PyGame modules failed to init', numFail)
    info('PyGame up')
    
    # Init resource management
    if 'resource' in modules:
        import resource
        resource.init()
        haveModule['resource'] = True
        info('Resource management up')
    else:
        warn('No resource management')

    # Init the display
    if 'display' in modules:
        import display
        display.init()
        pygame.display.set_caption(caption)
        haveModule['display'] = True
        info('Display up')
    else:
        warn('No display')

    # Set the window icon 
    if 'resource' in modules and icon:
        iconSurf = resource.getTexture(icon)
        if iconSurf:
            pygame.display.set_icon(iconSurf)
        else:
            error('Requested icon %r unavailable.', icon)

    # Init the shader module
    if 'shader' in modules:
        import shader
        import splash
        shader.init()
        haveModule['shader'] = True
        info('Shaders up')
    else:
        warn('No shaders')
    
    # Init the input module
    if 'input' in modules:
        import input
        input.init()
        haveModule['input'] = True
        info('Input module up')
    else:
        warn('No input')

    # Init the console module
    if 'console' in modules:
        import console
        console.init()
        haveModule['console'] = True
        info('Console up')
    else:
        warn('No console')
        
    # Init the map module
    if 'map' in modules:
        import map
        parole.map.init()
        haveModule['map'] = True
        info('Map module up')
    else:
        warn('No map module')

    # Give all loaded modules a chance to incorporate current config settings
    #parole.conf.changed()

    # Retrieve updateFunc if it names a script resource
    if type(updateFunc) is str:
        updateFuncObj = resource.getObject(updateFunc, 'updateFunc')
        if not updateFuncObj:
            panic("Couldn't load updateFunc from \"%s\"!" % (updateFunc,))
    else:
        updateFuncObj = updateFunc

    if not callable(updateFuncObj):
        panic("updateFunc is not callable!")

    # did the user give us a functor or a generator?
    updateGen = None
    if gen:
        updateGen = updateFuncObj()

    # Init done
    info('Parole ready. Entering main loop.')

    #if not len(uiEventHandlers):
    #    warn('There is no handler to receive ui events.')
    
    # Main Engine loop
    while not __paroleShutdown:
        pygame.event.pump()

        try:
            # Update the display for this frame
            if haveModule['display']:
                t = time()
                display.update()
                t = time() - t
                if parole.conf.general.logFrameTime:
                    debug('Display update time: %sms', t)
                if parole.conf.general.printFrameTime:
                    sys.stderr.write('Display update time: %sms\n' % t)
                    sys.stderr.flush()

                # Show the splash screen/animation on engine startup
                if haveModule['shader'] and haveModule['resource'] and \
                        parole.conf.general.engineSplash:
                    if not splash.doneSplash:
                        if not splash.splash:
                            splash.doSplash()
                        continue

            # Get PyGame's events for this frame. If __continuousUpdates is
            # non-zero, then we have some animations running and need to
            # immediately grab events with pygame.event.get, otherwise we can
            # afford to free up some CPU time by blocking with
            # pygame.event.wait.
            if __continuousUpdates > 0:
                #parole.debug('Continuous updates: %s', __continuousUpdates)
                events = pygame.event.get()
            else:
                events = [pygame.event.wait()]

            # Give the input module a chance to queue any input events
            if haveModule['input']:
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        parole.input.handleKeyDown(event)
                    elif event.type == pygame.KEYUP:
                        parole.input.handleKeyUp(event)

            # The console might want to respond to key presses before anything
            # else
            if haveModule['console']:
                console.update()
            
            # The user's update function. Called each frame.    
            if updateGen:
                try:
                    updateGen.next()
                except StopIteration:
                    warn("User frame code has been exhausted.")
                    updateGen = None
            else:
                updateFuncObj()

            # Give the UI event handlers a chance to handle stuff
            for event in events:
                if len(uiEventHandlers):
                    handler = uiEventHandlers[-1]
                    if callable(handler):
                        handler(event)
                    else:
                        for h in handler:
                            #parole.debug('Sending event "%s" to %s', event, h)
                            h(event)
                    
        except ParoleShutdown:
            __paroleShutdown = True
            
    info('Parole shutting down.')
    
    if 'resource' in modules:
        resource.clearAll()
    
    # TODO: Save changes to configuration
    #config.writeOut(configFile)
    parole.conf.notify(__onConfigChange, False)
    __unloadModules(modules)
    
    # We don't need to call pygame.quit(), since that will be taken care of
    # automatically when the process exits. Also, this way we can restart
    # the engine in the same process, if desired.
    info('Goodbye.\n*********************\n')

#==============================================================================

class ParoleShutdown(ParoleError):
    """
    Raise this exception from game-code (i.e., from within or below the update
    function passed to C{parole.startup}) to cause Parole to shutdown gracefully
    at its earliest opportunity.
    """

    def __init__(self):
        ParoleError.__init__(self, "Parole shutdown requested")

#==============================================================================
    
def shutdown():
    """
    Causes Parole to shut down gracefully at its earliest opportunity. User code
    should generally raise a L{ParoleShutdown} exception from within its update
    function instead. C{shutdown()} is available in case Parole needs to be told
    to shut down from someplace outside the frame update.
    """

    global __paroleShutdown
    __paroleShutdown = True
    
#==============================================================================

def panic(msg):
    """
    Prints the given message to standard output, logs it at level C{CRITICAL},
    then instructs the current process to exit (by raising a C{SystemExit}
    exception). Does not give Parole a chance to shutdown properly.
    
    @param msg: The message string to print and log before ending the process.
    """

    print msg
    logging.critical("\n********************\n%s\n********************",
            str(msg))
    info('PANIC - Goodbye!')
    raise SystemExit

#==============================================================================
#{ User Interface

__continuousUpdates = 0

def pushAnimation():
    """
    Call this function to inform Parole that you are beginning an activity
    that requires continuous frame updates. As a matter of convenience, such
    activities are referred to as "animations", but they don't necessarily
    have to animate anything. Call C{popAnimation} when the animation is done.
    """
    global __continuousUpdates
    __continuousUpdates += 1
    parole.debug('Pushing animation; continuousUpdates = %s',
            __continuousUpdates)

def popAnimation():
    """
    Call this function to inform Parole that an animation has finished and no
    longer needs continuous frame updates. Once all animations have been
    popped, parole will wait for input before updating each frame, rather than
    updating continuously. This significantly reduces CPU overhead.  
    """
    global __continuousUpdates 
    __continuousUpdates = max(0, __continuousUpdates - 1)
    pygame.event.post(pygame.event.Event(GeneralUpdateEvent, {}))
    parole.debug('Popping animation; continuousUpdates = %s',
            __continuousUpdates)

#==============================================================================

uiEventHandlers = []
"""
The stack of user interface event handlers, represented as a list, with the last
element being the top of the stack.
"""

def pushUIEventHandler(handler):
    """
    Pushes a user interface event handler onto the stack of handlers. The stack
    is maintained by the engine, and may only contain callable objects that
    accept one argument. Each frame, the engine calls the object (or objects;
    see below) at the top of the stack, passing it any PyGame event that was
    received that frame. A stack is used in order to easily accomodate the
    common case where "layers" of interfaces may be present, the topmost one
    overriding those beneath it until it is removed; for example, an inventory
    screen temporarily appearing over, and superceding the keypress-handling of,
    the main gameplay screen.

    @param handler: 
    May be specified in one of two ways:
        1. A simple C{callable} object to be invoked with a PyGame event object
           as its argument. It will become the topmost, and only active UI event
           handling function.
        2. A tuple of C{callable} objects, each accepting a single PyGame event
           object as an argument. These will become the I{simultaneously}
           topmost, active UI event handling functions; each of them will
           receive the same event object per frame, in the order in which they
           are contained in the tuple.

    @type handler: C{callable} or C{tuple} of C{callable}s
    """
    debug('Pushing ui event handler: %s', handler)
    uiEventHandlers.append(handler)

#==============================================================================

def popUIEventHandler():
    """
    Removes the topmost user interface event handler from the stack of handlers
    and returns it. The handler immediately below it on the stack will become
    active. If there is no other handler on the stack, a warning will be logged,
    and the program will cease to respond to any user input
    """
    handler = uiEventHandlers.pop()
    debug('Popped ui event handler: %s', handler)
    if len(uiEventHandlers):
        debug('Current ui event handler: %s', uiEventHandlers[-1])
    else:
        warn('There are no more ui event handlers')
    return handler

#==============================================================================

__logLevels = \
{
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'error': logging.ERROR
}

def __onConfigChange(conf):
    global __logFrameTime, __printFrameTime
    val = parole.conf.general.loglevel
    try:
        logging.root.setLevel(__logLevels[val])
        info('Log level: %s', val)
    except KeyError:
        error('Bad loglevel requested: %s', val)

    __logFrameTime = int(parole.conf.general.logFrameTime)
    __printFrameTime = int(parole.conf.general.printFrameTime)
    info('logFrameTime: %s', __logFrameTime)
    info('printFrameTime: %s', __printFrameTime)
    info('engineSplash: %s', parole.conf.general.engineSplash)
            
def __unloadModules(modules):
    # give modules a chance to clean up, unregister for events, config
    # notifications, etc.
    parole.info('Unloading modules: %s', ', '.join(modules))
    if 'resource' in modules:   
        parole.resource.unload()
    if 'input' in modules:      
        parole.input.unload()
    if 'display' in modules:    
        parole.display.unload()
    if 'shader' in modules:     
        parole.shader.unload()
    if 'console' in modules:    
        parole.console.unload()
    if 'map' in modules:
        parole.map.unload()
    
