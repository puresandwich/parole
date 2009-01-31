
import parole, logging, sys
import pygame
from optparse import OptionParser

def main():
    parser = OptionParser()

    (options, args) = parser.parse_args()

    if len(args) != 2:
        print 'Please provide two args: config file, and updateFunc script'
        return

    print 'Config file: %s\nScript: %s' % (args[0], args[1])

    parole.startup(args[0], args[1])

if __name__ == "__main__":
    main()
