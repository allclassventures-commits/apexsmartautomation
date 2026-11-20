#!/usr/bin/env python3
"""Generate the Apex Smart Automations keychain.

Outputs (written next to this script):
  apex-keychain.stl         single-piece model (print in one colour)
  apex-keychain-base.stl    navy base only        } for two-colour / MMU
  apex-keychain-inlay.stl   raised gold artwork   } printing
  apex-keychain.svg         full-colour artwork (acrylic / UV print / preview)
  apex-keychain-laser.svg   cut (red) + engrave (black) file for laser cutters

Requires: pip install manifold3d shapely fonttools
All dimensions are millimetres.
"""
import math
import pathlib
import struct

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from manifold3d import CrossSection, FillRule
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------- parameters
TAG_W, TAG_H, TAG_R = 74.0, 28.0, 9.0  # tag outline + corner radius
HOLE_X, HOLE_R = 9.0, 3.4              # key-ring hole (fits 25-30 mm split rings)
BASE_T = 3.0                           # base plate thickness
RAISE_T = 1.0                          # height of raised artwork / rim
RIM_W = 1.2                            # width of raised border
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

NAVY, GOLD_A, GOLD_B = "#09121b", "#b89d62", "#e5cf95"  # from site styles.css


# ------------------------------------------------------------------ geometry
def rounded_rect(w, h, r):
    return box(r, r, w - r, h - r).buffer(r, resolution=32)


def apex_mark(size):
    """Peak chevron with a 'sensor node' dot — the Apex 'A'."""
    s = size / 16.0
    stroke = 1.2 * s  # half-width of the chevron legs
    chev = LineString([(0.6 * s, -2 * s), (8 * s, 14.8 * s), (15.4 * s, -2 * s)]).buffer(
        stroke, join_style="mitre", mitre_limit=4, cap_style="flat"
    )
    cx, cy = 8 * s, 3.4 * s
    node = Point(cx, cy).buffer(1.25 * s, resolution=24)
    arcs = []
    for r_in, r_out in ((2.3, 2.95), (3.8, 4.45)):
        ring = Point(cx, cy).buffer(r_out * s, resolution=48).difference(
            Point(cx, cy).buffer(r_in * s, resolution=48))
        arcs.append(ring.intersection(box(0, cy + 0.5 * s, 16 * s, 16 * s)))
    # keep a clear gap between the signal arcs and the legs
    arc = unary_union(arcs).difference(chev.buffer(0.7 * s))
    mark = unary_union([chev, node, arc]).intersection(box(-5, 0, 50, 50))
    return mark


class FlatPen(BasePen):
    def __init__(self, glyphset, steps=8):
        super().__init__(glyphset)
        self.contours, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            mt = 1 - t
            self.cur.append(tuple(mt**3 * a + 3 * mt * mt * t * b + 3 * mt * t * t * c + t**3 * d
                                  for a, b, c, d in zip(p0, p1, p2, p3)))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            mt = 1 - t
            self.cur.append(tuple(mt * mt * a + 2 * mt * t * b + t * t * c
                                  for a, b, c in zip(p0, p1, p2)))

    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def text_shape(txt, cap_height, tracking=0.0):
    """Text outline as shapely geometry, baseline at y=0, starting at x=0."""
    font = TTFont(FONT)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    cap = getattr(font["OS/2"], "sCapHeight", 0) or font["glyf"]["H"].yMax
    scale = cap_height / cap
    parts, x = [], 0.0
    for ch in txt:
        g = cmap[ord(ch)]
        pen = FlatPen(gs)
        gs[g].draw(pen)
        glyph = None
        for c in pen.contours:
            poly = Polygon(c).buffer(0)
            glyph = poly if glyph is None else glyph.symmetric_difference(poly)
        if glyph is not None:
            parts.append(affinity.translate(glyph, xoff=x))
        x += gs[g].width + tracking / scale
    return affinity.scale(unary_union(parts), scale, scale, origin=(0, 0))


def fit(geom, x0, y0, max_w=None):
    minx, miny, maxx, _ = geom.bounds
    if max_w and maxx - minx > max_w:
        k = max_w / (maxx - minx)
        geom = affinity.scale(geom, k, k, origin=(minx, miny))
        minx, miny, maxx, _ = geom.bounds
    return affinity.translate(geom, x0 - minx, y0 - miny)


def build():
    outline = rounded_rect(TAG_W, TAG_H, TAG_R)
    hole = Point(HOLE_X, TAG_H / 2).buffer(HOLE_R, resolution=48)
    base = outline.difference(hole)

    rim = outline.difference(outline.buffer(-RIM_W, resolution=32))
    hole_rim = Point(HOLE_X, TAG_H / 2).buffer(HOLE_R + RIM_W, resolution=48).difference(hole)

    mark = fit(apex_mark(16.0), 18.5, 6.0)
    word_x = mark.bounds[2] + 3.6
    word = fit(text_shape("APEX", 8.6, tracking=0.9), word_x, 12.4, max_w=TAG_W - word_x - 6.5)
    sub = fit(text_shape("SMART AUTOMATIONS", 2.6, tracking=0.25), word_x, 7.0,
              max_w=word.bounds[2] - word_x)
    divider = box(mark.bounds[2] + 1.6, 6.0, mark.bounds[2] + 2.1, TAG_H - 6.0)

    art = unary_union([rim, hole_rim, mark, word, sub, divider]).intersection(base)
    return base, art, dict(mark=mark, word=word, sub=sub, divider=divider, hole=hole, outline=outline)


# -------------------------------------------------------------------- export
def to_cross_section(geom):
    polys = getattr(geom, "geoms", [geom])
    rings = []
    for p in polys:
        if p.is_empty:
            continue
        rings.append(list(p.exterior.coords)[:-1])
        rings.extend(list(i.coords)[:-1] for i in p.interiors)
    return CrossSection(rings, FillRule.EvenOdd)


def write_stl(manifold, path):
    mesh = manifold.to_mesh()
    v, tris = mesh.vert_properties, mesh.tri_verts
    with open(path, "wb") as f:
        f.write(b"Apex Smart Automations keychain".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p0, p1, p2 = (v[i][:3] for i in (a, b, c))
            u = [p1[k] - p0[k] for k in range(3)]
            w = [p2[k] - p0[k] for k in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            ln = math.sqrt(sum(x * x for x in n)) or 1.0
            f.write(struct.pack("<12fH", *(x / ln for x in n), *p0, *p1, *p2, 0))
    return len(tris)


def svg_path(geom, h):
    d = []
    for p in getattr(geom, "geoms", [geom]):
        if p.is_empty:
            continue
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)
            d.append("M" + "L".join(f"{x:.3f},{h - y:.3f}" for x, y in pts) + "Z")
    return "".join(d)


def write_svgs(base, art, parts):
    W, H = TAG_W, TAG_H
    color = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">
  <title>Apex Smart Automations keychain</title>
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{GOLD_A}"/><stop offset="1" stop-color="{GOLD_B}"/>
    </linearGradient>
  </defs>
  <path d="{svg_path(base, H)}" fill="{NAVY}" fill-rule="evenodd"/>
  <path d="{svg_path(art, H)}" fill="url(#gold)" fill-rule="evenodd"/>
</svg>
"""
    (OUT / "apex-keychain.svg").write_text(color)

    engrave = unary_union([parts["mark"], parts["word"], parts["sub"], parts["divider"]])
    laser = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">
  <title>Apex keychain laser file: red = cut, black = engrave</title>
  <path d="{svg_path(engrave, H)}" fill="#000" fill-rule="evenodd"/>
  <path d="{svg_path(parts['outline'], H)}{svg_path(parts['hole'], H)}" fill="none" stroke="#ff0000" stroke-width="0.01"/>
</svg>
"""
    (OUT / "apex-keychain-laser.svg").write_text(laser)


def main():
    base, art, parts = build()
    base3d = to_cross_section(base).extrude(BASE_T)
    art3d = to_cross_section(art).extrude(RAISE_T).translate((0, 0, BASE_T))
    n1 = write_stl(base3d + art3d, OUT / "apex-keychain.stl")
    n2 = write_stl(base3d, OUT / "apex-keychain-base.stl")
    n3 = write_stl(art3d, OUT / "apex-keychain-inlay.stl")
    write_svgs(base, art, parts)
    print(f"tag {TAG_W}x{TAG_H}x{BASE_T + RAISE_T} mm | triangles: {n1} / {n2} / {n3}")
    print("watertight:", (base3d + art3d).status())


if __name__ == "__main__":
    main()
