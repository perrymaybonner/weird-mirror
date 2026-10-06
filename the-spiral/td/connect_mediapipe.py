"""
Curiosity Loop - wire MediaPipe into /project1/curiosity_loop.

Prerequisite: MediaPipe.tox is already in /project1 and named `MediaPipe`
(drag it in from the plugin's toxes/ folder, choose "Enable External .tox").
Then in the Textport:

    exec(open(project.folder + '/td/connect_mediapipe.py', encoding='utf-8').read())

It:
  1. turns on only the models we use (hands + pose) to save CPU,
  2. loads hand_tracking.tox / pose_tracking.tox next to MediaPipe,
  3. picks the helper CHOP outputs whose channels loop_td recognises,
  4. points curiosity_loop at them (+ the webcam TOP for the ghost layer),
  5. turns the simulator off, saves, and prints a diagnosis.
Safe to re-run.
"""

import os

MP_TOX_DIR = os.path.expanduser('~/Downloads/mediapipe-touchdesigner/toxes')


def _connect():
    p1 = op('/project1')
    mp = p1.op('MediaPipe')
    cl = p1.op('curiosity_loop')
    if mp is None or cl is None:
        print('!! Need /project1/MediaPipe and /project1/curiosity_loop first.')
        return
    glue = cl.op('loop_td').module

    # 1. only the models we need (names match the MediaPipe COMP's parameters)
    # Showoverlays off: the ghost layer should be a clean mirror, not debug skeletons
    wanted = {'Showoverlays': False, 'Detectgestures': True, 'Detectposes': True,
              'Detectfacelandmarks': False, 'Detectfaces': False, 'Detectobjects': False,
              'Detectimages': False, 'Detectimageembeddings': False, 'Detectsegments': False}
    for name, val in wanted.items():
        par = getattr(mp.par, name, None)
        if par is not None:
            par.val = val

    # 2. helper components, wired to the matching MediaPipe output
    def helper(name, keywords, x):
        comp = p1.op(name)
        if comp is None:
            path = os.path.join(MP_TOX_DIR, name + '.tox')
            if not os.path.isfile(path):
                print('!! Missing %s' % path)
                return None
            comp = p1.loadTox(path)
            comp.name = name
        comp.nodeX, comp.nodeY = mp.nodeX + 300, mp.nodeY + x
        if comp.inputConnectors and not comp.inputConnectors[0].connections:
            for oc in mp.outputConnectors:
                if any(k in oc.outOP.name.lower() for k in keywords):
                    comp.inputConnectors[0].connect(oc)
                    break
        return comp

    hands = helper('hand_tracking', ('hand', 'gesture'), -200)
    pose = helper('pose_tracking', ('pose',), -400)

    # 3. choose the CHOP output whose channels we can actually read
    def best_chop(comp, aliases, n):
        if comp is None:
            return None, 0
        best, score = None, 0
        candidates = [oc.outOP for oc in comp.outputConnectors if oc.outOP.isCHOP]
        candidates += [c for c in comp.findChildren(type=CHOP, maxDepth=2) if c not in candidates]
        for chop in candidates:
            try:
                cmap = glue.ChannelMap(chop, aliases, n)
                s = sum(len(v) for v in cmap.entities.values()) + 21 * len(cmap.sample_layout)
            except Exception:
                s = 0
            if s > score:
                best, score = chop, s
        if best is None and candidates:
            # nobody in frame yet, so channels may be empty; trust the first output
            best = candidates[0]
        return best, score

    def null_after(chop, name, y):
        if chop is None:
            return None
        n = p1.op(name) or p1.create(nullCHOP, name)
        n.nodeX, n.nodeY = mp.nodeX + 600, mp.nodeY + y
        if chop.parent() == p1:
            n.inputConnectors[0].connect(chop)
        else:   # a CHOP inside the helper: reference it with a Select CHOP
            sel = p1.op(name + '_sel') or p1.create(selectCHOP, name + '_sel')
            sel.nodeX, sel.nodeY = mp.nodeX + 450, mp.nodeY + y
            sel.par.chops = chop.path
            n.inputConnectors[0].connect(sel)
        return n

    hchop, hs = best_chop(hands, glue.HAND_ALIASES, 21)
    pchop, ps = best_chop(pose, glue.POSE_ALIASES, 33)
    hnull = null_after(hchop, 'hands_null', -200)
    pnull = null_after(pchop, 'pose_null', -400)

    # 4. point the piece at them
    if hnull is not None:
        cl.par.Handchop = hnull.path
    if pnull is not None:
        cl.par.Posechop = pnull.path
    video = next((oc.outOP for oc in mp.outputConnectors if oc.outOP.isTOP), None)
    if video is not None:
        cl.par.Videotop = video.path

    # 5. go live
    ok = hnull is not None and pnull is not None
    if ok:
        cl.par.Simulate = False
    glue.Reset()
    project.save()
    print('== hands: %s (%d landmarks recognised)' % (hchop.path if hchop else 'NOT FOUND', hs))
    print('== pose:  %s (%d landmarks recognised)' % (pchop.path if pchop else 'NOT FOUND', ps))
    print('== ghost video: %s' % (video.path if video else 'none'))
    print('== Simulate is %s. Saved %s' % ('OFF (live camera)' if ok else 'still ON', project.name))
    glue.Diagnose()


_connect()
