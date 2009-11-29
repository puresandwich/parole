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
A resource management system vaguely inspired by that of the Quake 3 engine.

In this system, all of the resources needed by a game (art, sounds, video,
text, whatever) are collected together into "packages" which reside in the
game's "gamedir" (specified by config option C{general.gamedir}). Each package
is a directory or a Zip archive whose name must end with the suffix C{.res}
(by default; controlled by config option C{resource.packsuffix}).

Upon engine startup, all of the packages under the gamedir are identified and
scanned. Together, their contents constitute all of the resources that the
game has access to. An individual resource is identified by its name, which
corresponds to the actual path + filename of some file contained in one
of the packages, and can be retrieved with the L{getResource} function. If a
resource name is contained by more than one package, the alphabetically latest
package takes precedence. This allows one to easily patch a game's resources
by simply adding a package whose name comes alphabetically later than any 
existing ones - whatever resources it contains will effectively replace any
copies in previous packages.

The L{getResource} function caches the resources it returns, so that future
requests for the same resource will not result in an actual disk-read. If
a resource is no longer needed, its data can be cleared from the cache with
the L{clearResource} function. Note that if any user code still has references
to the data, it may not actually be freed from memory.

The resource module also provides a number of convenience functions, like
L{getTexture}, which both retrieves the bytes of the requested resource, and
attempts to turn those bytes into a useful PyGame C{Surface} object.

It is possible to disallow directory packages through the config option
C{resource.allowdirs}.
"""

import pygame, parole, logging, os, zipfile, cStringIO, shader, imp, sys

__resTable = {}


__gameDir = ''

packages = []

#==============================================================================

class __NotFound(Exception):
    pass

#==============================================================================

#def addConfigOptions():
#    """
#    addConfigOptions() -> None
#    
#    Registers the resource module's config options. Handled by the engine - most
#    user code shouldn't need to call this.
#    """
#    config.categories.append('resource')
#
#    config.addOption('resource.packsuffix', '.res',
#            'Suffix identifying resource packages', None)
#    config.addOption('resource.allowdirs', 'true', 
#            'Whether to allow resource packages that are just directories',
#            config.validateBool)

#==============================================================================

__inInit = False
def __onConfigChange(conf):
    global __gameDir
    parole.info('Resource package suffix: %s', conf.resource.packsuffix)
    if not __inInit:
        parole.warn('New package suffix will take effect on restart.')
    parole.info('Allowdirs: %s', conf.resource.allowdirs)
    if not __inInit:
        parole.warn('New resource.allowdirs will take effect on restart.')
    __gameDir = conf.resource.gamedir
    parole.info('Game directory: %s', __gameDir)

def __init():
    """
    Initializes the resource module. Detects and loads all resource pakcages 
    in the gamedir directory. Automatically called during engine 
    startup -- user code shouldn't need to use this function.
    """
    global __gameDir, __inInit
    __inInit = True
    __resTable.clear()

    parole.conf.notify(__onConfigChange, True)
    __gameDir = parole.conf.resource.gamedir

    # Score some packages
    while len(packages): packages.pop()
    suff = parole.conf.resource.packsuffix
    for root, dirs, files in os.walk(__gameDir):
        if root == __gameDir:
            if bool(parole.conf.resource.allowdirs):
                packages.extend([(dir, None, __getResourceFromDir) \
                        for dir in dirs if dir.endswith(suff)])
            for arch in files:
                if not arch.endswith(suff): continue
                if not zipfile.is_zipfile(os.sep.join([__gameDir, arch])):
                    parole.error('Ignoring bad archive resource package: %s: Not dir or zip.', 
                            arch)
                    continue
                #archf = None
                try:
                    archf = zipfile.ZipFile(os.sep.join([__gameDir, arch]), 'r')
                    parole.info('archf = %r', archf)
                except Exception, e:
                    parole.error('Ignoring bad archive resource package: %s: %s', 
                            arch, e)
                    continue
                packages.append((arch, archf, __getResourceFromArch))

    # sort packages - reversed alphabetic, because alphabetically later
    # packages take precedence/override
    packages.sort(lambda x, y: cmp(x[0], y[0]), reverse=True)
    #parole.info('Packages: %r', packages)

    parole.info('Resource packages: %s',
        ', '.join([pkgname + ((get==__getResourceFromArch) and ' (arch)' or ' (dir)') for (pkgname, f, get) in packages]))
    __inInit = False
    parole.info('Extended image loading available: %s', pygame.image.get_extended())
    
def __unload():
    parole.conf.notify(__onConfigChange, False)


#==============================================================================

def getPackages():
    """
    Returns a list of (pkgname, isArch) pairs for each loaded resource package,
    where isArch indicates whether the associated package is a zip archive or
    not (in which case, it's a directory). The packages are listed in the order
    that they are searched for resources: reverse alphabetic.

    @return: C{[(pkgname, isArch), ...]}
    """
    return [(pkgname, f is not None) for (pkgname, f, g) in packages]

#==============================================================================

def __getResourceFrom(path, package, binary=False):
    """
    __getResourceFrom(path, package, binary=False) -> str or None
    
    Returns the bytes (as a string) of the resource at the given path in the
    given package, or None if an error is encountered. If binary is True, 
    attempts to read the resource in binary mode.
    """
    for (pkgname, archf, getter) in packages:
        if pkgname == package: return getter(path, archf or pkgname, binary)

    parole.error('__getResourceFrom(): unknown package: %s', package)

#==============================================================================

def __getResourceFromDir(path, dir, binary=False):
    """
    __getResourceFromDir(path, package, binary=False) -> str or None

    Returns the bytes (as a string) of the resource at the given path in the
    given directory, or None if an error is encountered. If binary is True, 
    attempts to read the resource in binary mode.
    """
    try:
        f = open(os.sep.join([__gameDir, dir, path]), binary and 'rb' or 'r')
        return f.read()
    except Exception, e:
        raise __NotFound(e)

#==============================================================================

def __getResourceFromArch(path, archf, binary=False):
    """
    __getResourceFrom(path, package, binary=False) -> str or None

    Returns the bytes (as a string) of the resource at the given path in the
    given zip archive, or None if an error is encountered. If binary is True, 
    attempts to read the resource in binary mode.
    """
    #parole.info('archf.namelist(): %r', archf.namelist())
    if path not in archf.namelist():
        raise \
        __NotFound('__getResourceFromArch(): "%s" not found in archive "%s"' \
                % (path, archf.filename))
    try:
        return archf.read(path)
    except Exception, e:
        raise __NotFound(e)

#==============================================================================

def getResource(name, binary=False):
    """
    Attempts to retrieve the bytes of the given resource. If multiple packages
    contain the resource, the copy in the alphabetically latest package is
    returned. Returns C{None} if the given resource is not known by any package.

    @param name: The path + filename of the resource to retrieve.
    @type name: C{str}
    
    @param binary: If C{True}, then an attempt will be made to open the resource
    in binary mode. This probably only has an effect if the file is in a
    directory package. Resources from archive packages are always binary.
    @type binary: C{bool}
    
    @return: C{str} or C{None}
    """
    # see if we've already loaded this resource
    if name in __resTable:
        return __resTable[name]
    
    # we need to load it
    parole.info('Loading resource: "%s"', name)
    bytes = None

    # go through all packages until we find one with the resource
    # we need. The packages list should already be in the proper order
    for (package, f, g) in packages:
        try:
            bytes = __getResourceFrom(name, package, binary)
            parole.debug('"%s" found in "%s"', name, package)
            break
        except __NotFound, e:
            parole.debug('"%s" not found in "%s"', name, package)

    if not bytes:
        parole.error('Unknown resource: %s', name)
        return None
    
    # store the resource's bytes in the resource table
    __resTable[name] = bytes
    return bytes
    
#==============================================================================

def clearResource(name):
    """
    Clears the cache of the given resource. Any future retrieval of the 
    resource will result in an actual disk read. The resource may not actually
    be freed from memory if any user code still contains references to it.
    Furthermore, it won't actually be freed until the next sweep of Python's
    garbage collector.

    @param name: The path + filename of the resource to clear from the cache.
    @type name: C{str}
    """
    parole.info('Clearing resource: %s', name)
    if name in __resTable: 
        del __resTable[name]
    else:
        parole.warn("Can't clear unknown resource: %s", name)
    
#==============================================================================

def clearAll():
    """
    Clears all loaded resources from the cache.
    """
    parole.info('Clearing all resources')
    __resTable.clear()
    
#==============================================================================

def getTexture(name):
    """
    Attempts to retrieve the given texture resource as a PyGame C{Surface}
    object.

    @todo: Return a dummy texture if not found.

    @return: C{pygame.Surface} or C{None}

    @param name: The path + filename of the texture resource to retrieve. Must
    name an image file in a format that PyGame can read (png, jpeg, tiff, etc.).
    @type name: C{str}
    """
    # Return any cached copy of the texture surface object
    if name in __resTable:
        return __resTable[name]
    
    parole.info('Loading texture "%s"', name)

    # name should be a resource whose bytes are loadable by pygame's image
    # module
    bytes = getResource(name, binary=True)
    if not bytes:
        return None

    tex = None

    # Create a file-like object which pygame can use to read the bytes of
    # the texture
    texf = cStringIO.StringIO(bytes)

    # Attempt to load the texture
    try:
        tex = pygame.image.load(texf, name).convert()
    except Exception, e:
        # TODO: return a dummy "not found" texture
        parole.error('Unable to load texture "%s": %s', name, e)
        return None

    # Store the texture's Surface object in the resource table, rather
    # than the actual bytes of the texture file
    __resTable[name] = tex
    return tex

#==============================================================================

def getSound(name):
    """
    Attempts to retrieve the given sound resource as a PyGame C{Sound} object.
    The file can either be an uncompressed WAV or an OGG file.

    @return: C{pygame.mixer.Sound} or C{None}

    @param name: The path + filename of the sound resource to retrieve. 
    @type name: C{str}
    """
    # Return any cached copy of the texture surface object
    if name in __resTable:
        return __resTable[name]
    
    parole.info('Loading sound "%s"', name)

    # name should be a resource whose bytes are loadable by pygame's mixer
    # module
    bytes = getResource(name, binary=True)
    if not bytes:
        return None

    sound = None

    # Create a file-like object which pygame can use to read the bytes of
    # the sound
    soundf = cStringIO.StringIO(bytes)

    # Attempt to load the sound
    try:
        sound = pygame.mixer.Sound(soundf)
    except Exception, e:
        parole.error('Unable to load sound "%s": %s', name, e)
        return None
        
    # Store the Sound object in the resource table, rather
    # than the actual bytes of the sound file
    __resTable[name] = sound
    return sound

#==============================================================================

def getFont(name, size):
    """
    Attempts to retrieve the given font resource as a PyGame Font object.

    @return: C{pygame.font.Font} or C{None}

    @param name: The path + filename of the font resource to retrieve. Must name
    a font file in a format that PyGame can read (e.g., TrueType).
    @type name: C{str}
    """
    # Return any cached copy of the font object
    if (name,size) in __resTable:
        return __resTable[(name,size)]
    
    parole.info('Loading font "%s" %spt', name, size)

    # name should be a resource whose bytes are loadable by pygame's font
    # module
    bytes = getResource(name, binary=True)
    if not bytes:
        parole.error('"%s" names an empty font resource.', name)
        return None

    font = None

    # Create a file-like object which pygame can use to read the bytes of
    # the font file
    fontf = cStringIO.StringIO(bytes)

    # Attempt to load the font
    try:
        font = pygame.font.Font(fontf, size)
    except Exception, e:
        parole.error('Unable to load font "%s" %pt: %s', name, size, e)
        return None

        
    # Store the font object in the resource table, rather
    # than the actual bytes of the font file
    __resTable[(name,size)] = font
    return font
    
#==============================================================================

def getShader(scriptName):
    """
    Attempts to retrieve a L{Shader} object resource. 
    
    @param scriptName: 
    Should name a resource that is a python script. The script should, upon
    execution, create a global (to itself) object C{theShader}, which is
    expected to be an instance of L{Shader}. This object is what is retrieved
    and cached by this function.
    @type scriptName: C{str}

    @return: L{Shader} or C{None}
    """
    # Return any cached copy of the desired shader object
    if (scriptName, 'theShader') in __resTable:
        return __resTable[(scriptName, 'theShader')]
    
    parole.info('Loading shader "%s"', scriptName)
    
    theShader = getObject(scriptName, 'theShader')
    if theShader and not isinstance(theShader, parole.Shader):
        parole.error('Shader definition script bound "theShader" to non-Shader')
        return None
    
    # The shader definition worked and we have a bona fide Shader object
    # getObject should have already cached it
    return theShader

#==============================================================================

def getShaderClass(scriptName):
    """
    Attempts to retrieve the class of Shader object resource, useful for shader
    "factories". 
    
    @param scriptName:
    Should name a resource that is a python 
    script. The script should, upon execution, create a global (to itself) 
    object C{theShader}, which is expected to be an instance of 
    L{Shader}. This object's C{__class__} attribute is what is 
    retrieved and cached by this function.
    @type scriptName: C{str}

    @return: class object of a subclass of L{Shader}, or C{None}
    """
    # piggy back off of getShader (more efficient in case we've already 
    # loaded the shader)
    theShader = getShader(scriptName)
    if theShader is not None:
        return shader.__class__
    return None

#==============================================================================

def __runScript(scriptName):
    # scriptName should be a resource whose bytes are python code
    bytes = getResource(scriptName)
    if not bytes:
        return None

    # compile the code, copy the current global namespace to execute it in
    scriptCode = compile(bytes, scriptName, 'exec')
    #modName = scriptName.replace('.py', '').replace('/', '.')
    modName = scriptName.split('/')[-1].replace('.py', '')
    scriptNamespace = {'__name__': modName, 
                       '__file__': scriptName,
                       '__builtins__': globals()['__builtins__'],
                       'parole': globals()['parole']}

    # Attempt to execute the code of the shader definition script.
    # It should create a global in its namespace called 'theShader', which
    # is the shader object we want to associate with this resource
    try:
        exec scriptCode in scriptNamespace
    except Exception, e:
        parole.error('Error executing "%s".\n%s', scriptName, e)
        return None

    return scriptNamespace

#==============================================================================

def getObject(scriptName, objName):
    """
    Retrieves a python object defined in the given python script 
    resource.

    @param scriptName:
    Should name a resource that is a python 
    script. The script should, upon execution, create a global (to itself) 
    object object with the name C{objName}.
    @type scriptName: C{str}

    @param objName:
    The name of the object created in the script's global namespace to return.

    @return: C{object}
    """
    # Return any cached copy of the desired object
    if (scriptName, objName) in __resTable:
        return __resTable[(scriptName, objName)]
    
    parole.info('Loading object "%s" from "%s"', objName, scriptName)
    
    scriptNamespace = __runScript(scriptName)
    if not scriptNamespace:
        parole.error('Failed to load object "%s" from "%s"', objName,
                scriptName)
        return None
    
    if objName not in scriptNamespace:
        parole.error('Script "%s" did not bind "s"', scriptName, objName)
        return None

    obj = scriptNamespace[objName]
    
    # The script worked and we have a bona fide object
    # Cache it and return it
    __resTable[(scriptName, objName)] = obj
    return obj

#==============================================================================

def getModule(name, addToSysModules=True):
    """
    Loads a script resource and returns it as a module object.

    @param name:
    Should name a resource that is a python 
    script. The script will be loaded and executed, and a new module object will
    be constructed from its global namespace.
    @type name: C{str}

    @param addToSysModules:
    If C{True}, the loaded module will also be added to C{sys.modules}, as if
    it were truly imported.
    @type addToSysModules: C{bool}

    @return: C{module}. The module's name will be derived from that of the script
    resource, with directories corresponding to packages. For example,
    C{"scripts/util.py"} results in a module called C{"scripts.util"}.
    """
    # Return any cached copy of the desired object
    if name in __resTable:
        return __resTable[name]

    modName = name.replace('.py', '').replace('/', '.')
    parole.info('Loading script "%s" as module %s...', name, modName)

    scriptNamespace = __runScript(name)

    # set up the module object
    moduleObj = imp.new_module(modName)
    moduleObj.__dict__.update(scriptNamespace)

    # The script worked and we have a bona fide module
    # Cache it and return it
    __resTable[name] = moduleObj

    # add to sys.modules if requested
    if addToSysModules:
        if moduleObj not in sys.modules:
            sys.modules[moduleObj.__name__] = moduleObj

    return moduleObj

#==============================================================================

def exportResource(name, destination):
    """
    Exports the named resource to the given destination on disk.
    C{destination} should be the full path plus filname to which the
    byte-contents of the named resource should be copied.

    This function can be useful for extracting a sound resource from a zip
    package and writing it to disk as a standalone file so that
    it can be used by C{pygame.mixer.music}, for instance.
    """
    parole.info('Exporting resource "%s" to "%s".', name, destination)

    bytes = getResource(name, binary=True)
    if not bytes:
        parole.error('exportResource: resource "%s" not found.', name)

    destf = None
    try:
        destf = open(destination, 'wb')
        destf.write(bytes)
    except IOError, e:
        parole.error('exportResource: IOError while writing resource "%s" to'
                     ' "%s": %s', name, destination, e)
    if destf:
        destf.close()

