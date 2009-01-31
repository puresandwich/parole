
import parole, traceback, sys

def t_logging():
    parole.debug('gubed')
    parole.info('ofni')
    parole.warn('nraw')
    parole.error('rorre')
    
def t_startup():
    def update():
        parole.info('t_startup update function')        
        raise parole.ParoleShutdown
    
    parole.startup('test.cfg', update, 'Testing')

firstUpdate = True

def t_input():
    def update():
        global firstUpdate
        if firstUpdate:
            parole.info("----> Press some keys. 'q' quits.")
            firstUpdate = False
        for key in parole.input.getKeyPresses():
            if key == 'q':
                raise parole.ParoleShutdown
        
    parole.startup('test.cfg', update, 'Testing')

tests = [t_logging, t_startup, t_input]
failed = {}

def main():
    for t in tests:
        failed[t] = False
        
    for t in tests:
        print '----------\nTest %s\n----------' % (t.__name__)
        try:
            t()
        except Exception, e:
            traceback.print_exception(type(e), e, sys.exc_traceback)
            print 'Test failed.'
            failed[t] = True
    
    print '\nSummary'
    print 'Pass | Fail | Test'
    for t in tests:
        if failed[t]:
            print '[ ]  | [X]  |', t.__name__
        else:
            print '[X]  | [ ]  |', t.__name__

if __name__ == "__main__":
    main()