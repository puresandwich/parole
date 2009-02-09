
import parole

def updateFunc():
    parole.info('Game code started!')

    # Display a message in a box
    m = messageBox("You have a working skeleton game.\nYou may begin to "
                   "customize it.\nPress 'q' to quit, or '~' for the\n"
                   "interactive console")
    yield

    # Wait for the user to press 'q'
    # Use peekKeyPresses() instead of getKeyPresses() so that we don't steal
    # keypresses from the console, in case the user activates it.
    while 'q' not in parole.input.peekKeyPresses():
        yield

    # remove our message box from the display
    parole.display.scene.remove(m)

    # quit
    raise parole.ParoleShutdown

def messageBox(text, align='left'):
    """
    Use parole's shader system to construct a simple framed text box to display
    a message at the center of the screen.
    """
    font = parole.resource.getFont("fonts/Arial.ttf", 14)
    block = parole.shader.TextBlockPass(font, (255,255,255),
            wrap_width=274, bg_rgb=(0,64,128), align=align, wrap='word')
    block.text = text
    block.update()
    sdr = parole.shader.Shader("FrameContents", 
            (block.width+20, block.height+20))
    sdr.addPass(parole.shader.ColorField((0,64,128), sdr.size))
    sdr.addPass(block, (10,10))
    mbox = parole.shader.Frame((parole.shader.VerticalBevel((0,0,0), 
        (128,128,128), (255,255,255),1, 2, 1),
        parole.shader.VerticalBevel((0,0,0), (128,129,128), (255,255,255), 1, 2, 1),
        parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1,
            2, 1),
        parole.shader.HorizontalBevel((255,255,255), (128,128,128), (0,0,0), 1,
            2, 1),
        None,None,None,None),
        contents=[sdr])
    mbox.update()
    parole.display.scene.add(mbox, pos=mbox.centeredPos())
    return mbox
