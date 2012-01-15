#!/usr/bin/env python
f = open('hello.txt', 'w')
f.write('hello world!')
f.close()
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup

setup(
        name = "parole",
        version = "0.5.0dev",
        description="The Python Advanced Roguelike Engine",
        long_description=\
"""
Parole is the Python Advanced Roguelike Engine, a framework in Python 2.5-2.7
for use with PyGame to create graphical, discrete-event, agent-based simulations
in the Roguelike genre.
""",

        install_requires = ['pygame>=1.8'],

        package_dir={'':'src'},
        packages=['parole'],

        scripts=['src/scripts/parolestart.py', 'src/scripts/parolenew.py'],

        package_data = {'parole': ['data/*.cfg',
                                   'data/template/config.cfg',
                                   'data/template/startgame.py',
                                   'data/template/gamedir/data01.res/fonts/*',
                                   'data/template/gamedir/data01.res/scripts/*',
                                   'data/template/gamedir/data01.res/sounds/*',
                                   ]},

        author = 'Max Bane',
        author_email = 'max.bane@gmail.com',
        url = 'http://parole.googlecode.com',
        license="GNU GPL v2"
    )
