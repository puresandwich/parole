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
The Parole resource module provides a resource management system vaguely
inspired by that of the Quake 3 engine.

In this system, all of the resources needed by a game (art, sounds, video,
text, whatever) are collected together into "packages" which reside in the
game's "gamedir" (specified by config option "general.gamedir"). Each package
is a directory or a Zip archive whose name must end with the suffix ".res"
(by default; controlled by config option "resource.packsuffix").

Upon engine startup, all of the packages under the gamedir are identified and
scanned. Together, their contents constitute all of the resources that the
game has access to. An individual resource is identified by its name, which
should correspond to the actual path + filename of some file contained in one
of the packages, and can be retrieved with the getResource() function. If a
resource name is contained by more than one package, the alphabetically latest
package takes precedence. This allows one to easily patch a game's resources
by simply adding a package whose name comes alphabetically later than any 
existing ones - whatever resources it contains will effectively replace any
copies in previous packages.

The getResource() function caches the resources it returns, so that future
requests for the same resource will not result in an actual disk-read. If
a resource is no longer needed, its data can be cleared from the cache with
the clearResource() function. Note that if any user code still has references
to the data, it may not actually be freed from memory.

The resource module also provides a number of convenience functions, like
getTexture(), which both retrieves the bytes of the requested resource, and
attempts to turn those bytes into a useful PyGame Surface object.

It is possible to disallow directory packages through the config option
"resource.allowdirs".
"""

import pygame, parole, logging, os, zipfile, cStringIO, shader

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

def init():
    """
    init() -> None
    
    Initializes the resource module. Detects and loads all resource pakcages 
    in the gamedir directory. Automatically called during engine 
    startup - user code shouldn't need to use this function.
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
    
def unload():
    parole.conf.notify(__onConfigChange, False)


#==============================================================================

def getPackages():
    """
    getPackages() -> [(pkgname, isArch), ...]

    Returns a list of (pkgname, isArch) pairs for each loaded resource package,
    where isArch indicates whether the associated package is a zip archive or
    not (in which case, it's a directory). The packages are listed in the order
    that they are searched for resources: reverse alphabetic.
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
    getResource(name, [binary]) -> str or None

    Attempts to retrieve the bytes of the given resource. If multiple packages
    contain the resource, the copy in the alphabetically latest package is
    returned. Returns None if the given resource is not known by any package.
    If binary is given and is True, then it will attempt to open the resource
    in binary mode - this probably only has an effect if the file is in
    a directory package. Resources from archive packages are always binary.
    """
    # see if we've already loaded this resource
    if name in __resTable:
        return __resTable[name]
    
    # we need to load it
    logging.info('Loading resource: "%s"', name)
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
    clearResource(name) -> None

    Clears the cache of the given resource. Any future retrieval of the 
    resource will result in an actual disk read. The resource may not actually
    be freed from memory if any user code still contains references to it.
    Furthermore, it won't actually be freed until the next sweep of Python's
    garbage collector.
    """
    logging.info('Clearing resource: %s', name)
    if name in __resTable: 
        del __resTable[name]
    else:
        parole.warn("Can't clear unknown resource: %s", name)
    
#==============================================================================

def clearAll():
    """
    clearAll() -> None

    Clears all loaded resources from the cache.
    """
    logging.info('Clearing all resources')
    __resTable.clear()
    
#==============================================================================

def getTexture(name):
    """
    getTexture(name) -> pygame.Surface or None

    Attempts to retrieve the given texture resource as a PyGame Surface object.
    TODO: Return a dummy texture if not found.
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
    getSound(name) -> pygame.mixer.Sound or None

    Attempts to retrieve the given sound resource as a PyGame C{Sound} object.
    The file can either be an uncompressed WAV or an OGG file.
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
    getFont(name) -> pygame.font.Font or None

    Attempts to retrieve the given font resource as a PyGame Font object.
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
    getShader(name) -> parole.shader.Shader or None

    Attempts to retrieve a Shader object resource. The name argument should
    name a resource which is a python script. The script should, upon
    execution, create a global (to itself) object "theShader", which is
    expected to be an instance of parole.shader.Shader. This object is what
    is retrieved and cached by this function.
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
    getShaderClass(name) -> parole.shader.Shader class object or None

    Attempts to retrieve the class of Shader object resource, useful for shader
    "factories". The name argument should name a resource that is a python 
    script. The script should, upon execution, create a global (to itself) 
    object "theShader", which is expected to be an instance of 
    parole.shader.Shader. This object's "__class__" attribute is what is 
    retrieved and cached by this function.
    """
    # piggy back off of getShader (more efficient in case we've already 
    # loaded the shader)
    theShader = getShader(scriptName)
    if theShader is not None:
        return shader.__class__
    return None

#==============================================================================

def getObject(scriptName, objName):
    """
    getFunction(scriptName, objName) -> object or None

    Retrieves a python object defined in the given python script 
    resource.
    """
    # Return any cached copy of the desired shader object
    if (scriptName, objName) in __resTable:
        return __resTable[(scriptName, objName)]
    
    parole.info('Loading object "%s" from "%s"', objName, scriptName)
    
    # scriptName should be a resource whose bytes are python code
    bytes = getResource(scriptName)
    if not bytes:
        return None

    # compile the code, copy the current global namespace to execute it in
    scriptCode = compile(bytes, scriptName, 'exec')
    scriptNamespace = globals().copy()

    # Attempt to execute the code of the shader definition script.
    # It should create a global in its namespace called 'theShader', which
    # is the shader object we want to associate with this resource
    try:
        exec scriptCode in scriptNamespace
    except Exception, e:
        parole.error('Error executing "%s".\n%s', scriptName, e)
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

def exportResource(name, destination):
    """
    Exports the named resource to the given destination on disk.
    C{destination} should be the full path plus filname to which the
    byte-contents of the named resource should be copied.

    This function can be useful for extracting a sound resource from an zip
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

