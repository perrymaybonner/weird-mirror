"""Run with:  python3 tests/test_core.py   (no TouchDesigner needed)"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'td'))
import loop_core as L  # noqa: E402

DT = 1 / 60.0


def run(loop, seconds, make_inputs):
    fr = None
    for k in range(int(seconds / DT)):
        fr = loop.update(make_inputs(loop.t), DT)
        for p in fr.photos:
            for v in (p.x, p.y, p.z, p.rot, p.scale, p.alpha, p.bright):
                assert math.isfinite(v), 'non-finite output in %s' % loop.state
    return fr


def nobody(t):
    return L.Inputs()


def standing(t, x=0.0):
    return L.Inputs(person=True, body_x=x, proximity=0.5, body_speed=0.05)


def two_hands(t):
    return L.Inputs(person=True, body_speed=0.05, hands=[
        L.Hand(-0.4, 0.0, speed=0.2), L.Hand(0.4, 0.1, speed=0.2)])


def pointing_at(loop, i):
    sp = loop.springs[i]
    tx, ty = sp['x'].x / (L.WORLD_W / 2), sp['y'].x / (L.WORLD_H / 2)
    return lambda t: L.Inputs(person=True, hands=[
        L.Hand(tx, ty - 0.1, tip_x=tx, tip_y=ty, pointing=True, speed=0.05)])


def exploring(t):
    # hand moving side to side and toward camera
    return L.Inputs(person=True, hands=[
        L.Hand(math.sin(t * 2) * 0.5, 0.0, size=0.12 + 0.05 * math.sin(t), speed=0.8)])


def still_hand(t):
    return L.Inputs(person=True, hands=[L.Hand(0.1, 0.0, size=0.12, speed=0.0)])


def test_full_loop():
    loop = L.CuriosityLoop(16)
    fr = run(loop, 1, nobody)
    assert fr.state == L.IDLE

    fr = run(loop, 2, standing)
    assert fr.state == L.AWARENESS, fr.state
    assert fr.trail < 0.05

    fr = run(loop, 1, two_hands)
    assert fr.state == L.REVEAL, fr.state
    assert all(c.alpha == 0.0 for c in fr.cursors), 'hand dots are off by default'

    fr = run(loop, 2.0, pointing_at(loop, 5))
    assert fr.state in (L.FOCUS, L.DISTORT), fr.info
    assert loop.selected == 5, loop.selected

    fr = run(loop, 2.0, exploring)
    assert fr.state == L.DISTORT, fr.state
    sel = fr.photos[5]
    others = [p.alpha for i, p in enumerate(fr.photos) if i != 5]
    w, h = sel.scale * L.BASE_H * loop.aspects[5], sel.scale * L.BASE_H
    fill = max(w / L.WORLD_W, h / L.WORLD_H)
    assert w < L.WORLD_W and h < L.WORLD_H and 0.7 < fill <= 0.85, ('whole photo, not zoomed', w, h)
    assert 0.15 < max(others) < 0.5, 'background still shows'
    assert fr.warp == 0.0, 'no warp filter by default'

    fr = run(loop, 2.0, exploring)
    assert fr.state == L.DISTORT, 'still exploring before the 8 s hold ends'

    fr = run(loop, 3.5, still_hand)
    assert fr.state == L.FORGET, fr.info

    fr = run(loop, 4.0, lambda t: standing(t, 0.0))
    assert fr.state == L.ORBIT, fr.state
    assert fr.trail == 0.0, 'no motion trails by default'


def test_orbit_responds_more_than_awareness():
    def lean_amount(visited):
        loop = L.CuriosityLoop(16)
        loop.visited = visited
        run(loop, 3, lambda t: standing(t, 0.0))
        cx0 = sum(p.x for p in loop._compose([], DT).photos)
        run(loop, 3, lambda t: standing(t, 1.0))
        cx1 = sum(p.x for p in loop._compose([], DT).photos)
        return (cx1 - cx0) / loop.n
    a, o = lean_amount(False), lean_amount(True)
    assert o > a * 2.5 > 0, (a, o)


def test_cursor_toggle():
    loop = L.CuriosityLoop(16, {'show_cursors': True})
    run(loop, 1, standing)
    fr = run(loop, 1, two_hands)
    assert all(c.alpha > 0.1 for c in fr.cursors), 'dots show when enabled'


def _settle(loop):
    """snap every photo straight to its spiral slot (skip the springs)"""
    for i, sp in enumerate(loop.springs):
        for k, v in zip(('x', 'y', 'z', 'rot', 'scale'), loop._spiral_slot(i)):
            sp[k].x = v


def test_spiral_builds_out_then_becomes_circle():
    loop = L.CuriosityLoop(36)
    c = loop.cfg
    radii = lambda: [math.hypot(sp['x'].x / 1.15, sp['y'].x) for sp in loop.springs]

    loop.cycle_t = c['grow_time'] * 0.25          # early: only some photos are out
    visible, m = loop._cycle()
    assert 6 < visible < 12 and m == 0.0, (visible, m)
    out = [loop._presence(i, visible) for i in range(loop.n)]
    assert out[0] == 1.0 and out[-1] == 0.0, 'center photos first, outer ones later'

    loop.cycle_t = c['grow_time'] + 1.0           # full spiral
    assert loop._cycle() == (36.0, 0.0)
    _settle(loop)
    assert max(radii()) - min(radii()) > 2.5, 'spiral spans center to edge'

    loop.cycle_t = c['grow_time'] + c['spiral_hold'] + c['to_circle'] + 1.0   # ring
    assert loop._cycle() == (36.0, 1.0)
    _settle(loop)
    assert max(radii()) - min(radii()) < 0.3, 'ring: everyone on one radius'

    total = sum(c[k] for k in ('grow_time', 'spiral_hold', 'to_circle', 'circle_time', 'to_spiral', 'retract_time'))
    loop.cycle_t = total - 0.01                   # end of cycle: gathered back in
    assert loop._cycle()[0] < 0.1


def test_selection_holds_then_returns_with_caption():
    loop = L.CuriosityLoop(16, {'caption_layout': True})
    run(loop, 1, standing)
    run(loop, 1, two_hands)
    fr = run(loop, 2.0, pointing_at(loop, 3))
    assert loop.selected == 3
    fr = run(loop, 2.0, exploring)
    assert fr.state == L.DISTORT and fr.caption_index == 3 and fr.caption_alpha > 0.9
    assert fr.photos[3].x < -1.0, 'artwork moves left to make room for the caption'
    # keeps moving the whole time, but still lets go at ~8 s after selection
    fr = run(loop, 4.0, exploring)
    assert fr.state == L.DISTORT, '~6.8 s in: still showing'
    fr = run(loop, 1.5, exploring)
    assert fr.state in (L.FORGET, L.ORBIT), fr.state
    fr = run(loop, 1.0, exploring)
    assert fr.caption_alpha < 0.05, 'caption gone once it lets go'


def test_caption_formats():
    t, b = L.caption_for({'stage': 'birth', 'title': 'Morning', 'date': '1803-5',
                          'artist': 'Philipp Otto Runge', 'description': 'A print.', 'museum': 'CMA'})
    assert t == 'Morning' and b == '1803-5\nPhilipp Otto Runge\n\nA print.', b
    t, b = L.caption_for({'title': 'Spiral', 'culture': 'Etruscan', 'date': 'BCE', 'medium': 'Silver',
                          'museum': 'The Met', 'objectNumber': '95.1'})
    assert 'The Met' in b and 'Silver' in b, 'older records keep the museum caption'


def test_intro_screen():
    loop = L.CuriosityLoop(16)
    fr = run(loop, 2, nobody)
    assert fr.intro_alpha > 0.95 and fr.intro_page < 0.05, 'title page while nobody is there'
    still = lambda t: L.Inputs(person=True, body_speed=0.0)
    fr = run(loop, 1.5, still)
    assert fr.intro_alpha > 0.9 and fr.intro_page < 0.05, 'someone arrived but has not moved yet'
    fr = run(loop, 2.0, standing_moving)
    assert fr.intro_alpha > 0.9 and fr.intro_page < 0.1, 'title holds a few seconds after moving'
    fr = run(loop, 2.5, standing_moving)
    assert fr.intro_alpha > 0.9 and fr.intro_page > 0.9, 'then the instructions page'
    fr = run(loop, 6.0, standing_moving)
    assert fr.intro_alpha > 0.9, 'instructions stay up ~8 s'
    fr = run(loop, 3.5, standing_moving)
    assert fr.intro_alpha < 0.1, 'then it fades into the mirror'
    fr = run(loop, 6.0, nobody)          # leaves: mirror goes idle after person_lost_time
    assert fr.intro_alpha > 0.9 and fr.intro_page < 0.1, 'title page returns for the next visitor'
    loop2 = L.CuriosityLoop(16)
    fr = run(loop2, 18.0, still)
    assert fr.intro_alpha < 0.1, 'a person standing still is not stuck on the intro'
    loop3 = L.CuriosityLoop(16, {'intro': False})
    assert run(loop3, 1, nobody).intro_alpha == 0.0


def standing_moving(t):
    return L.Inputs(person=True, body_x=0.3 * math.sin(t * 3), proximity=0.5, body_speed=0.6)


def test_forget_returns_to_full_spiral():
    loop = L.CuriosityLoop(36)
    loop.cycle_t = 1.0                            # half-built spiral
    loop._go(L.FORGET)
    assert loop._cycle() == (36.0, 0.0)


def test_grid_fits_screen():
    for n in (12, 16, 36, 48):
        loop = L.CuriosityLoop(n)
        xs = [loop._grid_slot(i)[0] for i in range(n)]
        ys = [loop._grid_slot(i)[1] for i in range(n)]
        assert max(map(abs, xs)) < L.WORLD_W / 2 - 0.8, (n, max(xs))
        assert max(map(abs, ys)) < L.WORLD_H / 2 - 0.5, (n, max(ys))


def test_hands_leave_grid_dissolves():
    loop = L.CuriosityLoop(12)
    run(loop, 1, standing)
    run(loop, 1, two_hands)
    assert loop.state == L.REVEAL
    run(loop, 2, standing)
    assert loop.state == L.AWARENESS


def test_person_leaves_and_mirror_forgets():
    loop = L.CuriosityLoop(12)
    loop.visited = True
    run(loop, 1, standing)
    assert loop.state == L.ORBIT
    run(loop, 4, nobody)
    assert loop.state == L.IDLE
    run(loop, 9, nobody)
    assert not loop.visited
    run(loop, 1, standing)
    assert loop.state == L.AWARENESS


def test_garbage_inputs_dont_crash():
    loop = L.CuriosityLoop(3)
    bad = L.Inputs(person=True, body_x=float('nan'), proximity=float('inf'),
                   body_speed=float('nan'), hands=[L.Hand(0, 0, size=0.0, speed=float('nan'))])
    run(loop, 2, lambda t: bad)
    loop.update(bad, float('nan'))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok ', name)
