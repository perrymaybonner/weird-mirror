# Curiosity Loop

*A weird mirror that seems alive but passive, quietly teaches you how to play with it, rewards you for exploring, and then lets go.*

IXD415 — Weird Mirror · TouchDesigner 2025 + MediaPipe (webcam only)

```
PERSON → CURIOUS → EXPERIMENTS → DISCOVERS → EXPLORES → SYSTEM LETS GO → CURIOUS AGAIN
```

**Intro (from the Figma design):** while nobody is there the screen shows the title page, **THE SPIRAL** / *a continuous movement through states of being, life, death, transformation, return*, in Inter. When someone enters the frame and starts moving (or has stood there ~4 s), the title holds ~3 s more, then crossfades to the instructions page (**raise hands** over two open hands, **point to select** over a pointing hand) for ~8 s, then fades into the mirror. A very faint mirror of the visitor (15%, **Mirror Behind Intro**) shows behind both pages; the artworks stay hidden until the intro ends. It returns once the mirror goes idle. Title, subtitle and on/off switch are on `curiosity_loop`'s **Intro** page; the hand images are in `intro/`, the Inter font (SIL Open Font License) in `fonts/`.

| # | Stage | Trigger | What you see |
|---|-------|---------|--------------|
| 1 | **Awareness** | a body enters the frame | Photos drift in a loose spiral that "breathes" once when you arrive, then shifts slightly with your position, distance and movement |
| 2 | **Reveal** | both hands up (or one hand held ~1.5 s) | Photos snap into a grid. Hand distance sets spacing, the tilt between your hands rotates it, and their midpoint moves it. Soft dots show where your hands are |
| 3 | **Focus** | point at an artwork for ~1.2 s | The grid freezes so you can aim. The target lifts as it "charges", then moves to the left of the screen, uncropped, and a museum caption fades in on the right: title, maker, date, culture, medium, museum, object number |
| 4 | **Exploration** | move your hand | The artwork drifts gently with your hand while the caption stays up |
| 5 | **Forget** | automatically, 8 s after selecting | The caption fades, the artwork shrinks back into the collection, and the spiral returns |
| 6 | **Orbit** | automatically | The spiral returns, now reacting strongly: it leans with you, and photos grow or shrink with your distance. After 8 s with nobody there, it forgets and returns to the subtle stage 1 |

## Open it

Double-click **Curiosity Loop** on the Desktop for the working version, or **Curiosity Loop - Spiral Artworks** for the frozen artwork-and-captions version (`curiosity_loop_v2_artworks.toe`). Other snapshots: `curiosity_loop_v1.toe` (my own photos) and `curiosity_loop_firstrun.toe`. It's a Finder alias to `curiosity_loop_final.toe` in this folder, which is the approved version. TouchDesigner opens it, starts the timeline, and pops up the output window after about 1.5 s. Keep the `.toe` inside this folder: it finds `td/` and `photos/` relative to itself, so a plain copy elsewhere would break.

## Folder layout

```
curiosity-loop/
  td/loop_core.py      behaviour + state machine (pure Python, unit-tested)
  td/loop_td.py        TouchDesigner glue: reads MediaPipe, drives the nodes
  td/build.py          builds the whole network from the Textport
  photos/              your images (placeholders included)
  tools/make_placeholders.py
  tests/               run without TouchDesigner: python3 tests/test_core.py
```

Both `.py` files are linked to Text DATs with **Sync to File** turned on. If you edit them in VS Code, TouchDesigner reloads them live, and your git history shows real code diffs.

---

## 1. Build the network (5 min, no camera needed)

1. Open TouchDesigner. Choose **File → New**, then **File → Save As…** and save as `curiosity_loop.toe` **inside this `curiosity-loop` folder**.
2. Open the Textport (**Dialogs → Textport and DATs**, or Alt+T) and paste:
   ```python
   exec(open(project.folder + '/td/build.py', encoding='utf-8').read())
   ```
3. You should see `== Curiosity Loop built: 16 photos`. Parameter warnings, if any, are printed after that line.
4. Double-click `/project1/curiosity_loop` to look inside, or view its output on the node tile.

## 2. Test with the simulator

Select `curiosity_loop`. On its **Simulate** page, **Simulate** is on by default. Try this sequence:

| Do this | Expect |
|---|---|
| Turn **Person Present** on, then drag **Body X** / **Proximity** | The spiral follows you slightly (Awareness) |
| Set **Hands Visible** to 2, then drag Hand 1 X / Hand 2 X / Hand 2 Y | The grid snaps in, then spreads and tilts |
| Move **Hand 1 X/Y** over a photo, then turn **Hand 1 Pointing** on | The photo charges and fills the screen |
| Drag **Hand Size** and **Hand 1 X** | Zoom, pan and warp |
| Stop touching everything | After about 2.5 s it forgets and returns to Orbit, with trails |

Turn on **Input → Debug Overlay** to print the current state on screen.

## 3. Install MediaPipe and connect the camera

1. Download `release.zip` from https://github.com/torinmb/mediapipe-touchdesigner/releases (v0.5.3 supports TD 2025) and unzip it **outside** this repo.
2. From its `toxes/` folder, drag **MediaPipe.tox** into `/project1`. When prompted, choose **Enable External .tox**, which keeps your .toe small.
3. On the MediaPipe COMP, pick your webcam. Make sure hand tracking **and** pose tracking are enabled on its parameter pages, and turn the other models (face, etc.) off to save CPU.
4. Drag in **hand_tracking.tox** and **pose_tracking.tox**. They wire themselves to the `MediaPipe` operator automatically.
5. Put a **Null CHOP** after the landmark CHOP output of each helper, e.g. `hands_null` and `pose_null`.
6. On `curiosity_loop → Input`:
   - **Hand Tracking CHOP** → `hands_null`
   - **Pose Tracking CHOP** → `pose_null`
   - Optional: **Webcam TOP (ghost)** → the MediaPipe video TOP output, which adds a faint mirror image behind the photos
   - On the **Simulate** page, turn **Simulate** off
7. In the Textport, run:
   ```python
   op('/project1/curiosity_loop/loop_td').module.Diagnose()
   ```
   It lists which hand and pose landmarks it recognised. The code detects channel naming automatically, but **if it says "nothing recognised", paste the output to Claude.**

### Calibrating in the actual room
- **Wrong horizontal direction** (you step right, the spiral leans left)? Toggle **Mirror X**.
- **Up and down reversed?** Set **Raw Y Axis** to Down or Up. It is detected automatically from your pose, but you can force it.
- **Distance too sensitive?** Stand where visitors will stand close and far away. Diagnose doesn't print shoulder width, so adjust **Shoulder Width: Close/Far** until the spiral's size change feels right.
- **Pointing doesn't register?** Increase **Open-Hand Dwell** from 0 so hovering also works, or lower **Point Dwell Time**.

## 4. Show it

`curiosity_loop/window` is a Window COMP set to `out`. Pulse **Open as Separate Window**, or set it as the Perform window and press F1. The free (non-commercial) version renders at 1280×720, which is within its 1280 limit.

**Assignment requirement: 3 minutes unattended.** Errors in `loop_td` are caught, printed at most once every 5 s, and the show keeps running. Test it: start it, walk away for 3 minutes, and check the Textport.

## The exhibition: life, death, transformation, return

The current piece (`exhibition/`) treats the spiral as a continuous movement through states of being.
It opens at the centre with **Birth** (the Kongo cosmogram, Hilma af Klint's *Primordial Chaos* and
*Childhood*, creation and seed imagery), widens through **Growth** (*Youth* and *Adulthood*, mother and
child, metamorphosis, a nautilus), erodes through **Death** (*Old Age*, ruins, sand, burial, an
emptied nkisi, the earth goddess Bhu: public-domain echoes of Robert Smithson and Ana Mendieta),
and turns into **Rebirth** (cicada, scarab, *The Swan*, ancestors, the *Altarpiece*). It ends on the
same Kongo crucifix it began with, whose incised x references the dikenga dia Kongo, so the
viewer realizes the exhibition has been moving in a circle.

- 36 places in the spiral (35 works) from the Cleveland Museum of Art (CC0), The Met (public domain)
  and Wikimedia Commons (public-domain af Klint scans). See `exhibition/metadata/README.md`.
- Selecting a work shows its **title, date, artist and a short description**. Each description is
  tagged as museum text, abridged museum text, or written for this exhibition.
- Edit the selection or the descriptions in `exhibition/curation.json`, then run
  `python3 scripts/build_exhibition.py` and the build line again.
- **Photo Folder** switches sets: `exhibition/images` (current), `artworks/images` (the 40 spiral
  artworks, tagged `v2-artworks` in git), or `photos` (my own photos).

## The artworks

The piece shows 40 public-domain / CC0 artworks about spirals, vortexes, coils and circular motion,
from **The Metropolitan Museum of Art** (21) and the **Cleveland Museum of Art** (19): ancient
spiral jewelry, prints and drawings (Piranesi, Hiroshige, Galli Bibiena, Wadsworth), paintings
(Kōrin, Gauguin, Turner), early photographs (the Ring Nebula, a spiral staircase) and decorative art.

- `artworks/images/001.jpg ... 040.jpg`: the images, 1600 px on the long side, never cropped
- `artworks/metadata/artworks.json` and `artworks.csv`: full museum metadata for each work (fields a museum doesn't provide are `null`, never invented)
- `artworks/metadata/README.md`: sources, licenses, and an object-page link for every work
- `artworks/selection.json`: the 40 picks in spiral order (the first ones appear at the center)
- `scripts/download_artworks.py`: regenerates everything from the museum APIs (`candidates`, then `build`)

To swap a work, edit `artworks/selection.json`, run `python3 scripts/download_artworks.py build`, and run the build line again.

### Using my own photos instead
Set **Photo Folder** on `curiosity_loop`'s Input page to `photos`, then run the build line again. To refresh them, put originals in `photos_originals/` and run `zsh tools/prepare_photos.sh`. Personal photos are git-ignored.

## Git
`.gitignore` excludes `*.toe`, `Backup/` and MediaPipe files, following the assignment's rule not to commit the .toe. Because the network is generated by `build.py`, the repo is the source of truth: anyone can rebuild the piece with one line.
