#!/usr/bin/env python
import os

try:
    os.unlink('hello.txt')
except:
    pass

os.system('setup.py develop')
if os.path.exists('hello.txt'):
    print 'It worked!'
    raw_input('Press Enter')
    raise SystemExit

os.system('python setup.py develop')
if os.path.exists('hello.txt'):
    print 'It worked!'
    raw_input('Press Enter')
    raise SystemExit

print "Crap, it didn't work."
raw_input('Press enter')
