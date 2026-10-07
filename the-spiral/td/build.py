"""
Curiosity Loop - network builder.

Save your .toe in the repo root (next to /td and /photos), then in the Textport:

    exec(open(project.folder + '/td/build.py', encoding='utf-8').read())

Re-running is safe: it rebuilds /project1/curiosity_loop and keeps the values
of its custom parameters (tracking CHOP paths, tuning, etc).
Re-run it whenever you add or remove photos.
"""

import os


def _build():
    # CURIOSITY_ROOT lets you build before the .toe is saved in the repo folder
    root_dir = globals().get('CURIOSITY_ROOT') or project.folder
    rel = os.path.normpath(root_dir) == os.path.normpath(project.folder)

    def path(*parts):   # relative to the .toe when possible, so the repo stays portable
        return '/'.join(parts) if rel else os.path.join(root_dir, *parts)
    td_dir = os.path.join(root_dir, 'td')
    if not os.path.isfile(os.path.join(td_dir, 'loop_core.py')):
        print('!! Could not find td/loop_core.py next to this .toe (project.folder = %s).' % root_dir)
        print('!! Save the .toe inside the curiosity-loop folder, then run build again.')
        return

    parent_comp = op('/project1')
    warnings = []

    def setp(o, **pars):
        for name, val in pars.items():
            try:
                p = getattr(o.par, name)
                if isinstance(val, str) and val.startswith('='):
                    p.expr = val[1:]
                else:
                    p.val = val
            except Exception as e:
                warnings.append('%s.par.%s: %s' % (o.path, name, e))

    def place(o, x, y):
        o.nodeX, o.nodeY = x * 180, -y * 140
        return o

    # ---------------------------------------------------------- keep settings
    saved = {}
    old = parent_comp.op('curiosity_loop')
    if old is not None:
        for p in old.customPars:
            if p.mode == ParMode.CONSTANT:
                saved[p.name] = p.val
        old.destroy()

    base = parent_comp.create(baseCOMP, 'curiosity_loop')
    base.nodeX, base.nodeY = 0, 0
    base.color = (0.35, 0.25, 0.5)

    # ---------------------------------------------------------- custom pars
    def f(page, name, label, default, lo, hi, clamp=False):
        par = page.appendFloat(name, label=label)[0]
        par.default = default
        par.val = default
        par.normMin, par.normMax = lo, hi
        if clamp:
            par.clampMin, par.clampMax = True, True
            par.min, par.max = lo, hi
        return par

    def t(page, name, label, default):
        par = page.appendToggle(name, label=label)[0]
        par.default = default
        par.val = default
        return par

    inp = base.appendCustomPage('Input')
    inp.appendCHOP('Handchop', label='Hand Tracking CHOP')
    inp.appendCHOP('Posechop', label='Pose Tracking CHOP')
    inp.appendTOP('Videotop', label='Webcam TOP (ghost)')
    pf = inp.appendStr('Photofolder', label='Photo Folder')[0]
    pf.default = pf.val = 'artworks/images'
    t(inp, 'Mirrorx', 'Mirror X', True)
    m = inp.appendMenu('Yaxis', label='Raw Y Axis')[0]
    m.menuNames, m.menuLabels = ['auto', 'down', 'up'], ['Auto (from pose)', 'Down (MediaPipe raw)', 'Up']
    m = inp.appendMenu('Range', label='Coordinate Range')[0]
    m.menuNames, m.menuLabels = ['auto', 'zeroone', 'm05to05', 'm1to1'], ['Auto', '0 to 1', '-0.5 to 0.5', '-1 to 1']
    f(inp, 'Nearsw', 'Shoulder Width: Close', 0.40, 0.1, 0.8)
    f(inp, 'Farsw', 'Shoulder Width: Far', 0.12, 0.0, 0.5)
    f(inp, 'Ghost', 'Ghost Mirror Opacity', 0.35, 0.0, 1.0)
    t(inp, 'Debug', 'Debug Overlay', False)
    t(inp, 'Handdots', 'Hand Dots (Reveal)', False)

    tune = base.appendCustomPage('Tuning')
    f(tune, 'Awarenessgain', 'Awareness Gain (subtle)', 0.3, 0, 1)
    f(tune, 'Orbitgain', 'Orbit Gain (strong)', 1.0, 0, 2)
    f(tune, 'Onehandtime', 'One-Hand Reveal Time (0=off)', 1.5, 0, 5)
    f(tune, 'Dwelltime', 'Point Dwell Time', 1.2, 0.2, 4)
    f(tune, 'Hoverdwelltime', 'Open-Hand Dwell (0=off)', 0.0, 0, 6)
    f(tune, 'Stilltime', 'Stillness Before Forget', 2.5, 0.5, 8)
    f(tune, 'Stillthreshold', 'Stillness Threshold', 0.12, 0, 1)

    intro = base.appendCustomPage('Intro')
    t(intro, 'Intro', 'Show Intro Screen', True)
    it = intro.appendStr('Introtitle', label='Title')[0]
    it.default = it.val = 'THE SPIRAL'
    isub = intro.appendStr('Introsubtitle', label='Subtitle')[0]
    isub.default = isub.val = 'a continuous movement through states of being\nlife, death, transformation, return'
    f(intro, 'Intromirror', 'Mirror Behind Intro', 0.15, 0.0, 0.6)
    f(intro, 'Introrepeat', 'Replay Every (s without a selection, 0=off)', 15.0, 0.0, 240.0)

    sim = base.appendCustomPage('Simulate')
    t(sim, 'Simulate', 'Simulate (no camera)', True)
    t(sim, 'Simperson', 'Person Present', False)
    f(sim, 'Simbodyx', 'Body X', 0.0, -1, 1)
    f(sim, 'Simprox', 'Proximity', 0.5, 0, 1)
    ip = sim.appendInt('Simhands', label='Hands Visible')[0]
    ip.normMin, ip.normMax, ip.clampMin, ip.clampMax, ip.min, ip.max = 0, 2, True, True, 0, 2
    f(sim, 'Simh1x', 'Hand 1 X', -0.4, -1, 1)
    f(sim, 'Simh1y', 'Hand 1 Y', 0.0, -1, 1)
    f(sim, 'Simh2x', 'Hand 2 X', 0.4, -1, 1)
    f(sim, 'Simh2y', 'Hand 2 Y', 0.0, -1, 1)
    t(sim, 'Simpoint', 'Hand 1 Pointing', False)
    f(sim, 'Simhandsize', 'Hand Size (zoom)', 0.12, 0.05, 0.3)

    for name, val in saved.items():
        try:
            getattr(base.par, name).val = val
        except Exception:
            pass

    # ---------------------------------------------------------- scripts
    core = place(base.create(textDAT, 'loop_core'), 0, 0)
    setp(core, file=path('td', 'loop_core.py'), syncfile=True)
    glue = place(base.create(textDAT, 'loop_td'), 1, 0)
    setp(glue, file=path('td', 'loop_td.py'), syncfile=True)
    ex = place(base.create(executeDAT, 'frame_exec'), 2, 0)
    ex.text = (
        "# Runs the Curiosity Loop once per frame. Logic lives in loop_core / loop_td.\n"
        "def onStart():\n"
        "\t# frame callbacks stop while the timeline is paused: never open frozen\n"
        "\top('/').time.play = True\n"
        "\t# open the output window once the network has settled\n"
        "\trun(\"op('/project1/curiosity_loop/window').par.winopen.pulse()\", delayFrames=90)\n"
        "\treturn\n"
        "\n"
        "def onFrameStart(frame):\n"
        "\top('loop_td').module.update()\n"
        "\treturn\n")
    setp(ex, start=True, framestart=True, active=True)

    # ---------------------------------------------------------- photos
    exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp', '.exr')
    # which images to show: the spiral artworks by default, or e.g. `photos` for my own
    photo_folder = (saved.get('Photofolder') or 'artworks/images').strip('/')
    photo_dir = os.path.join(root_dir, *photo_folder.split('/'))
    files = sorted(fn for fn in os.listdir(photo_dir) if fn.lower().endswith(exts)) if os.path.isdir(photo_dir) else []
    files = files[:60]
    if not files:
        print('!! No images in %s - run tools/make_placeholders.py or add photos.' % photo_dir)

    for i, fn in enumerate(files):
        row, col = 2 + (i // 8) * 3, i % 8
        img = place(base.create(moviefileinTOP, 'img%d' % i), col, row)
        setp(img, file=path(*(photo_folder.split('/') + [fn])))
        mat = place(base.create(constantMAT, 'mat_photo%d' % i), col, row + 1)
        setp(mat, colormap=img.name, blending=True, alpha=1.0)
        geo = place(base.create(geometryCOMP, 'photo%d' % i), col, row + 2)
        for child in list(geo.children):
            child.destroy()
        rect = geo.create(rectangleSOP, 'rect')
        setp(rect, sizex=2.4, sizey=1.8, texture='face')
        rect.render = rect.display = True
        setp(geo, material=mat.path)

    # ---------------------------------------------------------- hand cursors
    for i in range(2):
        mat = place(base.create(constantMAT, 'mat_cursor%d' % i), 9 + i, 2)
        # no depth: a faint cursor must never punch a hole in the photo behind it
        setp(mat, colorr=1.0, colorg=0.95, colorb=0.85, alpha=0.0, blending=True,
             depthtest=False, depthwriting=False)
        geo = place(base.create(geometryCOMP, 'cursor%d' % i), 9 + i, 3)
        for child in list(geo.children):
            child.destroy()
        circ = geo.create(circleSOP, 'circ')
        setp(circ, radx=1.0, rady=1.0, divs=48)
        circ.render = circ.display = True
        setp(geo, material=mat.path, render=False, drawpriority=-1)

    # ---------------------------------------------------------- render
    cam = place(base.create(cameraCOMP, 'cam'), 11, 2)
    setp(cam, tz=10, projection='ortho', orthowidth=16)
    render = place(base.create(renderTOP, 'render1'), 12, 2)
    setp(render, camera='cam', geometry='photo* cursor*', outputresolution='custom',
         resolutionw=1280, resolutionh=720, bgcolorr=0, bgcolorg=0, bgcolorb=0, bgcolora=0)

    # trails: the "memory" that only appears in the final Orbit stage
    fb = place(base.create(feedbackTOP, 'fb'), 12, 4)
    fb.inputConnectors[0].connect(render)
    decay = place(base.create(levelTOP, 'fb_decay'), 13, 4)
    decay.inputConnectors[0].connect(fb)
    setp(decay, opacity=0.0)
    trail_over = place(base.create(overTOP, 'trail_over'), 14, 2)
    trail_over.inputConnectors[0].connect(render)
    trail_over.inputConnectors[1].connect(decay)
    trail_out = place(base.create(nullTOP, 'trail_out'), 15, 2)
    trail_out.inputConnectors[0].connect(trail_over)
    setp(fb, top='trail_out')

    # optional ghost of the webcam behind everything
    black = place(base.create(constantTOP, 'black'), 12, 6)
    setp(black, outputresolution='custom', resolutionw=1280, resolutionh=720,
         colorr=0, colorg=0, colorb=0, alpha=1)
    gsel = place(base.create(selectTOP, 'ghost_sel'), 13, 7)
    setp(gsel, top='black')
    gflip = place(base.create(flipTOP, 'ghost_flip'), 14, 7)
    gflip.inputConnectors[0].connect(gsel)
    setp(gflip, flipx="=parent().par.Mirrorx")
    gfit = place(base.create(fitTOP, 'ghost_fit'), 15, 7)
    gfit.inputConnectors[0].connect(gflip)
    setp(gfit, outputresolution='custom', resolutionw=1280, resolutionh=720)
    glevel = place(base.create(levelTOP, 'ghost_level'), 16, 7)
    glevel.inputConnectors[0].connect(gfit)
    setp(glevel, opacity=0.1)
    gover = place(base.create(overTOP, 'ghost_over'), 17, 6)
    gover.inputConnectors[0].connect(glevel)
    gover.inputConnectors[1].connect(black)
    gswitch = place(base.create(switchTOP, 'ghost_switch'), 18, 6)
    gswitch.inputConnectors[0].connect(black)
    gswitch.inputConnectors[1].connect(gover)
    setp(gswitch, index=0)

    scene = place(base.create(overTOP, 'scene'), 19, 2)
    scene.inputConnectors[0].connect(trail_out)
    scene.inputConnectors[1].connect(gswitch)

    # warp driven by hand velocity during Distortion
    noise = place(base.create(noiseTOP, 'warp_noise'), 19, 4)
    setp(noise, outputresolution='custom', resolutionw=256, resolutionh=256, mono=False,
         tz='=absTime.seconds * 0.35')
    warp = place(base.create(displaceTOP, 'warp'), 20, 2)
    warp.inputConnectors[0].connect(scene)
    warp.inputConnectors[1].connect(noise)
    setp(warp, displaceweightx=0.0, displaceweighty=0.0)

    master = place(base.create(levelTOP, 'master'), 21, 2)
    master.inputConnectors[0].connect(warp)

    # museum caption for the selected artwork (text + fade driven by loop_td)
    ink = dict(fontcolorr=0.93, fontcolorg=0.91, fontcolorb=0.87)
    ctitle = place(base.create(textTOP, 'cap_title'), 22, 6)
    setp(ctitle, outputresolution='custom', resolutionw=420, resolutionh=300, text='',
         font='Baskerville', fontsizexunit='pixels', fontsizex=34, wordwrap=True,
         alignx='left', aligny='top', bgalpha=0.0, fontalpha=0.0, **ink)
    cbody = place(base.create(textTOP, 'cap_body'), 22, 8)
    setp(cbody, outputresolution='custom', resolutionw=420, resolutionh=420, text='',
         font='Avenir Next', fontsizexunit='pixels', fontsizex=17, wordwrap=True,
         alignx='left', aligny='top', linespacingunit='pixels', linespacing=6,
         bgalpha=0.0, fontalpha=0.0, fontcolorr=0.72, fontcolorg=0.70, fontcolorb=0.66)
    # soft dark gradient behind the caption column so the grid never fights the text
    shade = place(base.create(rampTOP, 'cap_shade'), 22, 10)
    setp(shade, outputresolution='custom', resolutionw=1280, resolutionh=720, type='horizontal')
    keys = shade.par.dat.eval() if hasattr(shade.par, 'dat') else None
    if keys is not None:
        keys.text = 'pos\tr\tg\tb\ta\n0.0\t0\t0\t0\t0\n0.56\t0\t0\t0\t0\n0.66\t0\t0\t0\t0.82\n1.0\t0\t0\t0\t0.9\n'
    else:
        warnings.append('cap_shade: no ramp keys DAT, caption backdrop is flat')
    shade_lvl = place(base.create(levelTOP, 'cap_shade_level'), 23, 10)
    shade_lvl.inputConnectors[0].connect(shade)
    setp(shade_lvl, opacity=0.0)
    shade_over = place(base.create(overTOP, 'cap_shade_over'), 23, 8)
    shade_over.inputConnectors[0].connect(shade_lvl)
    shade_over.inputConnectors[1].connect(master)
    ctover = place(base.create(overTOP, 'cap_title_over'), 23, 6)
    ctover.inputConnectors[0].connect(ctitle)
    ctover.inputConnectors[1].connect(shade_over)
    setp(ctover, size='input2', prefit='nativeres', justifyh='left', justifyv='top',
         tunit='pixels', tx=810, ty=-150)
    cbover = place(base.create(overTOP, 'cap_body_over'), 24, 8)
    cbover.inputConnectors[0].connect(cbody)
    cbover.inputConnectors[1].connect(ctover)
    setp(cbover, size='input2', prefit='nativeres', justifyh='left', justifyv='top',
         tunit='pixels', tx=810, ty=-240)
    captioned = place(base.create(nullTOP, 'captioned'), 25, 6)
    captioned.inputConnectors[0].connect(cbover)

    # intro screens, from the Figma design (1440x1024 frames scaled to 1280x720 by height):
    #   page 1  title + subtitle      page 2  "raise hands" / "point to select" + hand images
    # loop_td crossfades page 1 -> 2 (intro_pages.cross) and fades the whole layer out
    # (intro_level.opacity) once someone steps in and moves.
    inter = path('fonts', 'Inter-Regular.ttf')
    inter_light = path('fonts', 'Inter-Light.ttf')
    white = dict(fontcolorr=1.0, fontcolorg=1.0, fontcolorb=1.0)

    def text_layer(name, x, y, txt, font_file, size, nx, ny, spacing=0):
        tt = place(base.create(textTOP, name), nx, ny)
        setp(tt, outputresolution='custom', resolutionw=1280, resolutionh=720, text=txt,
             fontfile=font_file, fontsizexunit='pixels', fontsizex=size,
             alignx='center', aligny='center', positionunit='pixels', positionx=x, positiony=y,
             linespacingunit='pixels', linespacing=spacing, bgalpha=0.0, **white)
        return tt

    def over(name, top, under, nx, ny, **xf):
        o = place(base.create(overTOP, name), nx, ny)
        o.inputConnectors[0].connect(top)
        o.inputConnectors[1].connect(under)
        if xf:
            setp(o, size='input2', prefit='nativeres', justifyh='center', justifyv='center',
                 tunit='pixels', **xf)
        return o

    ibg = place(base.create(constantTOP, 'intro_bg'), 22, 12)
    setp(ibg, outputresolution='custom', resolutionw=1280, resolutionh=720,
         colorr=0, colorg=0, colorb=0, alpha=1)

    # page 1: THE SPIRAL / subtitle
    ititle = text_layer('intro_title', 0, 39, '=parent().par.Introtitle', inter, 90, 22, 14)
    isubt = text_layer('intro_subtitle', 0, -74, '=parent().par.Introsubtitle', inter_light, 25, 22, 16, spacing=6)
    # a very faint mirror of the visitor behind both intro pages (artworks stay hidden)
    imir = place(base.create(levelTOP, 'intro_mirror'), 22, 10)
    imir.inputConnectors[0].connect(gfit)
    setp(imir, opacity='=parent().par.Intromirror')
    ibase = over('intro_base', imir, ibg, 23, 11)
    p1a = over('intro_p1_title', ititle, ibase, 23, 14)
    page1 = over('intro_page1', isubt, p1a, 24, 15)

    # page 2: instructions with the hand images (pointing hand's grey square crushed to black)
    def hand(name, fn, nx, ny):
        img = place(base.create(moviefileinTOP, name), nx, ny)
        setp(img, file=path('intro', fn))
        lvl = place(base.create(levelTOP, name + '_clean'), nx + 1, ny)
        lvl.inputConnectors[0].connect(img)
        setp(lvl, inlow=0.14)
        return lvl

    hl = hand('intro_hand_left', 'hand_left.png', 22, 18)
    hr = hand('intro_hand_right', 'hand_right.png', 22, 19)
    hp = hand('intro_hand_point', 'hand_point.png', 22, 20)
    raise_t = text_layer('intro_raise', -216, 142, 'raise hands', inter_light, 25, 22, 21)
    point_t = text_layer('intro_point', 195, 142, 'point to select', inter_light, 25, 22, 22)
    # Over TOP scales before it translates, so offsets are given in pre-scale pixels
    def at(x, y, sc):
        return dict(tx=round(x / sc, 1), ty=round(y / sc, 1), sx=sc, sy=sc)
    p2a = over('intro_p2_left', hl, ibase, 24, 18, **at(-319, -50, 0.703))
    p2b = over('intro_p2_right', hr, p2a, 25, 19, **at(-125, -59, 0.703))
    # the pointing hand comes on its own dark square: place it on a clear layer, then
    # "lighten" it onto the page so only the white hand shows over the faint mirror
    clear = place(base.create(constantTOP, 'intro_clear'), 24, 21)
    setp(clear, outputresolution='custom', resolutionw=1280, resolutionh=720,
         colorr=0, colorg=0, colorb=0, alpha=0)
    pt_layer = over('intro_p2_point', hp, clear, 25, 21, **at(195, -55, 0.593))
    p2c = place(base.create(compositeTOP, 'intro_p2_point_lighten'), 26, 20)
    p2c.inputConnectors[0].connect(p2b)
    p2c.inputConnectors[1].connect(pt_layer)
    setp(p2c, operand='maximum')
    p2d = over('intro_p2_raise', raise_t, p2c, 27, 21)
    page2 = over('intro_page2', point_t, p2d, 28, 22)

    pages = place(base.create(crossTOP, 'intro_pages'), 29, 15)
    pages.inputConnectors[0].connect(page1)
    pages.inputConnectors[1].connect(page2)
    setp(pages, cross=0.0)
    ilevel = place(base.create(levelTOP, 'intro_level'), 30, 15)
    ilevel.inputConnectors[0].connect(pages)
    setp(ilevel, opacity=1.0)
    iover = place(base.create(overTOP, 'intro_over'), 26, 8)
    iover.inputConnectors[0].connect(ilevel)
    iover.inputConnectors[1].connect(captioned)
    presented = place(base.create(nullTOP, 'presented'), 27, 8)
    presented.inputConnectors[0].connect(iover)

    dtext = place(base.create(textTOP, 'debug_text'), 21, 4)
    setp(dtext, outputresolution='custom', resolutionw=1280, resolutionh=720,
         bgalpha=0.0, fontsizex=18, alignx='left', aligny='top', text='')
    dover = place(base.create(overTOP, 'debug_over'), 22, 4)
    dover.inputConnectors[0].connect(dtext)
    dover.inputConnectors[1].connect(presented)
    dswitch = place(base.create(switchTOP, 'debug_switch'), 23, 2)
    dswitch.inputConnectors[0].connect(presented)
    dswitch.inputConnectors[1].connect(dover)

    out = place(base.create(nullTOP, 'out'), 24, 2)
    out.inputConnectors[0].connect(dswitch)
    out_top = place(base.create(outTOP, 'out1'), 25, 2)
    out_top.inputConnectors[0].connect(out)
    base.viewer = True

    win = place(base.create(windowCOMP, 'window'), 25, 4)
    # normal title bar so the window can be dragged around
    setp(win, winop='out', winw=1280, winh=720, borders=True, title='Curiosity Loop')

    # ---------------------------------------------------------- done
    try:
        glue.module.Reset()
    except Exception as e:
        warnings.append('loop_td reset: %s' % e)
    print('== Curiosity Loop built: %d photos -> %s' % (len(files), base.path))
    if warnings:
        print('== %d parameter warnings (usually harmless - paste to Claude if visuals look wrong):' % len(warnings))
        for w in warnings:
            print('   ', w)
    if rel:
        try:
            project.save()
            print('== Saved %s' % project.name)
        except Exception as e:
            print('!! Could not save the project: %s' % e)
    print('== Next: Simulate page -> toggle Person Present, set Hands Visible = 2, etc.')
    print('== Or wire MediaPipe: set Input page -> Hand/Pose Tracking CHOP, turn off Simulate.')


_build()
