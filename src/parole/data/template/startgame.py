#!/usr/bin/env python

import parole

def main():
    parole.startup('config.cfg', 'scripts/main.py', gen=True)

if __name__ == "__main__":
    main()
