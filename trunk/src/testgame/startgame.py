#!/usr/bin/env python

import parole
import main

def start():
    parole.startup('testgame.cfg', main.updateFunc, gen=True)

if __name__ == "__main__":
    start()
