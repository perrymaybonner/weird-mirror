"""
Curiosity Loop - core behaviour.

Pure Python (no TouchDesigner imports) so it can be unit-tested outside TD.
TouchDesigner-specific code lives in loop_td.py, which feeds `Inputs` in and
applies the returned `Frame` to operators every frame.

Coordinate conventions
----------------------
Input (from loop_td):  "screen-normalized" -1..1, x right +, y up +,
                       already mirrored so moving right = +x on screen.
World (render):        orthographic camera, WORLD_W x WORLD_H units,
                       origin at screen centre.
"""

import math
import random

WORLD_W = 16.0
WORLD_H = 9.0
BASE_H = 1.8           # photo height in world units at scale 1

IDLE, AWARENESS, REVEAL, FOCUS, DISTORT, FORGET, ORBIT = (
    'idle', 'awareness', 'reveal', 'focus', 'distort', 'forget', 'orbit')

DEFAULTS = {
    # --- person / spiral ---
    'awareness_gain': 0.3,      # how strongly the spiral follows you on first contact
    'orbit_gain': 1.0,          # ...and after you've "been remembered"
    'spin': 0.08,               # base spiral rotation, rad/s
    # idle cycle: build the spiral out -> hold -> open to a circle -> rotate -> gather back
    'grow_time': 12.0,          # s for photos to spiral out one by one from the center
    'spiral_hold': 3.0,         # s the full spiral turns before opening
    'to_circle': 3.0,           # s for the spiral to unwind into a ring
    'circle_time': 8.0,         # s the ring rotates
    'to_spiral': 2.5,           # s for the ring to wind back into a spiral
    'retract_time': 5.0,        # s for photos to pull back into the center, outermost first
    'circle_spin': 2.5,         # the ring turns this many times faster than the spiral
    'spiral_turns': 1.75,        # how many times the spiral winds around
    'show_cursors': False,      # soft dots under the hands during Reveal
    # --- intro screen ---
    'intro': True,              # black title screen until someone enters and moves
    'intro_motion': 0.15,       # movement that counts as "starts moving"
    'intro_max_wait': 4.0,      # s a still person waits before it fades anyway
    'intro_fade_out': 1.5,      # s for the black to fade into the mirror
    'intro_fade_in': 2.0,       # s for it to return once nobody is there
    'intro_title_hold': 3.0,    # s the title stays up after someone starts moving
    'intro_instructions_time': 8.0,  # s the "raise hands / point to select" page shows before the mirror
    'person_lost_time': 3.0,    # s without a person before going idle
    'forget_visitor_time': 8.0, # s idle before the mirror forgets you were here
    # --- reveal ---
    'two_hand_time': 0.25,      # s both hands must be visible to snap to grid
    'one_hand_time': 1.5,       # s one raised hand also reveals (0 = disabled)
    'hands_lost_time': 1.5,     # s without hands before grid dissolves
    # --- focus ---
    'dwell_time': 1.2,          # s of pointing at one photo to select it
    'hover_dwell_time': 0.0,    # s of open-hand hover to select (0 = pointing only)
    'focus_time': 1.6,          # s for the chosen photo to separate and fill
    # --- distort ---
    'grace_time': 3.0,          # s in distort before stillness counts
    'still_threshold': 0.12,    # motion below this counts as "still"
    'still_time': 2.5,          # s of stillness before the mirror lets go
    'max_distort_time': 30.0,
    'zoom_min': 1.0,
    'zoom_max': 1.0,            # >1 lets hand distance zoom in (off: show the whole photo)
    'focus_fill': 0.8,          # selected photo fills this much of the screen, uncropped
    'select_hold': 8.0,         # s a selected artwork stays up (with its caption) before returning
    'still_exit': False,        # True: holding still also ends the selection early
    'caption_layout': False,    # True: artwork moves left to leave room for a caption on the right
    'caption_box': 0.56,        # width fraction the artwork gets when a caption is shown
    'focus_drift': 0.6,         # world units the photo drifts with your hand
    'warp_amount': 0.0,         # velocity warp / wobble while exploring (0 = clean image)
    'focus_others_alpha': 0.3,  # how visible the rest of the collection stays behind it
    # --- forget ---
    'forget_time': 3.5,
    # --- look ---
    'orbit_trail': 0.0,         # motion trails in orbit (0 = off; ~0.8 = long smears)
}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(cur, target, dt, tau):
    """Frame-rate independent exponential smoothing."""
    if tau <= 0:
        return target
    return cur + (target - cur) * (1.0 - math.exp(-dt / tau))


def finite(v, fallback=0.0):
    return v if isinstance(v, (int, float)) and math.isfinite(v) else fallback


def caption_for(record):
    """(title, body) for a museum record, using the museum's own wording.

    Only fields the museum provided are shown; nothing is filled in or reworded.
    Exhibition records (with a 'stage'): date, artist, then the short description.
    Older artwork records: maker (or culture), date, culture, medium, museum, object number.
    """
    if not record:
        return None, None

    def f(key):
        v = record.get(key)
        return v.strip() if isinstance(v, str) and v.strip() else None

    if record.get('stage'):
        # exhibition records: title / date / artist / short description
        body = [l for l in (f('date'), f('artist') or f('maker') or f('culture')) if l]
        if f('description'):
            body += ['', f('description')]
        return f('title'), '\n'.join(body)

    maker, culture = f('maker'), f('culture')
    lines = [maker or culture, f('date')]
    if maker and culture and culture not in maker:
        lines.append(culture)
    lines.append(f('medium'))
    body = [l for l in lines if l]
    tail = [l for l in (f('museum'), f('objectNumber')) if l]
    if tail:
        body += [''] + tail
    return f('title'), '\n'.join(body)


class Hand:
    __slots__ = ('x', 'y', 'tip_x', 'tip_y', 'size', 'pointing', 'speed')

    def __init__(self, x=0.0, y=0.0, tip_x=None, tip_y=None, size=0.1,
                 pointing=False, speed=0.0):
        self.x, self.y = x, y
        self.tip_x = x if tip_x is None else tip_x
        self.tip_y = y if tip_y is None else tip_y
        self.size, self.pointing, self.speed = size, pointing, speed


class Inputs:
    def __init__(self, person=False, body_x=0.0, proximity=0.5,
                 body_speed=0.0, hands=None):
        self.person = person
        self.body_x = body_x          # -1..1
        self.proximity = proximity    # 0 far .. 1 close
        self.body_speed = body_speed  # screen units / s
        self.hands = hands or []


class PhotoOut:
    __slots__ = ('x', 'y', 'z', 'rot', 'scale', 'alpha', 'bright')


class CursorOut:
    __slots__ = ('x', 'y', 'size', 'alpha')


class Frame:
    def __init__(self):
        self.photos = []
        self.cursors = []
        self.trail = 0.0
        self.warp = 0.0
        self.caption_index = -1     # which artwork's caption to show (-1 = none)
        self.caption_alpha = 0.0
        self.intro_alpha = 0.0      # black title screen over everything (1 = shown)
        self.intro_page = 0.0       # 0 = title page, 1 = instructions page (crossfade)
        self.state = IDLE
        self.info = {}


class _Spring:
    """Damped spring for one scalar. Gives the 'snap' with slight overshoot."""
    __slots__ = ('x', 'v')

    def __init__(self, x=0.0):
        self.x, self.v = x, 0.0

    def step(self, target, dt, k, c):
        self.v += ((target - self.x) * k - self.v * c) * dt
        self.x += self.v * dt
        return self.x


# stiffness / damping presets per feel
SNAP = (140.0, 16.0)    # grid snap: fast, slight overshoot
FOLLOW = (40.0, 12.0)   # tracking the body / hands
SLOW = (9.0, 6.0)       # focus separation
DRIFT = (4.0, 4.2)      # forgetting


class CuriosityLoop:
    def __init__(self, num_photos, config=None, seed=7):
        self.cfg = dict(DEFAULTS)
        if config:
            self.cfg.update(config)
        self.n = max(1, int(num_photos))
        self.aspects = [4.0 / 3.0] * self.n
        rnd = random.Random(seed)
        self.jitter = [rnd.uniform(-1, 1) for _ in range(self.n)]
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self):
        self.state = IDLE
        self.t = 0.0
        self.state_t = 0.0
        self.visited = False
        self.selected = -1
        self.hovered = -1
        self.charge = 0.0
        self.two_hand_t = 0.0
        self.one_hand_t = 0.0
        self.no_hands_t = 0.0
        self.no_person_t = 0.0
        self.still_t = 0.0
        self.motion = 0.0
        self.spiral_angle = 0.0
        self.cycle_t = 0.0
        self.enter_kick = 0.0
        self.had_person = False
        # smoothed person-driven values
        self.s_cx = 0.0
        self.s_lean = 0.0
        self.s_expand = 1.0
        self.s_size = 1.0
        # grid layout (held while pointing)
        self.g_spacing = 1.0
        self.g_angle = 0.0
        self.g_ox = 0.0
        self.g_oy = 0.0
        # distort
        self.ref_size = None
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.warp = 0.0
        self.trail = 0.0
        self.caption_alpha = 0.0
        self.intro_on = True
        self.intro_alpha = 1.0
        self.intro_phase = 'title'  # title -> instructions -> off
        self.intro_phase_t = 0.0
        self.intro_page = 0.0
        self.person_t = 0.0
        self.springs = [{k: _Spring() for k in ('x', 'y', 'z', 'rot', 'scale', 'alpha', 'bright')}
                        for _ in range(self.n)]
        for i, sp in enumerate(self.springs):
            x, y, z, rot, sc = self._spiral_slot(i)
            sp['x'].x, sp['y'].x, sp['z'].x, sp['rot'].x, sp['scale'].x = x, y, z, rot, sc
            sp['alpha'].x = self._presence(i, self._cycle()[0])
            sp['bright'].x = 0.7
        self.cursor_springs = [{k: _Spring() for k in ('x', 'y', 'size', 'alpha')} for _ in range(2)]

    def set_aspects(self, aspects):
        for i, a in enumerate(aspects[:self.n]):
            if a and a > 0:
                self.aspects[i] = clamp(float(a), 0.4, 3.0)

    def _go(self, state):
        if state == self.state:
            return
        self.state = state
        self.state_t = 0.0
        if state == REVEAL:
            self.charge = 0.0
            self.hovered = -1
            self.no_hands_t = 0.0
        elif state == FOCUS:
            self.visited = True
        elif state == DISTORT:
            self.ref_size = None
            self.still_t = 0.0
            self.zoom = 1.0
            self.pan_x = self.pan_y = 0.0
        elif state == FORGET:
            self.charge = 0.0
            self.hovered = -1
            # the collection comes back as a full spiral, not a half-built one
            self.cycle_t = self.cfg['grow_time']
        elif state == ORBIT:
            self.selected = -1

    # --------------------------------------------------------------- layouts
    def _focus_scale(self, i):
        """largest scale that shows the whole photo inside its box, uncropped"""
        w = BASE_H * self.aspects[i]
        fill = clamp(self.cfg['focus_fill'], 0.2, 1.0)
        box_w = WORLD_W * (self.cfg['caption_box'] if self.cfg['caption_layout'] else fill)
        return min(box_w / w, WORLD_H * fill / BASE_H)

    def _focus_x(self):
        """centre of the artwork's box: left of centre when a caption shares the screen"""
        if not self.cfg['caption_layout']:
            return 0.0
        margin = 0.6
        return -WORLD_W * 0.5 + margin + WORLD_W * self.cfg['caption_box'] * 0.5

    def _cover_scale(self, i):
        w = BASE_H * self.aspects[i]
        return max(WORLD_W / w, WORLD_H / BASE_H) * 1.12

    def _cycle(self):
        """-> (visible, m): how many photos are out (0..n, fractional) and
        0 = spiral .. 1 = circle, for the current point in the idle cycle."""
        c = self.cfg
        spans = [c['grow_time'], c['spiral_hold'], c['to_circle'], c['circle_time'],
                 c['to_spiral'], c['retract_time']]
        spans = [max(v, 0.01) for v in spans]
        tc = self.cycle_t % sum(spans)
        n = float(self.n)
        ease = lambda u: u * u * (3.0 - 2.0 * u)
        for k, span in enumerate(spans):
            if tc < span or k == len(spans) - 1:
                u = clamp(tc / span, 0.0, 1.0)
                break
            tc -= span
        if k == 0:
            return n * u, 0.0                   # building out
        if k == 1:
            return n, 0.0                       # full spiral
        if k == 2:
            return n, ease(u)                   # opening into a circle
        if k == 3:
            return n, 1.0                       # rotating ring
        if k == 4:
            return n, 1.0 - ease(u)             # winding back
        return n * (1.0 - u), 0.0               # gathering in, outermost first

    def _presence(self, i, visible):
        """0 = still hidden in the center, 1 = out in its slot."""
        u = clamp(visible - i, 0.0, 1.0)
        return u * u * (3.0 - 2.0 * u)

    def _spiral_slot(self, i):
        f = (i + 0.5) / self.n
        visible, m = self._cycle()
        a = self._presence(i, visible)
        big = (0.9 + 0.1 * (1.0 - m)) * self.s_expand * (1.0 + self.enter_kick)
        # spiral: radius grows with f, winding several turns
        r_s = (1.0 + 3.1 * f) * big      # open center, no pile-up
        a_s = f * self.cfg['spiral_turns'] * 2.0 * math.pi
        # circle: everyone on one ring, evenly spaced
        r_c = 3.7 * big
        a_c = f * 2.0 * math.pi
        r = lerp(r_s, r_c, m) * a               # new photos slide out from the center
        ang = lerp(a_s, a_c, m) + self.spiral_angle
        x = r * math.cos(ang) * 1.15
        y = r * math.sin(ang)
        # lean: shear the spiral sideways, more at the top
        x += self.s_cx + self.s_lean * (y + WORLD_H * 0.5) * 0.6
        rot = math.degrees(self.s_lean) * 0.6 + self.jitter[i] * 6.0
        size_n = math.sqrt(16.0 / self.n)           # more photos -> smaller photos
        scale = lerp(0.3 + 0.3 * (1.0 - f), 0.42, m) * size_n * self.s_size * max(a, 0.02)
        z = lerp(1.0 - f, 0.5, m) + 0.001 * i
        return x, y, z, rot, scale

    def _grid_dims(self):
        cols = max(1, int(math.ceil(math.sqrt(self.n * 1.6))))
        rows = int(math.ceil(self.n / float(cols)))
        return cols, rows

    def _grid_fit(self):
        """cell width that keeps every photo on screen, however many there are"""
        cols, rows = self._grid_dims()
        return min(2.25, 13.0 / cols, 6.8 / (rows * 0.78))

    def _grid_slot(self, i):
        cols, rows = self._grid_dims()
        c, r = i % cols, i // cols
        fit = self._grid_fit()
        cw, ch = fit * self.g_spacing, fit * 0.78 * self.g_spacing
        gx = (c - (cols - 1) / 2.0) * cw
        gy = ((rows - 1) / 2.0 - r) * ch
        ca, sa = math.cos(self.g_angle), math.sin(self.g_angle)
        x = gx * ca - gy * sa + self.g_ox
        y = gx * sa + gy * ca + self.g_oy
        return x, y, 0.5, math.degrees(self.g_angle), 0.72 * fit / 2.25

    # ----------------------------------------------------------------- update
    def update(self, inp, dt):
        dt = clamp(finite(dt, 1 / 60.0), 1e-4, 1 / 20.0)
        cfg = self.cfg
        self.t += dt
        self.state_t += dt
        hands = [h for h in (inp.hands or []) if h is not None][:2]
        nh = len(hands)
        person = bool(inp.person) or nh > 0

        body_speed = finite(inp.body_speed)
        hand_speed = max([finite(h.speed) for h in hands] or [0.0])
        self.motion = smooth(self.motion, body_speed + hand_speed, dt, 0.35)

        # --- presence bookkeeping
        self.no_person_t = 0.0 if person else self.no_person_t + dt
        self.person_t = self.person_t + dt if person else 0.0
        if person and not self.had_person and self.state in (IDLE, AWARENESS, ORBIT):
            self.enter_kick = 0.18   # a tiny "breath" when someone arrives
        self.had_person = person
        self.enter_kick = smooth(self.enter_kick, 0.0, dt, 0.8)
        self.two_hand_t = self.two_hand_t + dt if nh >= 2 else 0.0
        self.one_hand_t = self.one_hand_t + dt if nh == 1 else 0.0
        self.no_hands_t = self.no_hands_t + dt if nh == 0 else 0.0

        # --- spiral drivers (person position)
        gain = 0.0
        if self.state in (AWARENESS, REVEAL) or (self.state == IDLE and person):
            gain = cfg['awareness_gain']
        elif self.state in (ORBIT, FORGET, FOCUS, DISTORT):
            gain = cfg['orbit_gain'] if self.visited else cfg['awareness_gain']
        if not person:
            gain = 0.0
        bx = clamp(finite(inp.body_x), -1.0, 1.0)
        prox = clamp(finite(inp.proximity, 0.5), 0.0, 1.0)
        orbit_mode = self.visited and self.state in (ORBIT, FORGET)
        self.s_cx = smooth(self.s_cx, gain * bx * WORLD_W * 0.28, dt, 0.5)
        self.s_lean = smooth(self.s_lean, gain * bx * 0.35, dt, 0.6)
        self.s_expand = smooth(self.s_expand, 1.0 + gain * (prox - 0.5) * 0.7, dt, 0.6)
        self.s_size = smooth(self.s_size, 1.0 + (gain * (prox - 0.5) * 1.1 if orbit_mode else 0.0), dt, 0.6)
        self.cycle_t += dt
        m = self._cycle()[1]
        self.spiral_angle += dt * (cfg['spin'] * (1.0 + (cfg['circle_spin'] - 1.0) * m)
                                  + gain * clamp(self.motion, 0.0, 2.0) * 0.5)

        # --- state machine
        s = self.state
        if s in (IDLE, AWARENESS, ORBIT):
            if s == IDLE and person:
                self._go(ORBIT if self.visited else AWARENESS)
            elif s != IDLE and self.no_person_t > cfg['person_lost_time']:
                self._go(IDLE)
            elif s == IDLE and self.visited and self.state_t > cfg['forget_visitor_time']:
                self.visited = False   # slip back into ambiguity for the next visitor
            if self.state != IDLE and (
                    self.two_hand_t >= cfg['two_hand_time'] or
                    (cfg['one_hand_time'] > 0 and self.one_hand_t >= cfg['one_hand_time'])):
                self._go(REVEAL)
        elif s == REVEAL:
            self._update_reveal(hands, dt)
        elif s == FOCUS:
            if self.state_t >= cfg['focus_time']:
                self._go(DISTORT)
        elif s == DISTORT:
            self._update_distort(hands, dt)
        elif s == FORGET:
            if self.state_t >= cfg['forget_time']:
                self._go(ORBIT)

        # visual memory: trails only once you've been "remembered"
        trail_target = cfg['orbit_trail'] if (self.visited and self.state == ORBIT) else 0.0
        self.trail = smooth(self.trail, trail_target, dt, 1.5)
        if self.state != DISTORT:
            self.warp = smooth(self.warp, 0.0, dt, 0.3)

        return self._compose(hands, dt)

    # ----------------------------------------------------------- reveal/focus
    def _cursor_world(self, h):
        return h.tip_x * WORLD_W * 0.5, h.tip_y * WORLD_H * 0.5

    def _update_reveal(self, hands, dt):
        cfg = self.cfg
        if self.no_hands_t >= cfg['hands_lost_time']:
            self._go(ORBIT if self.visited else AWARENESS)
            return
        pointing = [h for h in hands if h.pointing]

        # grid layout follows hands - frozen while pointing so you can aim
        if not pointing and hands:
            if len(hands) >= 2:
                a, b = sorted(hands[:2], key=lambda h: h.x)
                d = math.hypot(b.x - a.x, b.y - a.y)
                # never below ~1: photos are 77% of a cell, so smaller spacing overlaps them
                spacing = lerp(0.95, 1.25, clamp((d - 0.4) / 1.0, 0.0, 1.0))
                angle = clamp(math.atan2(b.y - a.y, b.x - a.x), -0.6, 0.6) * 0.8
                mx, my = (a.x + b.x) * 0.5, (a.y + b.y) * 0.5
            else:
                spacing, angle = 1.0, 0.0
                mx, my = hands[0].x * 0.5, hands[0].y * 0.5
            self.g_spacing = smooth(self.g_spacing, spacing, dt, 0.25)
            self.g_angle = smooth(self.g_angle, angle, dt, 0.25)
            self.g_ox = smooth(self.g_ox, mx * WORLD_W * 0.18, dt, 0.25)
            self.g_oy = smooth(self.g_oy, my * WORLD_H * 0.18, dt, 0.25)

        # which photo is the user aiming at?
        aim = pointing[0] if pointing else (hands[0] if (hands and cfg['hover_dwell_time'] > 0) else None)
        target = -1
        if aim is not None:
            cx, cy = self._cursor_world(aim)
            best, best_d = -1, 1e9
            for i, sp in enumerate(self.springs):
                d = math.hypot(sp['x'].x - cx, sp['y'].x - cy)
                if d < best_d:
                    best, best_d = i, d
            if best_d < 0.6 * self._grid_fit() * self.g_spacing:
                target = best

        if target >= 0 and target == self.hovered:
            dwell = cfg['dwell_time'] if pointing else cfg['hover_dwell_time']
            self.charge += dt / max(dwell, 0.05)
        elif target >= 0:
            self.hovered, self.charge = target, 0.0
        else:
            # brief tracking dropouts shouldn't reset the aim instantly
            self.charge = max(0.0, self.charge - dt * 2.0)
            if self.charge <= 0.0:
                self.hovered = -1
        if self.charge >= 1.0 and self.hovered >= 0:
            self.selected = self.hovered
            self._go(FOCUS)

    def _update_distort(self, hands, dt):
        cfg = self.cfg
        if hands:
            h = max(hands, key=lambda q: q.size)
            if self.ref_size is None:
                self.ref_size = max(h.size, 1e-3)
            ratio = h.size / self.ref_size
            zoom = clamp(ratio ** 1.5, cfg['zoom_min'], cfg['zoom_max'])
            self.zoom = smooth(self.zoom, zoom, dt, 0.35)
            # pan across the whole image, but never past its edges
            # zoomed past the screen: pan across it; otherwise drift gently with the hand
            sc = self._focus_scale(self.selected) * self.zoom
            over_x = (BASE_H * self.aspects[self.selected] * sc - WORLD_W) * 0.5
            over_y = (BASE_H * sc - WORLD_H) * 0.5
            hx, hy = clamp(h.x, -1.0, 1.0), clamp(h.y, -1.0, 1.0)
            if over_x > 0 or over_y > 0:
                tx, ty = -hx * max(over_x, 0.0), -hy * max(over_y, 0.0)
            else:
                tx, ty = hx * cfg['focus_drift'], hy * cfg['focus_drift'] * 0.6
            self.pan_x = smooth(self.pan_x, tx, dt, 0.4)
            self.pan_y = smooth(self.pan_y, ty, dt, 0.4)
            self.warp = smooth(self.warp, clamp(h.speed * 0.6, 0.0, 1.0) * cfg['warp_amount'], dt, 0.12)
        else:
            self.warp = smooth(self.warp, 0.0, dt, 0.3)

        if self.state_t > cfg['grace_time']:
            if self.motion < cfg['still_threshold'] or not hands:
                self.still_t += dt
            else:
                self.still_t = 0.0
        # the artwork (and its caption) stays up for select_hold seconds in total, then lets go
        held = self.state_t + cfg['focus_time']
        if (held >= cfg['select_hold'] or self.state_t >= cfg['max_distort_time']
                or (cfg['still_exit'] and self.still_t >= cfg['still_time'])):
            self._go(FORGET)

    # ---------------------------------------------------------------- compose
    def _compose(self, hands, dt):
        s = self.state
        fr = Frame()
        fr.state = s
        spring = SNAP if s == REVEAL else FOLLOW
        for i, sp in enumerate(self.springs):
            if s == REVEAL:
                x, y, z, rot, sc = self._grid_slot(i)
                alpha, bright = 1.0, 0.85
                if i == self.hovered:
                    sc *= 1.1 + 0.3 * self.charge
                    z += 1.0
                    bright = 0.85 + 0.15 * self.charge
                elif self.hovered >= 0:
                    bright = 0.85 - 0.3 * self.charge
                prof = spring
            elif s in (FOCUS, DISTORT) and i == self.selected:
                x, y, rot = self._focus_x(), 0.0, 0.0
                z = 3.0
                sc = self._focus_scale(i)
                alpha, bright = 1.0, 1.0
                prof = SLOW
                if s == DISTORT:
                    sc *= self.zoom
                    x, y = self._focus_x() + self.pan_x, self.pan_y
                    rot = self.warp * 4.0 * math.sin(self.t * 7.0)
                    prof = FOLLOW
            elif s in (FOCUS, DISTORT):
                x, y, z, rot, sc = self._grid_slot(i)
                sc *= 0.9
                alpha, bright = self.cfg['focus_others_alpha'], 0.45
                prof = SLOW
            else:
                x, y, z, rot, sc = self._spiral_slot(i)
                # during Forget the chosen photo stays visible until it's home
                alpha = 1.0 if (s == FORGET and i == self.selected) else self._presence(i, self._cycle()[0])
                bright = 0.55 if s == IDLE else 0.75
                prof = DRIFT if s == FORGET else FOLLOW
                if s == FORGET and i == self.selected:
                    z = 3.0
            k, c = prof
            o = PhotoOut()
            o.x = sp['x'].step(x, dt, k, c)
            o.y = sp['y'].step(y, dt, k, c)
            o.z = sp['z'].step(z, dt, k * 2, c * 1.4)
            o.rot = sp['rot'].step(rot, dt, k, c)
            o.scale = max(0.01, sp['scale'].step(sc, dt, k, c))
            # quick fade-in on reveal so the grid arrives at once; slow elsewhere
            a_prof = DRIFT if s == FORGET else (FOLLOW if s == REVEAL else SLOW)
            o.alpha = clamp(sp['alpha'].step(alpha, dt, *a_prof), 0.0, 1.0)
            o.bright = clamp(sp['bright'].step(bright, dt, *SLOW), 0.0, 1.5)
            fr.photos.append(o)

        # cursors: only while the grid is up - they're the "I see your hand" hint
        for idx in range(2):
            cs = self.cursor_springs[idx]
            h = hands[idx] if idx < len(hands) else None
            vis = s == REVEAL and h is not None
            if h is not None:
                tx, ty = self._cursor_world(h)
            else:
                tx, ty = cs['x'].x, cs['y'].x
            aiming = h is not None and (h.pointing or len(hands) == 1)
            size = 0.12 + (0.25 * (1.0 - self.charge) if aiming else 0.1)
            alpha = (0.85 if (h is not None and h.pointing) else 0.35) if vis else 0.0
            if not self.cfg['show_cursors']:
                alpha = 0.0
            co = CursorOut()
            co.x = cs['x'].step(tx, dt, *FOLLOW)
            co.y = cs['y'].step(ty, dt, *FOLLOW)
            co.size = max(0.01, cs['size'].step(size, dt, *FOLLOW))
            co.alpha = clamp(cs['alpha'].step(alpha, dt, *SLOW), 0.0, 1.0)
            fr.cursors.append(co)

        # intro: title page while nobody is here; once someone is here AND moving (or has
        # stood there a while) it crossfades to the instructions page, then fades into the
        # mirror. It comes back once the mirror goes idle, ready for the next visitor.
        c = self.cfg
        self.intro_phase_t += dt
        if not c['intro']:
            self.intro_phase = 'off'
        elif s == IDLE:
            if self.intro_phase != 'title':
                self.intro_phase, self.intro_phase_t = 'title', 0.0
        elif self.intro_phase == 'title' and self.person_t > 0.3 and (
                self.motion > c['intro_motion'] or self.person_t > c['intro_max_wait']):
            self.intro_phase, self.intro_phase_t = 'title_hold', 0.0
        elif self.intro_phase == 'title_hold' and self.intro_phase_t >= c['intro_title_hold']:
            self.intro_phase, self.intro_phase_t = 'instructions', 0.0
        elif self.intro_phase == 'instructions' and self.intro_phase_t >= c['intro_instructions_time']:
            self.intro_phase, self.intro_phase_t = 'off', 0.0
        self.intro_on = self.intro_phase != 'off'
        tau = (c['intro_fade_in'] if self.intro_on else c['intro_fade_out']) / 3.0
        self.intro_alpha = smooth(self.intro_alpha, 1.0 if self.intro_on else 0.0, dt, tau)
        page_target = (0.0 if self.intro_phase in ('title', 'title_hold')
                       else 1.0 if self.intro_phase == 'instructions' else self.intro_page)
        self.intro_page = smooth(self.intro_page, page_target, dt, 0.35)
        fr.intro_alpha = self.intro_alpha if c['intro'] else 0.0
        fr.intro_page = self.intro_page

        # caption: fades in once the artwork has mostly arrived, out as soon as it lets go
        showing = (s == DISTORT) or (s == FOCUS and self.state_t > self.cfg['focus_time'] * 0.6)
        self.caption_alpha = smooth(getattr(self, 'caption_alpha', 0.0), 1.0 if showing else 0.0,
                                    dt, 0.35 if showing else 0.2)
        fr.caption_index = self.selected if self.caption_alpha > 0.01 else -1
        fr.caption_alpha = self.caption_alpha if fr.caption_index >= 0 else 0.0
        fr.trail = self.trail
        fr.warp = self.warp
        fr.info = {
            'state': s, 'visited': self.visited, 'hands': len(hands),
            'selected': self.selected, 'hovered': self.hovered,
            'charge': round(self.charge, 2), 'motion': round(self.motion, 3),
            'still_t': round(self.still_t, 2), 'zoom': round(self.zoom, 2),
        }
        return fr
