"""
Curiosity Loop - TouchDesigner glue.

Lives in a Text DAT called `loop_td` inside /project1/curiosity_loop and is
called once per frame by the `frame_exec` Execute DAT.

  tracking CHOPs --> read_inputs() --> loop_core.CuriosityLoop --> apply()
                                                                   (geo/mat/TOP pars)

Useful from the Textport:
  op('/project1/curiosity_loop/loop_td').module.Diagnose()   # what did we find?
  op('/project1/curiosity_loop/loop_td').module.Reset()      # restart the loop
"""

import json
import math
import os
import re
import time
import traceback

BASE = parent()

HAND_NAMES = [
    'wrist', 'thumb_cmc', 'thumb_mcp', 'thumb_ip', 'thumb_tip',
    'index_finger_mcp', 'index_finger_pip', 'index_finger_dip', 'index_finger_tip',
    'middle_finger_mcp', 'middle_finger_pip', 'middle_finger_dip', 'middle_finger_tip',
    'ring_finger_mcp', 'ring_finger_pip', 'ring_finger_dip', 'ring_finger_tip',
    'pinky_mcp', 'pinky_pip', 'pinky_dip', 'pinky_tip']
POSE_NAMES = [
    'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer', 'right_eye_inner',
    'right_eye', 'right_eye_outer', 'left_ear', 'right_ear', 'mouth_left',
    'mouth_right', 'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_pinky', 'right_pinky', 'left_index',
    'right_index', 'left_thumb', 'right_thumb', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle', 'left_heel',
    'right_heel', 'left_foot_index', 'right_foot_index']
WRIST, INDEX_MCP, INDEX_PIP, INDEX_TIP = 0, 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_PIP, RING_TIP, PINKY_PIP, PINKY_TIP = 14, 16, 18, 20
NOSE, L_SHOULDER, R_SHOULDER = 0, 11, 12
CAM_ASPECT = 16.0 / 9.0


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _aliases(names):
    table = {}
    for i, n in enumerate(names):
        for variant in {n, n.replace('_finger', ''), n.replace('finger_', '')}:
            table[_norm(variant)] = i
    return sorted(table.items(), key=lambda kv: -len(kv[0]))


HAND_ALIASES = _aliases(HAND_NAMES)
POSE_ALIASES = _aliases(POSE_NAMES)
ENTITY_RE = re.compile(r'(?:^|[^a-z])(?:hand|pose|person|h|p)[_ ]?(\d+)')
AXIS_RE = re.compile(r'(?:^|[^a-z0-9])t?([xyz])$')


# ============================================================== channel map
class ChannelMap:
    """Figures out which CHOP channel is which landmark, whatever the naming.

    Handles names like  h1:wrist:x  /  hand0_index_finger_tip_x  /  p1/left_shoulder:ty
    and a 'sample layout' where each channel (x, y, z) holds one landmark per sample.
    """

    def __init__(self, chop, aliases, n_landmarks):
        self.entities = {}        # entity -> {lm: {axis: chan_index}}
        self.sample_layout = {}   # entity -> {axis: chan_index}
        self.extra = {}           # entity -> {name: chan_index}  (e.g. gesture scores)
        self.n_landmarks = n_landmarks
        for ci, ch in enumerate(chop.chans()):
            n = ch.name.lower()
            m_axis = AXIS_RE.search(n)
            m_ent = ENTITY_RE.search(n)
            ent = int(m_ent.group(1)) if m_ent else 0
            if not m_axis:
                self.extra.setdefault(ent, {})[_norm(n)] = ci
                continue
            axis = m_axis.group(1)
            rest = n[:m_axis.start()]
            if m_ent and m_ent.end() <= len(rest):
                rest = rest[:m_ent.start()] + ' ' + rest[m_ent.end():]
            rest = _norm(rest)
            lm = None
            for key, idx in aliases:
                if key and key in rest:
                    lm = idx
                    break
            if lm is None:
                digits = re.findall(r'\d+', rest)
                if digits and int(digits[-1]) < n_landmarks:
                    lm = int(digits[-1])
            if lm is None:
                if chop.numSamples >= n_landmarks:
                    self.sample_layout.setdefault(ent, {})[axis] = ci
                continue
            self.entities.setdefault(ent, {}).setdefault(lm, {})[axis] = ci

    def read(self, chop):
        """-> {entity: {lm: (x, y)}}"""
        out = {}
        chans = chop.chans()
        for ent, lms in self.entities.items():
            pts = {}
            for lm, ax in lms.items():
                if 'x' in ax and 'y' in ax:
                    pts[lm] = (chans[ax['x']][0], chans[ax['y']][0])
            if pts:
                out[ent] = pts
        for ent, ax in self.sample_layout.items():
            if 'x' in ax and 'y' in ax:
                cx, cy = chans[ax['x']], chans[ax['y']]
                n = min(len(cx), self.n_landmarks)
                out[ent] = {i: (cx[i], cy[i]) for i in range(n)}
        return out

    def describe(self):
        lines = []
        for ent, lms in sorted(self.entities.items()):
            lines.append('  entity %d: %d landmarks (%s)' % (ent, len(lms), sorted(lms)[:6]))
        for ent in self.sample_layout:
            lines.append('  entity %d: sample layout' % ent)
        for ent, ex in self.extra.items():
            lines.append('  entity %d extra chans: %s' % (ent, list(ex)[:8]))
        return '\n'.join(lines) or '  (nothing recognised)'


# ============================================================== tracking
class Tracker:
    def __init__(self):
        self.hand_map = self.pose_map = None
        self.hand_sig = self.pose_sig = None
        self.range_min = 0.0
        self.range_absmax = 0.0
        self.range_mean = None     # average coordinate: ~0.5 for 0..1 data, ~0 for centered
        self.ydown_vote = 1.0      # >0 means raw y points down (MediaPipe default)
        self.stale = {}            # key -> (signature, since)
        self.hand_state = {}       # entity -> dict
        self.body = {'x': 0.0, 'w': None, 'speed': 0.0}

    # ---- helpers
    def _map(self, chop, which):
        sig = (chop.path, chop.numChans, chop.numSamples, chop.chans()[0].name if chop.numChans else '')
        if which == 'hand':
            if sig != self.hand_sig:
                self.hand_map, self.hand_sig = ChannelMap(chop, HAND_ALIASES, 21), sig
            return self.hand_map
        if sig != self.pose_sig:
            self.pose_map, self.pose_sig = ChannelMap(chop, POSE_ALIASES, 33), sig
        return self.pose_map

    def _is_live(self, key, pts, now):
        vals = [v for p in pts.values() for v in p]
        if not vals or all(abs(v) < 1e-6 for v in vals) or not all(math.isfinite(v) for v in vals):
            return False
        sig = tuple(round(v, 6) for v in vals[:12])
        prev = self.stale.get(key)
        if prev is None or prev[0] != sig:
            self.stale[key] = (sig, now)
            return True
        return now - prev[1] < 0.4       # frozen values = tracker lost you

    def _observe_range(self, pts):
        # off-screen landmarks legitimately fall outside 0..1 (e.g. legs below
        # the frame), so decide the range from the average, not the extremes
        vals = [v for p in pts.values() for v in p]
        for v in vals:
            self.range_min = min(self.range_min, v)
            self.range_absmax = max(self.range_absmax, abs(v))
        if vals:
            m = sum(vals) / len(vals)
            self.range_mean = m if self.range_mean is None else self.range_mean + (m - self.range_mean) * 0.02

    def _to01(self, v):
        mode = BASE.par.Range.eval()
        if mode == 'auto':
            if self.range_mean is None or self.range_mean > 0.08:
                mode = 'zeroone'
            else:
                mode = 'm1to1' if self.range_absmax > 0.75 else 'm05to05'
        if mode == 'm1to1':
            return (v + 1.0) * 0.5
        if mode == 'm05to05':
            return v + 0.5
        return v

    def _ydown(self):
        mode = BASE.par.Yaxis.eval()
        if mode == 'down':
            return True
        if mode == 'up':
            return False
        return self.ydown_vote >= 0

    def screen(self, p):
        """raw landmark -> screen-normalized (-1..1, y up, mirrored)."""
        u, v = self._to01(p[0]), self._to01(p[1])
        x = (0.5 - u) * 2.0 if BASE.par.Mirrorx.eval() else (u - 0.5) * 2.0
        y = (0.5 - v) * 2.0 if self._ydown() else (v - 0.5) * 2.0
        return x, y

    @staticmethod
    def _d(a, b):
        return math.hypot((a[0] - b[0]) * CAM_ASPECT, a[1] - b[1])

    # ---- pose
    def read_body(self, chop, now, dt):
        if chop is None or chop.numChans == 0:
            return None
        people = self._map(chop, 'pose').read(chop)
        best, best_w = None, 0.0
        for ent, pts in people.items():
            if L_SHOULDER not in pts or R_SHOULDER not in pts:
                continue
            if not self._is_live(('pose', ent), pts, now):
                continue
            self._observe_range(pts)
            ls = tuple(map(self._to01, pts[L_SHOULDER]))
            rs = tuple(map(self._to01, pts[R_SHOULDER]))
            w = self._d(ls, rs)
            if w > best_w:
                best, best_w = (pts, ls, rs), w
        if best is None:
            return None
        pts, ls, rs = best
        if NOSE in pts:   # auto-detect y direction: the nose is above the shoulders
            ny = self._to01(pts[NOSE][1])
            vote = 1.0 if ny < (ls[1] + rs[1]) * 0.5 else -1.0
            self.ydown_vote += (vote - self.ydown_vote) * 0.05
        mid = ((pts[L_SHOULDER][0] + pts[R_SHOULDER][0]) * 0.5,
               (pts[L_SHOULDER][1] + pts[R_SHOULDER][1]) * 0.5)
        x, _ = self.screen(mid)
        b = self.body
        if b['w'] is None:
            b['x'], b['w'] = x, best_w
        raw_speed = (abs(x - b['x']) + abs(best_w - b['w']) * 4.0) / max(dt, 1e-3)
        b['speed'] += (raw_speed - b['speed']) * min(1.0, dt / 0.15)
        b['x'], b['w'] = x, best_w
        near, far = BASE.par.Nearsw.eval(), BASE.par.Farsw.eval()
        prox = (best_w - far) / max(near - far, 1e-3)
        return {'x': x, 'prox': max(0.0, min(1.0, prox)), 'speed': b['speed']}

    # ---- hands
    def read_hands(self, chop, core, now, dt):
        if chop is None or chop.numChans == 0:
            return []
        cmap = self._map(chop, 'hand')
        found = cmap.read(chop)
        chans = chop.chans()
        hands = []
        for ent, pts in sorted(found.items()):
            if WRIST not in pts or INDEX_TIP not in pts:
                continue
            if not self._is_live(('hand', ent), pts, now):
                self.hand_state.pop(ent, None)
                continue
            self._observe_range(pts)
            p01 = {k: (self._to01(v[0]), self._to01(v[1])) for k, v in pts.items()}
            w = p01[WRIST]
            palm = self._d(w, p01.get(MIDDLE_MCP, p01.get(INDEX_MCP, p01[INDEX_TIP])))
            palm = max(palm, 1e-3)

            # pointing = index extended, at least two of the other fingers curled
            score = 0.0
            if all(k in p01 for k in (INDEX_PIP, MIDDLE_PIP, MIDDLE_TIP, RING_PIP, RING_TIP, PINKY_PIP, PINKY_TIP)):
                idx_ext = (self._d(p01[INDEX_TIP], w) > self._d(p01[INDEX_PIP], w) * 1.15 and
                           self._d(p01[INDEX_TIP], w) > palm * 1.5)
                curled = sum(self._d(p01[t], w) < self._d(p01[pp], w) * 1.08
                             for t, pp in ((MIDDLE_TIP, MIDDLE_PIP), (RING_TIP, RING_PIP), (PINKY_TIP, PINKY_PIP)))
                score = 1.0 if (idx_ext and curled >= 2) else 0.0
            for name, ci in cmap.extra.get(ent, {}).items():   # plugin's own gesture, if any
                if 'point' in name and chans[ci][0] > 0.5:
                    score = 1.0

            st = self.hand_state.setdefault(ent, {'score': 0.0, 'pointing': False, 'pos': None, 'speed': 0.0})
            st['score'] += (score - st['score']) * min(1.0, dt / 0.12)
            st['pointing'] = st['score'] > (0.4 if st['pointing'] else 0.6)

            cx, cy = self.screen(((pts[WRIST][0] + pts.get(MIDDLE_MCP, pts[WRIST])[0]) * 0.5,
                                  (pts[WRIST][1] + pts.get(MIDDLE_MCP, pts[WRIST])[1]) * 0.5))
            tx, ty = self.screen(pts[INDEX_TIP])
            if st['pointing'] and INDEX_MCP in pts:   # aim a little past the fingertip
                mx, my = self.screen(pts[INDEX_MCP])
                tx, ty = tx + (tx - mx) * 0.6, ty + (ty - my) * 0.6
            elif not st['pointing']:
                tx, ty = cx, cy
            if st['pos'] is not None:
                sp = math.hypot(cx - st['pos'][0], cy - st['pos'][1]) / max(dt, 1e-3)
                st['speed'] += (sp - st['speed']) * min(1.0, dt / 0.15)
            st['pos'] = (cx, cy)
            hands.append(core.Hand(cx, cy, tip_x=tx, tip_y=ty, size=palm,
                                   pointing=st['pointing'], speed=st['speed']))
        return hands[:2]


# ============================================================== simulator
def _sim_inputs(core):
    p = BASE.par
    hands = []
    for i in range(int(p.Simhands.eval())):
        x = p.Simh1x.eval() if i == 0 else p.Simh2x.eval()
        y = p.Simh1y.eval() if i == 0 else p.Simh2y.eval()
        prev = _S['sim_prev'].get(i, (x, y))
        speed = math.hypot(x - prev[0], y - prev[1]) / max(_S['dt'], 1e-3)
        _S['sim_prev'][i] = (x, y)
        hands.append(core.Hand(x, y, size=p.Simhandsize.eval(),
                               pointing=bool(p.Simpoint.eval()) and i == 0, speed=speed))
    bx = p.Simbodyx.eval()
    bspeed = abs(bx - _S['sim_prev'].get('b', bx)) / max(_S['dt'], 1e-3)
    _S['sim_prev']['b'] = bx
    return core.Inputs(person=bool(p.Simperson.eval()), body_x=bx,
                       proximity=p.Simprox.eval(), body_speed=bspeed, hands=hands)


# ============================================================== main loop
_S = {'loop': None, 'core': None, 'tracker': None, 'last': None, 'dt': 1 / 60.0,
      'err_t': 0.0, 'frame': 0, 'sim_prev': {}, 'ops': None}


def _cfg():
    p = BASE.par
    return {'awareness_gain': p.Awarenessgain.eval(), 'orbit_gain': p.Orbitgain.eval(),
            'dwell_time': p.Dwelltime.eval(), 'hover_dwell_time': p.Hoverdwelltime.eval(),
            'still_time': p.Stilltime.eval(), 'still_threshold': p.Stillthreshold.eval(),
            'one_hand_time': p.Onehandtime.eval(),
            'show_cursors': bool(getattr(p, 'Handdots', None) and p.Handdots.eval()),
            'intro': bool(p.Intro.eval()) if getattr(p, 'Intro', None) is not None else False}


def _ops():
    photos = []
    i = 0
    while op('photo%d' % i) is not None:
        photos.append((op('photo%d' % i), op('mat_photo%d' % i), op('img%d' % i)))
        i += 1
    return {'photos': photos,
            'cursors': [(op('cursor%d' % i), op('mat_cursor%d' % i)) for i in range(2)],
            'fb_decay': op('fb_decay'), 'warp': op('warp'), 'ghost_sel': op('ghost_sel'),
            'ghost_level': op('ghost_level'), 'ghost_switch': op('ghost_switch'),
            'debug_text': op('debug_text'), 'debug_switch': op('debug_switch'),
            'cap_title': op('cap_title'), 'cap_body': op('cap_body'),
            'cap_body_over': op('cap_body_over'), 'cap_shade': op('cap_shade_level'),
            'intro_level': op('intro_level'), 'intro_pages': op('intro_pages')}


def _load_captions(ops, core):
    """One caption per photo, found by the image's OWN file name in the museum
    metadata next to its folder (artworks/images/007.jpg -> artworks/metadata/
    artworks.json record with filename 007.jpg). No record -> no caption."""
    caps, cache = [], {}
    for _, _, img in ops['photos']:
        cap = None
        if img is not None:
            f = img.par.file.eval()
            full = f if os.path.isabs(f) else os.path.join(project.folder, f)
            meta = os.path.join(os.path.dirname(os.path.dirname(full)), 'metadata', 'artworks.json')
            if meta not in cache:
                try:
                    with open(meta, encoding='utf-8') as fh:
                        cache[meta] = {r['filename']: r for r in json.load(fh)}
                except Exception:
                    cache[meta] = {}
            rec = cache[meta].get(os.path.basename(full))
            if rec:
                title, body = core.caption_for(rec)
                cap = (title or '', body or '', rec['filename'])
        caps.append(cap)
    return caps


def Reset():
    _S['loop'] = None
    _S['tracker'] = None
    _S['ops'] = None
    print('[curiosity_loop] reset')


def _ensure():
    core_dat = op('loop_core')
    core = core_dat.module
    # TD reloads edited modules in place, so compare the source, not the object
    version = hash(core_dat.text)
    if _S['loop'] is None or _S['core'] != version:
        _S['ops'] = _ops()
        _S['core'] = version
        _S['loop'] = core.CuriosityLoop(max(1, len(_S['ops']['photos'])), _cfg())
        _S['tracker'] = Tracker()
        _S['captions'] = _load_captions(_S['ops'], core)
        _S['cap_shown'] = None
        _S['loop'].cfg['caption_layout'] = any(_S['captions'])
        if _S['ops'].get('intro_pages') is None:
            # older saved versions have no instructions page: go straight to the mirror
            _S['loop'].cfg['intro_instructions_time'] = 0.0
    return core


def update():
    now = time.perf_counter()
    dt = 1 / 60.0 if _S['last'] is None else now - _S['last']
    _S['last'] = now
    _S['dt'] = dt
    try:
        core = _ensure()
        loop, ops = _S['loop'], _S['ops']
        loop.cfg.update(_cfg())
        _S['frame'] += 1
        if _S['frame'] % 60 == 1:
            loop.set_aspects([img.width / float(img.height) if img is not None and img.height > 0 else None
                              for _, _, img in ops['photos']])
        if BASE.par.Simulate.eval():
            inp = _sim_inputs(core)
        else:
            tr = _S['tracker']
            body = tr.read_body(BASE.par.Posechop.eval(), now, dt)
            hands = tr.read_hands(BASE.par.Handchop.eval(), core, now, dt)
            inp = core.Inputs(person=body is not None,
                              body_x=body['x'] if body else (sum(h.x for h in hands) / len(hands) if hands else 0.0),
                              proximity=body['prox'] if body else 0.5,
                              body_speed=body['speed'] if body else 0.0,
                              hands=hands)
        frame = loop.update(inp, dt)
        apply(frame, ops)
    except Exception:
        if now - _S['err_t'] > 5.0:     # never spam, never stop the show
            _S['err_t'] = now
            print('[curiosity_loop] error (will keep running):')
            traceback.print_exc()


def _rect_sizes(ops):
    for i, (geo, _, img) in enumerate(ops['photos']):
        if img is None or img.height <= 0:
            continue
        rect = geo.op('rect')
        a = max(0.4, min(3.0, img.width / float(img.height)))
        if rect is not None and abs(rect.par.sizex.eval() - 1.8 * a) > 1e-3:
            rect.par.sizex = 1.8 * a
            rect.par.sizey = 1.8


def apply(fr, ops):
    if _S['frame'] % 60 == 1:
        _rect_sizes(ops)
    for (geo, mat, _), p in zip(ops['photos'], fr.photos):
        geo.par.tx, geo.par.ty, geo.par.tz = p.x, p.y, p.z
        geo.par.rz = p.rot
        geo.par.sx = geo.par.sy = p.scale
        mat.par.alpha = p.alpha
        mat.par.colorr = mat.par.colorg = mat.par.colorb = p.bright
        geo.par.render = p.alpha > 0.005
    for (geo, mat), c in zip(ops['cursors'], fr.cursors):
        if geo is None:
            continue
        geo.par.tx, geo.par.ty, geo.par.tz = c.x, c.y, 5.0
        geo.par.sx = geo.par.sy = c.size
        mat.par.alpha = c.alpha
        geo.par.render = c.alpha > 0.005
    if ops['fb_decay'] is not None:
        ops['fb_decay'].par.opacity = fr.trail
    if ops['warp'] is not None:
        w = fr.warp * 0.06
        ops['warp'].par.displaceweightx = w
        ops['warp'].par.displaceweighty = w
    # ghost webcam layer (optional)
    vid = BASE.par.Videotop.eval()
    if ops['ghost_sel'] is not None:
        if vid is not None and ops['ghost_sel'].par.top.eval() != vid:
            ops['ghost_sel'].par.top = vid.path
        ops['ghost_switch'].par.index = 1 if vid is not None else 0
        ops['ghost_level'].par.opacity = BASE.par.Ghost.eval()
    _apply_caption(fr, ops)
    if ops.get('intro_level') is not None:
        ops['intro_level'].par.opacity = getattr(fr, 'intro_alpha', 0.0)
    if ops.get('intro_pages') is not None:
        ops['intro_pages'].par.cross = getattr(fr, 'intro_page', 0.0)
    dbg = bool(BASE.par.Debug.eval())
    if ops['debug_switch'] is not None:
        ops['debug_switch'].par.index = 1 if dbg else 0
        if dbg:
            ops['debug_text'].par.text = '  '.join('%s:%s' % kv for kv in fr.info.items())


# caption column (pixels in the 1280x720 output): right of the artwork's box
CAP_X, CAP_TOP, CAP_W, CAP_GAP = 810, 150, 420, 18


def _apply_caption(fr, ops):
    title_top, body_top = ops['cap_title'], ops['cap_body']
    if title_top is None or body_top is None:
        return
    caps = _S.get('captions') or []
    idx = fr.caption_index
    cap = caps[idx] if 0 <= idx < len(caps) else None
    if cap is not None and _S.get('cap_shown') != idx:
        _S['cap_shown'] = idx
        title, body, _ = cap
        # long catalogue titles get a smaller size rather than being cut
        size = 34 if len(title) <= 40 else (26 if len(title) <= 90 else 19)
        title_top.par.fontsizex = size
        title_top.par.text = title
        body_top.par.text = body
        # put the details just under however many lines the title wraps to
        per_line = max(8, int(CAP_W / (size * 0.5)))
        lines, width = 1, 0
        for word in title.split():
            if width and width + 1 + len(word) > per_line:
                lines, width = lines + 1, len(word)
            else:
                width += (1 if width else 0) + len(word)
        ops['cap_body_over'].par.ty = -(CAP_TOP + lines * size * 1.3 + CAP_GAP)
    a = fr.caption_alpha if cap is not None else 0.0
    title_top.par.fontalpha = a
    body_top.par.fontalpha = a
    if ops.get('cap_shade') is not None:
        ops['cap_shade'].par.opacity = a


def Diagnose():
    """Print what the tracker can see. Paste this output to Claude if tracking misbehaves."""
    p = BASE.par
    for label, par, aliases, n in (('HAND', p.Handchop, HAND_ALIASES, 21), ('POSE', p.Posechop, POSE_ALIASES, 33)):
        chop = par.eval()
        print('---- %s CHOP: %s' % (label, chop.path if chop else 'NOT SET'))
        if chop is None:
            continue
        names = [c.name for c in chop.chans()]
        print('  %d chans x %d samples. first chans: %s' % (len(names), chop.numSamples, names[:12]))
        print(ChannelMap(chop, aliases, n).describe())
    tr = _S['tracker']
    if tr:
        print('range_min=%.3f absmax=%.3f mean=%s  ydown_vote=%.2f' % (tr.range_min, tr.range_absmax, tr.range_mean, tr.ydown_vote))
    if _S['loop']:
        print('state:', _S['loop'].state, ' visited:', _S['loop'].visited)
