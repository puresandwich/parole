#summary Major prerequisites and features of the Python Advanced Roguelike Engine

# Prerequisites #

Parole is written in, and requires, [Python](http://python.org) version 2.5. It is not yet tested or supported with Python 2.6, and is certain not to work with 3.0.

In addition, Parole requires the following libraries to be installed:
  * [Pygame](http://pygame.org) version 1.8.1+, which in turn is built on (and depending on your platform, probably comes with):
    * [SDL](http://libsdl.org) 1.2+ and the usual SDL packages (sdl\_image, etc.)

Parole also optionally (and automatically) works with the following:
  * The [psyco](http://psyco.sf.net) just-in-time Python compiler.

# Features #
_(List compilation in progress)_

Parole is meant to help you quickly write 2-dimensional, tile-based games, with special emphasis on games in the [Roguelike](http://roguebasin.roguelikedevelopment.org) genre. Its aim is to be useful without getting in your way; no needless wrapping or replacement of functionality that Pygame or the Python standard library do perfectly well.

  * A central event-driven frame loop.
    * Calls a user-supplied function, or steps through a user-supplied generator each frame.
    * Can switch at will between updating constantly (e.g., for animation), or polling for input events between updates (drastically reducing cpu usage).
  * Selective activation of engine features, divided into different submodules.
  * A central logging mechanism with four log levels, based on the standard library logging module.
  * A full-featured configuration system (built on Vinay Sajip's [config](http://www.red-dove.com/python_config.html) module) with a powerful configuration file syntax, used by the engine for its own configuration, and usable by the user for game-specific configuration.
    * Configuration changes can be made in-game, with immediate results.
  * An in-game, interactive python console.
    * Drops down over the display at the touch of "~" (by default).
    * Allows interactive introspection of, and interaction with, the currently running engine and game; invaluable for development and debugging!
    * Can be disabled and hidden from the player, if desired.
  * Intelligent polling and handling of keyboard input
    * Automatically deals with modifier keys (control, alt, etc.), giving the programmer a simple string like "ctrl p", "alt a", "@" (for shift+2), etc.
    * Easy player-remappable keybindings. Don't check for the player pressing "q", simply check for the "quaff" command and let the user's configuration file determine what keypress gives that command.
    * A simple stack mechanism for handling multiple key-mappings (so, for example, when the player calls up his inventory, the inventory key-mappings become active, temporarily occluding the main screen's key-mappings).
  * A powerful graphical display system with a simple interface.
    * Shaders...