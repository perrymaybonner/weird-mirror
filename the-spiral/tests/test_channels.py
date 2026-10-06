"""Channel-name parsing tests with fake CHOPs. Run: python3 tests/test_channels.py"""
import builtins
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'td'))
builtins.parent = lambda: None      # TD globals the module touches at import
builtins.op = lambda *_: None
import loop_td as T  # noqa: E402


class Chan(list):
    def __init__(self, name, vals):
        super().__init__(vals)
        self.name = name


class FakeCHOP:
    path = '/fake'

    def __init__(self, chans):
        self._c = chans
        self.numChans = len(chans)
        self.numSamples = len(chans[0]) if chans else 0

    def chans(self):
        return self._c


def build(fmt, names, hands=(1,), samples=1):
    out = []
    for h in hands:
        for i, n in enumerate(names):
            for ax in 'xyz':
                out.append(Chan(fmt.format(h=h, n=n, i=i, ax=ax), [0.1 * h + i * 0.01] * samples))
    return FakeCHOP(out)


def check(fmt, hands=(1, 2)):
    chop = build(fmt, T.HAND_NAMES, hands)
    m = T.ChannelMap(chop, T.HAND_ALIASES, 21)
    got = m.read(chop)
    assert sorted(got) == sorted(hands), (fmt, sorted(got))
    for h in hands:
        assert sorted(got[h]) == list(range(21)), (fmt, h, sorted(got[h]))
        assert abs(got[h][8][0] - (0.1 * h + 0.08)) < 1e-9, fmt
    print('ok ', fmt)


for fmt in ('h{h}:{n}:{ax}', 'hand{h}_{n}_{ax}', 'h{h}/{n}:t{ax}', 'hand_{h}_{i}_{ax}', 'h{h}:landmark{i}:{ax}'):
    check(fmt)
check('{n}_{ax}', hands=(0,))

# pose naming, incl. names that contain other names (left_eye vs left_eye_inner)
chop = build('p{h}:{n}:{ax}', T.POSE_NAMES, (1,))
got = T.ChannelMap(chop, T.POSE_ALIASES, 33).read(chop)[1]
assert sorted(got) == list(range(33)), sorted(got)
print('ok  pose names')

# sample layout: one channel per axis, 21 samples
chop = FakeCHOP([Chan('h1:' + ax, [i * 0.01 for i in range(21)]) for ax in 'xyz'])
got = T.ChannelMap(chop, T.HAND_ALIASES, 21).read(chop)
assert sorted(got[1]) == list(range(21)), got
print('ok  sample layout')

# gesture/handedness channels are kept as extras, not landmarks
chop = FakeCHOP([Chan('h1:gesture_pointing_up', [1]), Chan('h1:wrist:x', [.5]), Chan('h1:wrist:y', [.5])])
m = T.ChannelMap(chop, T.HAND_ALIASES, 21)
assert 'h1gesturepointingup' in m.extra[1], m.extra
print('ok  extras')
