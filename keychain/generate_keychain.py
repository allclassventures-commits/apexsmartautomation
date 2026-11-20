#!/usr/bin/env python3
"""Generate the Apex Smart Automation keychain from the company logo.

Input:  apex-logo.png  (the logo used on the website)
Outputs (written next to this script):
  apex-keychain.stl         single-piece model (print in one colour)
  apex-keychain-base.stl    black base only        } for two-colour / MMU
  apex-keychain-inlay.stl   raised blue logo trace } printing
  apex-keychain.svg         full-colour artwork with the real logo (UV print / acrylic)
  apex-keychain-laser.svg   cut (red) + engrave (black) file for laser cutters

Requires: pip install manifold3d shapely opencv-python-headless
All dimensions are millimetres.
"""
import base64
import math
import pathlib
import struct

import cv2
import numpy as np
from manifold3d import CrossSection, FillRule
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parent
LOGO = OUT / "apex-logo.png"

# ---------------------------------------------------------------- parameters
DISC_R = 26.0          # fob radius (52 mm across)
TAB_R = 7.0            # radius of the key-ring tab
TAB_Y = DISC_R + 4.0   # tab centre above the disc centre
HOLE_R = 3.4           # key-ring hole (fits 25-30 mm split rings)
BASE_T = 3.0           # base plate thickness
RAISE_T = 1.0          # height of the raised logo and rim
RIM_W = 1.2            # width of the raised border
LOGO_FILL = 24.0       # logo artwork radius on the fob
MIN_LINE = 0.6         # thin logo lines are thickened to this in the STL (FDM-printable)

# logo trace settings (pixels of the 500x500 source image)
LOGO_C, LOGO_ART_R = 250.0, 238.0  # centre of the round logo, radius of its artwork
LOGO_BADGE_R = 229.0               # just inside the badge edge (the PNG has a white background)
THRESHOLD = 90                     # blue-channel brightness that counts as "logo"
MIN_AREA_PX = 12                   # drop specks smaller than this

BLACK, BLUE = "#000000", "#3aa8ff"


# ------------------------------------------------------------------ geometry
def trace_logo():
    """Vector trace of the bright (blue/white) parts of the logo, in mm, centred at 0,0."""
    img = cv2.imread(str(LOGO), cv2.IMREAD_UNCHANGED)
    blue, alpha = img[:, :, 0], img[:, :, 3]
    mask = ((blue > THRESHOLD) & (alpha > 0)).astype(np.uint8) * 255
    yy, xx = np.mgrid[: mask.shape[0], : mask.shape[1]]
    mask[(xx - LOGO_C) ** 2 + (yy - LOGO_C) ** 2 > (LOGO_ART_R - 2) ** 2] = 0

    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    k = LOGO_FILL / LOGO_ART_R

    def to_mm(c):
        return [((x - LOGO_C) * k, (LOGO_C - y) * k) for x, y in c.reshape(-1, 2)]

    shapes = []
    for i, c in enumerate(contours):
        if hier[0][i][3] != -1 or cv2.contourArea(c) < MIN_AREA_PX or len(c) < 3:
            continue
        holes, j = [], hier[0][i][2]
        while j != -1:
            if cv2.contourArea(contours[j]) >= MIN_AREA_PX and len(contours[j]) >= 3:
                holes.append(to_mm(contours[j]))
            j = hier[0][j][0]
        shapes.append(Polygon(to_mm(c), holes).buffer(0).simplify(0.03))
    # drop the faint glow arcs around the edge of the round logo badge
    centre = Point(0, 0)
    shapes = [s for s in shapes if s.distance(centre) < 0.88 * LOGO_FILL]
    return unary_union(shapes)


def printable(logo):
    """Thicken hairline parts (circuit traces) so a 0.4 mm nozzle can print them."""
    parts = []
    for p in getattr(logo, "geoms", [logo]):
        thin = p.buffer(-MIN_LINE / 2).is_empty
        parts.append(p.buffer(MIN_LINE / 4) if thin else p)
    return unary_union(parts)


def build():
    disc = Point(0, 0).buffer(DISC_R, resolution=96)
    tab = Point(0, TAB_Y).buffer(TAB_R, resolution=48)
    outline = unary_union([disc, tab]).convex_hull
    hole = Point(0, TAB_Y).buffer(HOLE_R, resolution=48)
    base = outline.difference(hole)

    rim = outline.difference(outline.buffer(-RIM_W, resolution=32))
    hole_rim = Point(0, TAB_Y).buffer(HOLE_R + RIM_W, resolution=48).difference(hole)
    logo = trace_logo()
    art = unary_union([rim, hole_rim, printable(logo)]).intersection(base)
    return base, art, dict(outline=outline, hole=hole, logo=logo, rims=unary_union([rim, hole_rim]))


# -------------------------------------------------------------------- export
def to_cross_section(geom):
    rings = []
    for p in getattr(geom, "geoms", [geom]):
        if p.is_empty:
            continue
        rings.append(list(p.exterior.coords)[:-1])
        rings.extend(list(i.coords)[:-1] for i in p.interiors)
    return CrossSection(rings, FillRule.EvenOdd)


def write_stl(manifold, path):
    mesh = manifold.to_mesh()
    v, tris = mesh.vert_properties, mesh.tri_verts
    with open(path, "wb") as f:
        f.write(b"Apex Smart Automation keychain".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p0, p1, p2 = (v[i][:3] for i in (a, b, c))
            u = [p1[k] - p0[k] for k in range(3)]
            w = [p2[k] - p0[k] for k in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            ln = math.sqrt(sum(x * x for x in n)) or 1.0
            f.write(struct.pack("<12fH", *(x / ln for x in n), *p0, *p1, *p2, 0))
    return len(tris)


def svg_path(geom, ox, oy):
    d = []
    for p in getattr(geom, "geoms", [geom]):
        if p.is_empty:
            continue
        for ring in [p.exterior, *p.interiors]:
            d.append("M" + "L".join(f"{x - ox:.3f},{oy - y:.3f}" for x, y in ring.coords) + "Z")
    return "".join(d)


def write_svgs(base, parts):
    minx, miny, maxx, maxy = parts["outline"].bounds
    W, H = maxx - minx, maxy - miny
    ox, oy = minx, maxy  # svg origin top-left, y down
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
            f'viewBox="0 0 {W:.3f} {H:.3f}">')

    # full colour: the real logo image, clipped to the fob, with a blue rim
    png = base64.b64encode(LOGO.read_bytes()).decode()
    k = LOGO_FILL / LOGO_ART_R
    cx, cy = -ox, oy  # fob centre in svg coords
    color = f"""{head}
  <title>Apex Smart Automation keychain</title>
  <defs><clipPath id="disc"><circle cx="{cx:.3f}" cy="{cy:.3f}" r="{LOGO_BADGE_R * k:.3f}"/></clipPath></defs>
  <path d="{svg_path(base, ox, oy)}" fill="{BLACK}" fill-rule="evenodd"/>
  <image href="data:image/png;base64,{png}" x="{cx - LOGO_C * k:.3f}" y="{cy - LOGO_C * k:.3f}" width="{500 * k:.3f}" height="{500 * k:.3f}" clip-path="url(#disc)"/>
  <path d="{svg_path(parts['rims'], ox, oy)}" fill="{BLUE}" fill-rule="evenodd"/>
</svg>
"""
    (OUT / "apex-keychain.svg").write_text(color)

    laser = f"""{head}
  <title>Apex keychain laser file: red = cut, black = engrave</title>
  <path d="{svg_path(parts['logo'], ox, oy)}" fill="#000" fill-rule="evenodd"/>
  <path d="{svg_path(parts['outline'], ox, oy)}{svg_path(parts['hole'], ox, oy)}" fill="none" stroke="#ff0000" stroke-width="0.01"/>
</svg>
"""
    (OUT / "apex-keychain-laser.svg").write_text(laser)
    return W, H


def main():
    base, art, parts = build()
    base3d = to_cross_section(base).extrude(BASE_T)
    art3d = to_cross_section(art).extrude(RAISE_T).translate((0, 0, BASE_T))
    whole = base3d + art3d
    n1 = write_stl(whole, OUT / "apex-keychain.stl")
    n2 = write_stl(base3d, OUT / "apex-keychain-base.stl")
    n3 = write_stl(art3d, OUT / "apex-keychain-inlay.stl")
    W, H = write_svgs(base, parts)
    print(f"fob {W:.1f} x {H:.1f} x {BASE_T + RAISE_T} mm | triangles: {n1} / {n2} / {n3}")
    print("mesh status:", whole.status())


if __name__ == "__main__":
    main()
