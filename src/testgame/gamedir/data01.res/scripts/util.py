
def messageBox(text, align='center', textWidth=274):
    font = parole.resource.getFont("fonts/Arial.ttf", 14)
    block = parole.shader.TextBlockPass(font, (255,255,255),
            wrap_width=textWidth, bg_rgb=(0,64,128), align=align, wrap='word')
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

