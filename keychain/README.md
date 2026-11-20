# Apex Smart Automation keychain

![Keychain preview](preview.png)

A 52 × 63 × 4 mm round fob built from the Apex logo used on the website
(`apex-logo.png`). It has a raised blue border and a key-ring hole that fits 25–30 mm
split rings.

## Files

| File | Use |
| --- | --- |
| `apex-keychain.svg` | Full-colour artwork with the real logo, at true size (mm), for UV printing, printed acrylic, or mock-ups |
| `apex-keychain.stl` | One-piece 3D print, single colour |
| `apex-keychain-base.stl` + `apex-keychain-inlay.stl` | Two-colour print: load both as parts of one object (black base, blue logo) |
| `apex-keychain-laser.svg` | Laser file: red hairline = cut, black fill = engrave |
| `apex-logo.png` | Source logo, taken from the website |
| `generate_keychain.py` | Rebuilds everything above from the logo |

## How the logo is used

- The **colour SVG** places the original logo image on the fob, unchanged.
- The **STL and laser files** use a vector trace of the logo's bright parts. Because the
  source is a glowing PNG, traced edges are a little rough. A vector logo from your
  designer (SVG, AI or EPS) would give crisper 3D-printed and engraved edges.
- In the STL, the thin circuit lines are thickened to 0.6 mm so they can print.

## Printing tips

- Print flat, logo facing up, no supports. 0.2 mm layers or finer.
- Single-extruder two-tone: add a filament change at **3.0 mm** (black, then blue).
- "SMART AUTOMATION" is about 1.3 mm tall. It needs a 0.25 mm nozzle to come out sharp;
  on a 0.4 mm nozzle it will be legible but soft. Laser engraving and UV printing have
  no trouble with it.

## Changing it

Edit the parameters at the top of `generate_keychain.py` (fob size, thickness, hole
size, trace threshold) and rerun:

```sh
pip install manifold3d shapely opencv-python-headless
python3 generate_keychain.py
```
