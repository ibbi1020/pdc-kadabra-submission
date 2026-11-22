"""Build the Milestone 2 slide deck (presentation.pptx) from the proposal content."""

import re
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from lxml import etree
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedFormatter, FixedLocator
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)

NAVY = "1B2A41"
INK = "2B2D42"
TEAL = "0E7C7B"
TEAL_LIGHT = "E3F3F2"
ORANGE = "E76F51"
ORANGE_LIGHT = "FDEDE8"
MUTED = "6B7280"
LINE = "DDE3EA"
EDGE = "9AA8BA"
PANEL = "F4F6F9"
WHITE = "FFFFFF"

FONT = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"
MONO = "Consolas"

plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["font.family"] = "Segoe UI"


def rgb(hex_color):
    return RGBColor.from_string(hex_color)


# --------------------------------------------------------------- animation

_capture_stack = []


def _track(shape):
    for items in _capture_stack:
        items.append(shape)
    return shape


@contextmanager
def capture():
    """Collect every shape created inside the block, for use as one animation step."""
    items = []
    _capture_stack.append(items)
    try:
        yield items
    finally:
        _capture_stack.remove(items)


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
EFFECTS = {
    "fade": (10, 0, "fade"),
    "wipe_left": (22, 8, "wipe(left)"),
    "wipe_down": (22, 1, "wipe(down)"),
}


def step(shapes, effect="fade", dur=450, stagger=0):
    return {"shapes": list(shapes), "effect": effect, "dur": dur, "stagger": stagger}


def animate(slide, steps):
    """Entrance animations that play automatically, one step after another."""
    next_id = iter(range(4, 1_000_000))
    pars, builds, start = [], [], 0
    for st in steps:
        shapes = [sh for sh in st["shapes"] if sh is not None]
        if not shapes:
            continue
        preset, subtype, filt = EFFECTS[st["effect"]]
        group_id = next(next_id)
        effects, end = [], 0
        for i, sh in enumerate(shapes):
            delay = i * st["stagger"]
            end = max(end, delay + st["dur"])
            node = "afterEffect" if i == 0 else "withEffect"
            spid = sh.shape_id
            eid, sid, aid = next(next_id), next(next_id), next(next_id)
            effects.append(
                f'<p:par><p:cTn id="{eid}" presetID="{preset}" presetClass="entr" '
                f'presetSubtype="{subtype}" fill="hold" grpId="0" nodeType="{node}">'
                f'<p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{sid}" dur="1" fill="hold"><p:stCondLst>'
                f'<p:cond delay="0"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/>'
                f'</p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
                f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="{filt}"><p:cBhvr>'
                f'<p:cTn id="{aid}" dur="{st["dur"]}"/><p:tgtEl><p:spTgt spid="{spid}"/>'
                f'</p:tgtEl></p:cBhvr></p:animEffect></p:childTnLst></p:cTn></p:par>')
            if sh._element.tag == qn("p:sp") and spid not in builds:
                builds.append(spid)
        pars.append(f'<p:par><p:cTn id="{group_id}" fill="hold"><p:stCondLst>'
                    f'<p:cond delay="{start}"/></p:stCondLst><p:childTnLst>'
                    f'{"".join(effects)}</p:childTnLst></p:cTn></p:par>')
        start += end
    bld = "".join(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>' for spid in builds)
    xml = (
        f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" '
        f'restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" '
        f'nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        f'<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
        f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst>'
        f'<p:childTnLst>{"".join(pars)}</p:childTnLst></p:cTn></p:par></p:childTnLst>'
        f'</p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/>'
        f'</p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" '
        f'delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
        f'</p:childTnLst></p:cTn></p:par></p:tnLst>'
        f'{"<p:bldLst>" + bld + "</p:bldLst>" if bld else ""}</p:timing>')
    sld = slide._element
    sld.append(etree.fromstring(f'<p:transition xmlns:p="{P_NS}" spd="med"><p:fade/>'
                                f'</p:transition>'))
    sld.append(etree.fromstring(xml))


# ---------------------------------------------------------------- primitives

def box(slide, x, y, w, h, fill=WHITE, line=None, rounded=False, radius=0.05, line_w=1.0,
        shape=None):
    kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE)
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded and shape is None:
        shp.adjustments[0] = radius
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return _track(shp)


TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|_\{.+?\}|\^\{.+?\})")


def add_runs(p, content, size, color, font, bold):
    for part in TOKEN.split(content):
        if not part:
            continue
        r = p.add_run()
        f = r.font
        f.size = Pt(size)
        f.color.rgb = rgb(color)
        if part[:2] in ("_{", "^{") and part.endswith("}"):
            r.text = part[2:-1]
            f.name = font
            f.bold = bold
            r._r.get_or_add_rPr().set("baseline", "-25000" if part[0] == "_" else "30000")
        elif part.startswith("**") and part.endswith("**"):
            r.text = part[2:-2]
            f.name = FONT_SEMI
            f.bold = False
            f.color.rgb = rgb(NAVY if color in (INK, NAVY) else color)
        elif part.startswith("`") and part.endswith("`"):
            r.text = part[1:-1]
            f.name = MONO
            f.color.rgb = rgb(TEAL)
        else:
            r.text = part
            f.name = font
            f.bold = bold


def set_bullet(p, color, char="•", indent=0.24):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent))))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", color)
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", char)


def text(slide, x, y, w, h, paras, size=16, color=INK, font=FONT, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.12, after=0,
         bullet=None, bullet_color=TEAL):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(paras, str):
        paras = [paras]
    for i, para in enumerate(paras):
        opts = para if isinstance(para, dict) else {"t": para}
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = opts.get("align", align)
        p.line_spacing = opts.get("spacing", spacing)
        p.space_after = Pt(opts.get("after", after))
        if "before" in opts:
            p.space_before = Pt(opts["before"])
        add_runs(p, opts["t"], opts.get("size", size), opts.get("color", color),
                 opts.get("font", font), opts.get("bold", bold))
        b = opts.get("bullet", bullet)
        if b:
            set_bullet(p, opts.get("bullet_color", bullet_color), char=b)
        if "hang" in opts:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(Inches(opts["hang"]))))
            pPr.set("indent", str(-int(Inches(opts["hang"]))))
    return _track(tb)


def connector(slide, x1, y1, x2, y2, color=EDGE, width=1.5, arrow=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if arrow:
        ln = c.line._get_or_add_ln()
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    return _track(c)


def badge(slide, x, y, d, label, fill=TEAL, size=14, color=WHITE):
    s = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.name = FONT_SEMI
    r.font.color.rgb = rgb(color)
    return s


def chip(slide, x, y, label, fill, color=WHITE, size=9.5, w=None, h=0.27):
    width = w if w is not None else 0.2 + 0.085 * len(label)
    s = box(slide, x, y, width, h, fill=fill, rounded=True, radius=0.5)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.name = FONT_SEMI
    r.font.color.rgb = rgb(color)
    return width


def card(slide, x, y, w, h, title=None, accent=TEAL, fill=WHITE, title_size=16, line=LINE):
    box(slide, x, y, w, h, fill=fill, line=line, rounded=True, radius=0.035)
    if title:
        box(slide, x + 0.28, y + 0.26, 0.38, 0.055, fill=accent)
        text(slide, x + 0.28, y + 0.38, w - 0.56, 0.45, title, size=title_size, color=NAVY,
             font=FONT_SEMI)
        return y + 0.9
    return y + 0.28


def math_img(name, tex, size=24, color=NAVY):
    path = ASSETS / f"{name}.png"
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size, color="#" + color)
    fig.savefig(path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return path


def picture(slide, path, x, y, scale=1.0, max_w=None, center_in=None, dpi=300):
    w_px, h_px = Image.open(path).size
    w, h = w_px / dpi * scale, h_px / dpi * scale
    if max_w is not None and w > max_w:
        h *= max_w / w
        w = max_w
    if center_in is not None:
        x = x + (center_in - w) / 2
    _track(slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h)))
    return w, h


def heading(slide, kicker, title):
    box(slide, 0.6, 0.47, 0.09, 0.78, fill=TEAL)
    text(slide, 0.88, 0.42, 11.5, 0.3, kicker.upper(), size=11, color=TEAL, font=FONT_SEMI)
    text(slide, 0.88, 0.68, 11.8, 0.6, title, size=28, color=NAVY, font=FONT, bold=True)


def footer(slide, number):
    connector(slide, 0.6, 6.98, 12.73, 6.98, color=LINE, width=0.75)
    text(slide, 0.6, 7.06, 9, 0.3,
         "KADABRA  ·  Paper 44  ·  CS-3006 Parallel and Distributed Computing  ·  Milestone 2",
         size=9.5, color=MUTED)
    text(slide, 11.73, 7.06, 1.0, 0.3, str(number), size=9.5, color=MUTED, align=PP_ALIGN.RIGHT)


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body


# ------------------------------------------------------------------- charts

def schedule_chart(path, w, h):
    costs = [3, 1, 1, 2, 5, 4, 1, 1, 1, 1, 2, 1, 2, 1, 1, 3]
    threads = 4
    chunk = len(costs) // threads
    static = []
    for t in range(threads):
        lane, start = [], 0
        for i in range(t * chunk, (t + 1) * chunk):
            lane.append((start, costs[i], i))
            start += costs[i]
        static.append(lane)
    dynamic = [[] for _ in range(threads)]
    free = [0] * threads
    for i, c in enumerate(costs):
        t = min(range(threads), key=lambda q: (free[q], q))
        dynamic[t].append((free[t], c, i))
        free[t] += c

    fig, axes = plt.subplots(2, 1, figsize=(w, h), sharex=True)
    static_barrier = max(lane[-1][0] + lane[-1][1] for lane in static)
    for ax, sched, name in zip(axes, (static, dynamic),
                               ("schedule(static)", "schedule(dynamic)")):
        finish = [lane[-1][0] + lane[-1][1] for lane in sched]
        barrier = max(finish)
        for t, lane in enumerate(sched):
            y = threads - 1 - t
            for start, c, i in lane:
                ax.add_patch(Rectangle((start, y - 0.36), c, 0.72, facecolor="#" + TEAL,
                                       edgecolor="white", linewidth=1.2))
                ax.text(start + c / 2, y, str(i + 1), ha="center", va="center", color="white",
                        fontsize=7)
            if finish[t] < barrier:
                ax.add_patch(Rectangle((finish[t], y - 0.36), barrier - finish[t], 0.72,
                                       facecolor="#EEF1F5", edgecolor="#C3CCD8", hatch="////",
                                       linewidth=0.5))
        ax.axvline(barrier, color="#" + ORANGE, linestyle="--", linewidth=1.6)
        ax.text(barrier + 0.2, threads - 1, f"barrier at t = {barrier}", color="#" + ORANGE,
                fontsize=8.5, va="center")
        ax.set_yticks(range(threads))
        ax.set_yticklabels([f"T{threads - y}" for y in range(threads)], fontsize=8.5,
                           color="#" + INK)
        ax.set_ylim(-0.6, threads - 0.4)
        ax.set_title(name, loc="left", fontsize=9.5, color="#" + NAVY, family="Consolas",
                     pad=3)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#" + EDGE)
        ax.tick_params(axis="both", length=0, colors="#" + MUTED, labelsize=8)
    axes[-1].set_xlim(0, static_barrier + 3.6)
    axes[-1].set_xlabel("time  (16 samples of uneven cost, illustrative units)", fontsize=8.5,
                        color="#" + MUTED)
    fig.tight_layout(h_pad=0.6)
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)


def k_chart(path, w, h):
    u = np.linspace(0, 4, 500)
    k = 10 ** u
    barrier = 3.0 * np.exp(-1.1 * u)
    waste = 0.12 * np.exp(0.9 * u)
    base = 0.6
    total = base + barrier + waste
    fig, ax = plt.subplots(figsize=(w, h))
    ax.plot(k, base + barrier, color="#" + TEAL, lw=1.8, label="barrier + merge cost")
    ax.plot(k, base + waste, color="#" + ORANGE, lw=1.8, label="samples taken past the stop")
    ax.plot(k, total, color="#" + NAVY, lw=2.8, label="time to a valid stop")
    best = int(np.argmin(total))
    ax.scatter([k[best]], [total[best]], s=46, color="#" + NAVY, zorder=5)
    ax.annotate("best k: to be measured", xy=(k[best], total[best]),
                xytext=(k[best], total[best] - 1.15), fontsize=8.5, color="#" + NAVY,
                ha="center", va="top",
                arrowprops=dict(arrowstyle="-", color="#" + NAVY, lw=0.8))
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([1, 10, 100, 1000, 10000]))
    ax.xaxis.set_major_formatter(FixedFormatter(["1", "10", "$10^2$", "$10^3$", "$10^4$"]))
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.set_ylim(0, 6.2)
    ax.set_yticks([])
    ax.set_xlabel("batch length k  (samples between stopping tests)", fontsize=8.5,
                  color="#" + MUTED)
    ax.set_ylabel("cost", fontsize=8.5, color="#" + MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_color("#" + EDGE)
    ax.tick_params(axis="both", length=0, colors="#" + MUTED, labelsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=1,
              bbox_to_anchor=(0.5, 1.02), labelcolor="#" + INK)
    ax.text(0.99, 0.03, "expected shape, not a measurement", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=8, color="#" + MUTED, style="italic")
    fig.tight_layout()
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------- slides

def network(s):
    """The navy-slide graph; returns (background shapes, path walk in drawing order, caption)."""
    nodes = {
        "a": (8.15, 1.25), "b": (9.35, 0.85), "c": (8.7, 2.45), "d": (10.0, 1.95),
        "e": (7.95, 3.75), "f": (9.3, 3.4), "v": (10.55, 3.65), "g": (11.65, 2.6),
        "h": (12.6, 1.55), "i": (11.9, 4.05), "j": (12.75, 3.2), "k": (11.25, 5.25),
        "l": (12.45, 5.65), "m": (9.7, 5.05), "n": (8.45, 5.7), "o": (10.5, 6.35),
    }
    edges = ["ab", "ac", "bd", "cd", "cf", "ef", "df", "fv", "mv", "vg", "vi", "gh", "hj",
             "gj", "ij", "ik", "kl", "jl", "en", "nm", "mo", "ce"]
    path = ["ac", "cf", "fv", "vg", "gh"]
    path_nodes = ["a", "c", "f", "v", "g", "h"]
    edge_shape, node_shape = {}, {}
    for e in edges:
        (x1, y1), (x2, y2) = nodes[e[0]], nodes[e[1]]
        on_path = e in path
        edge_shape[e] = connector(s, x1, y1, x2, y2, color="35B8B5" if on_path else "33496B",
                                  width=3.5 if on_path else 1.5)
    for name, (x, y) in nodes.items():
        if name == "v":
            d, fill = 0.46, "F08A5D"
        elif name in ("a", "h"):
            d, fill = 0.32, "35B8B5"
        elif name in ("c", "f", "g"):
            d, fill = 0.26, "35B8B5"
        else:
            d, fill = 0.24, "3D5679"
        node_shape[name] = box(s, x - d / 2, y - d / 2, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    caption = text(s, 9.6, 6.62, 3.2, 0.3, "one sampled shortest path", size=10,
                   color="7F93AE", align=PP_ALIGN.RIGHT)
    background = [edge_shape[e] for e in edges if e not in path]
    background += [node_shape[m] for m in nodes if m not in path_nodes]
    walk = [node_shape["a"]]
    for e, nxt in zip(path, path_nodes[1:]):
        walk += [edge_shape[e], node_shape[nxt]]
    return background, walk, caption


def navy_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(NAVY)
    return s


def slide_title(prs):
    s = navy_slide(prs)
    background, walk, caption = network(s)

    with capture() as title_block:
        text(s, 0.85, 0.95, 7, 0.3,
             "CS-3006  ·  PARALLEL AND DISTRIBUTED COMPUTING  ·  MILESTONE 2",
             size=11, color="7FD1CF", font=FONT_SEMI)
        text(s, 0.85, 1.45, 6.9, 2.2,
             "Parallel Approximation of Betweenness Centrality with KADABRA",
             size=40, color=WHITE, bold=True, spacing=1.0)
        box(s, 0.88, 3.72, 0.9, 0.06, fill="35B8B5")
    with capture() as details:
        text(s, 0.85, 3.98, 6.6, 1.0, [
            {"t": "Project proposal  ·  Paper 44", "size": 17, "color": "DCE4EE",
             "font": FONT_SEMI, "after": 4},
            {"t": "Borassi & Natale, KADABRA is an ADaptive Algorithm for Betweenness via "
                  "Random Approximation, ESA 2016", "size": 13, "color": "A9B7CA"},
        ])
        text(s, 0.85, 5.55, 6.5, 1.1, [
            {"t": "Ibraheem Farooq   23i-0816", "size": 14, "color": WHITE, "after": 2},
            {"t": "Musab Saleem   23i-0857", "size": 14, "color": WHITE, "after": 2},
            {"t": "Section D  ·  23 November 2026", "size": 12, "color": "A9B7CA"},
        ])

    animate(s, [
        step(title_block, dur=700),
        step(details, dur=500),
        step(background, dur=700),
        step(walk, dur=300, stagger=170),
        step([caption], dur=400),
    ])
    notes(s, "Introduce the group and the paper. Our project: sampled shortest-path "
             "betweenness on small graphs, samples run in parallel with OpenMP, error "
             "checked against exact Brandes.")


def slide_problem(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Understanding the paper", "The problem: who sits on the shortest paths?")

    with capture() as intro:
        text(s, 0.85, 1.55, 6.7, 0.7,
             "Betweenness centrality measures how much shortest-path traffic has to pass "
             "through a vertex.", size=17, color=INK)
    with capture() as formula:
        box(s, 0.85, 2.3, 6.7, 1.3, fill=PANEL, rounded=True, radius=0.06)
        f1 = math_img("bc", r"bc(v)\;=\;\frac{1}{n(n-1)}\sum_{s\neq v\neq t}"
                            r"\frac{\sigma_{st}(v)}{\sigma_{st}}", size=25)
        picture(s, f1, 0.85, 2.45, center_in=6.7)
        text(s, 0.85, 3.72, 6.7, 0.65,
             "σ_{st} counts shortest s–t paths and σ_{st}(v) those through v. Equivalently, "
             "bc(v) is the probability that v lies strictly inside a uniformly random shortest "
             "path.", size=12.5, color=MUTED)
    bullets = text(s, 0.85, 4.55, 6.7, 2.3, [
        {"t": "**Exact is expensive.** Brandes runs one BFS per vertex: O(nm) on unweighted "
              "graphs. Fine for thousands of vertices, impractical for millions.", "after": 8},
        {"t": "**And hard to beat.** A truly subcubic algorithm for even one vertex on sparse "
              "graphs would refute the Strong Exponential Time Hypothesis.", "after": 8},
        {"t": "**So we approximate.** Every vertex within additive error λ, with probability "
              "at least 1 − δ."},
    ], size=14.5, bullet="•")

    with capture() as graph_card:
        card(s, 8.0, 1.55, 4.73, 5.2, "Where betweenness is high", accent=ORANGE)
    left = [(8.6, 2.75), (9.45, 2.55), (8.5, 3.85), (9.5, 3.95), (9.0, 4.95)]
    right = [(11.3, 2.65), (12.15, 2.8), (11.25, 3.95), (12.2, 4.0), (11.75, 5.0)]
    v = (10.38, 3.8)
    with capture() as left_group:
        for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4), (0, 3)]:
            connector(s, *left[a], *left[b], color=EDGE, width=1.5)
    with capture() as right_group:
        for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4), (1, 2)]:
            connector(s, *right[a], *right[b], color=EDGE, width=1.5)
    with capture() as bridge:
        for p in (left[1], left[3], right[0], right[2]):
            connector(s, *p, *v, color=ORANGE, width=2.25)
    for i, (x, y) in enumerate(left + right):
        node = box(s, x - 0.15, y - 0.15, 0.3, 0.3, fill=WHITE, line=NAVY, line_w=1.5,
                   shape=MSO_SHAPE.OVAL)
        (left_group if i < len(left) else right_group).append(node)
    hub = badge(s, v[0] - 0.24, v[1] - 0.24, 0.48, "v", fill=ORANGE, size=15)
    graph_caption = text(s, 8.3, 5.55, 4.15, 1.0,
                         "Every shortest path between the two groups has to pass through v, "
                         "so bc(v) is the largest score in this graph.", size=12.5,
                         color=MUTED, align=PP_ALIGN.CENTER)
    footer(s, n)
    animate(s, [
        step(intro, dur=450),
        step(formula, dur=550),
        step(graph_card, dur=400),
        step(left_group, dur=500),
        step(right_group, dur=500),
        step([hub], dur=400),
        step(bridge, dur=350, stagger=150),
        step([graph_caption], dur=400),
        step([bullets], effect="wipe_down", dur=900),
    ])
    notes(s, "Betweenness is the fraction of shortest paths a vertex sits strictly inside. "
             "Exact Brandes is O(nm) and there is a SETH lower bound, so approximation is "
             "the practical route. The guarantee KADABRA gives is additive error lambda "
             "with probability 1 minus delta.")


def slide_algorithm(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Understanding the paper", "How KADABRA works")

    steps = [
        ("Cap the samples",
         "Compute an upper bound VD on the vertex diameter and set the hard cap ω. After ω "
         "samples every error is ≤ λ with probability 1 − δ/2."),
        ("Pilot, then freeze",
         "Draw ω/100 pilot paths and split δ/2 into per-vertex budgets δ_{L}(v), δ_{U}(v) "
         "(`computeDelta`). The pilot is then discarded."),
        ("Sample and credit",
         "Pick s, t uniformly and one uniform shortest path between them. Add 1 to every "
         "intermediate vertex, then τ\u00a0←\u00a0τ\u00a0+\u00a01."),
        ("Stop when tight",
         "Stop when f\u00a0≤\u00a0λ and g\u00a0≤\u00a0λ for every vertex, or when "
         "τ\u00a0=\u00a0ω. Return counts\u00a0/\u00a0τ. "
         "Otherwise repeat step 3."),
    ]
    w, gap, x0, y0, h = 2.78, 0.33, 0.6, 1.55, 2.6
    builds = []
    arrow = None
    for i, (title, body) in enumerate(steps):
        x = x0 + i * (w + gap)
        accent = ORANGE if i == 3 else TEAL
        with capture() as one:
            box(s, x, y0, w, h, fill=WHITE, line=LINE, rounded=True, radius=0.05)
            badge(s, x + 0.24, y0 + 0.24, 0.44, str(i + 1), fill=accent, size=14)
            text(s, x + 0.8, y0 + 0.3, w - 0.95, 0.4, title, size=15.5, color=NAVY,
                 font=FONT_SEMI)
            text(s, x + 0.24, y0 + 0.88, w - 0.46, h - 1.0, body, size=14, color=INK,
                 spacing=1.15)
        builds.append(step(([arrow] if arrow else []) + one, dur=450))
        arrow = None
        if i < 3:
            arrow = connector(s, x + w + 0.04, y0 + h / 2, x + w + gap - 0.04, y0 + h / 2,
                              color=EDGE, width=2, arrow=True)

    with capture() as formulas:
        box(s, 0.6, 4.4, 5.3, 2.38, fill=PANEL, rounded=True, radius=0.05)
        text(s, 0.88, 4.58, 4.8, 0.3, "THE TWO FORMULAS", size=10.5, color=TEAL,
             font=FONT_SEMI)
    f_omega = math_img("omega", r"\omega=\frac{c}{\lambda^{2}}\left(\lfloor\log_{2}"
                                r"(\mathrm{VD}-2)\rfloor+1+\ln\frac{2}{\delta}\right)", size=21)
    f_est = math_img("estimate", r"\tilde{b}(v)=\frac{1}{\tau}\sum_{i=1}^{\tau}X_i(v)"
                                 r",\qquad X_i(v)=1\ \mathrm{iff}\ v\ \mathrm{is\ inside}\ "
                                 r"\pi_i", size=19)
    with capture() as omega_img:
        picture(s, f_omega, 0.88, 4.95, max_w=4.8)
    with capture() as est_img:
        picture(s, f_est, 0.88, 5.95, max_w=4.8)

    with capture() as legal:
        card(s, 6.15, 4.4, 6.58, 2.38, None)
        text(s, 6.43, 4.58, 6.1, 0.3, "WHY STOPPING EARLY IS LEGAL", size=10.5, color=TEAL,
             font=FONT_SEMI)
        text(s, 6.43, 4.92, 6.05, 1.0,
             "A bound proved for a fixed τ does not hold at a stopping time chosen from the "
             "same samples. KADABRA fixes ω in advance, applies a martingale inequality up to "
             "ω, and only then transfers it to the actual stop.", size=12.5, color=INK,
             spacing=1.12)
    with capture() as theorem:
        box(s, 6.43, 5.92, 6.05, 0.7, fill=TEAL_LIGHT, rounded=True, radius=0.12)
        text(s, 6.6, 5.98, 5.75, 0.6,
             "**Theorem 1.** With probability ≥ 1 − δ, either τ = ω and every error is < λ, or "
             "it stopped early and bc(v) ∈ [b̃(v) − f, b̃(v) + g] for every v.",
             size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, n)
    animate(s, builds + [
        step(formulas, dur=400),
        step(omega_img, effect="wipe_left", dur=700),
        step(est_img, effect="wipe_left", dur=700),
        step(legal, dur=500),
        step(theorem, dur=500),
    ])
    notes(s, "Four steps. Cap omega from the vertex diameter. A pilot fixes per-vertex failure "
             "budgets, which are then frozen and the pilot discarded. Sample a pair and one "
             "uniform shortest path, credit intermediate vertices only. Stop when f and g are "
             "below lambda for every vertex, or at omega. The key idea: earlier methods "
             "applied a fixed-tau bound at a random time; KADABRA's cap plus martingale "
             "argument is what makes early stopping valid.")


def slide_review(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Understanding the paper", "What the paper contributes, and where it is limited")

    with capture() as left_card:
        top = card(s, 0.6, 1.55, 6.05, 5.22, "Core contributions", accent=TEAL)
    left_text = text(s, 0.88, top, 5.55, 4.2, [
        {"t": "**Adaptive sampling made rigorous.** Earlier adaptive methods applied fixed-τ "
              "bounds at a random stop. The cap ω plus a martingale argument makes early "
              "stopping provably safe.", "after": 10},
        {"t": "**Balanced bidirectional BFS.** Search from s and t, always expand the lighter "
              "frontier, stop when they meet. m^{1/2+o(1)} per sample w.h.p. on configuration "
              "and rank-1 random graph models.", "after": 10},
        {"t": "**Results.** On average more than 100× faster than earlier approximations on "
              "graphs of about 10,000 vertices; top-k on networks with millions of vertices.",
         "after": 10},
        {"t": "**Top-k mode.** A different stopping test lets well-separated vertices keep "
              "wider intervals."},
    ], size=15, bullet="•", bullet_color=TEAL)

    with capture() as right_card:
        top = card(s, 6.88, 1.55, 5.85, 5.22, "Critical review", accent=ORANGE)
    right_text = text(s, 7.16, top, 5.35, 4.2, [
        {"t": "The guarantee is probabilistic: a single run may exceed λ, at rate ≤ δ.",
         "after": 8},
        {"t": "Budgets are frozen before sampling. Moving them toward the hard vertices is "
              "left open.", "after": 8},
        {"t": "ω is valid only if VD is an upper bound. An underestimate voids half the proof.",
         "after": 8},
        {"t": "The sublinear BFS bound is for random-graph models, not the worst case.",
         "after": 8},
        {"t": "Path counts σ grow exponentially on grids, yet arithmetic is assumed O(1).",
         "after": 8},
        {"t": "A zero pilot estimate needs an εδ/2n floor, and the paper prints ε = 0.0001 "
              "and 0.001 in different places."},
    ], size=14.5, bullet="•", bullet_color=ORANGE)
    footer(s, n)
    animate(s, [
        step(left_card, dur=400),
        step([left_text], effect="wipe_down", dur=1000),
        step(right_card, dur=400),
        step([right_text], effect="wipe_down", dur=1000),
    ])
    notes(s, "Two contributions: rigorous adaptive stopping and the balanced bidirectional "
             "BFS. Critique: probabilistic guarantee, frozen budgets, dependence on a correct "
             "diameter bound, model-specific BFS bound, sigma overflow, and the epsilon "
             "inconsistency in the paper.")


def slide_scope(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Scope, challenge, and complexity", "What we will build, and what we leave out")

    with capture() as build_card:
        top = card(s, 0.6, 1.55, 7.45, 3.95, "What we build", accent=TEAL)
    rows = [
        ("BASELINE", TEAL, "Sequential adaptive sampler + Brandes oracle",
         "Our own C++ on CSR graphs. One-sided BFS from s with σ-weighted backtracking "
         "from t; exact Brandes as ground truth."),
        ("TWO PARALLEL VERSIONS", NAVY, "Barrier loop + lock-free local-frame",
         "The barrier loop is the 2019 baseline and our fallback. The local-frame version "
         "drops the barrier using epochs, and is the piece we measure."),
        ("OUR CONTRIBUTION", ORANGE, "Three studies on those loops",
         "Barrier vs lock-free at a few cores; static vs dynamic vs guided; how often to "
         "run the stopping test. KADABRA's rule stays unchanged."),
    ]
    y = top - 0.05
    row_steps = []
    for i, (tag, color, title, body) in enumerate(rows):
        with capture() as row:
            badge(s, 0.88, y + 0.02, 0.42, str(i + 1), fill=color, size=13)
            cw = chip(s, 1.48, y + 0.08, tag, fill=color, size=8.5)
            text(s, 1.48 + cw + 0.14, y + 0.03, 5.6 - cw, 0.35, title, size=14, color=NAVY,
                 font=FONT_SEMI)
            text(s, 1.48, y + 0.43, 6.3, 0.6, body, size=12, color=INK, spacing=1.1)
        row_steps.append(step(row, dur=450))
        y += 1.0

    with capture() as out_card:
        top = card(s, 8.3, 1.55, 4.43, 3.95, "Deliberately left out", accent=MUTED)
    out_list = text(s, 8.58, top, 3.95, 3.0, [
        "Balanced bidirectional BFS (explained, not built)",
        "Top-k stopping test",
        "Weighted, dynamic, and edge betweenness",
        "shared-frame and indexed-frame (we build local-frame)",
        "MPI and GPU samplers",
        "New bounds, or beating SILVAN on samples",
    ], size=13, color=INK, bullet="×", bullet_color=ORANGE, after=5)

    with capture() as prior:
        box(s, 0.6, 5.72, 12.13, 1.06, fill=PANEL, rounded=True, radius=0.1)
        text(s, 0.88, 5.83, 11.6, 0.9, [
            {"t": "**Prior work is our baseline, not our claim.**  van der Grinten, Angriman & "
                  "Meyerhenke (Euro-Par 2019): OpenMP KADABRA, synchronized loop plus lock-free "
                  "epochs; we rebuild one variant, local-frame, as a measured baseline. van der "
                  "Grinten & Meyerhenke (IPDPS 2020): MPI, context only. natema/kadabra "
                  "(Apache-2.0): used only to check f, g, and computeDelta.", "size": 12, "spacing": 1.12},
        ], anchor=MSO_ANCHOR.MIDDLE)
    footer(s, n)
    animate(s, [step(build_card, dur=400)] + row_steps + [
        step(out_card, dur=400),
        step([out_list], effect="wipe_down", dur=900),
        step(prior, dur=500),
    ])
    notes(s, "Four pieces: the sequential sampler with Brandes, the OpenMP barrier loop as "
             "baseline and fallback, a lock-free local-frame version, and three studies on top. "
             "The lock-free mechanism is the 2019 authors', re-implemented as a measured "
             "baseline, not claimed as ours. Dropping it would leave a very thin contribution, "
             "which is why it is back in. Everything left out is on the right.")


def slide_hard(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Scope, challenge, and complexity", "Why this is hard")
    intro = text(s, 0.88, 1.5, 11.8, 0.4,
         "Brandes on a small graph is the easy part. The hard part is a parallel adaptive "
         "estimator that is wrong while still looking plausible.", size=14.5, color=MUTED)

    items = [
        ("CORRECTNESS", "Uniform path sampling",
         "Backtrack with probability σ_{sp} / σ_{su}. A uniform pick still runs, but fails "
         "Brandes on grids and bipartite graphs."),
        ("CORRECTNESS", "Disconnected pairs",
         "They count as samples that credit nobody. Re-drawing the pair estimates a "
         "different quantity."),
        ("CORRECTNESS", "Consistent snapshot",
         "The stop test must see a whole prefix of finished samples. A racy read can pass "
         "casual tests on x86."),
        ("PERFORMANCE", "Load imbalance",
         "BFS cost depends on the drawn pair, so equal sample counts are not equal work "
         "per thread."),
        ("PERFORMANCE", "Synchronization cadence",
         "Testing after every sample is mostly barrier; testing rarely wastes samples past "
         "the stopping point."),
        ("BOTH", "Overflow and setup cost",
         "σ needs checked 64-bit counters. The diameter and pilot can outweigh the loop, so "
         "the loop is timed alone."),
    ]
    w, gap_x, h, gap_y = 3.86, 0.275, 2.3, 0.22
    card_steps = []
    for i, (tag, title, body) in enumerate(items):
        col, row = i % 3, i // 3
        x = 0.6 + col * (w + gap_x)
        y = 2.05 + row * (h + gap_y)
        color = ORANGE if tag == "CORRECTNESS" else (TEAL if tag == "PERFORMANCE" else NAVY)
        with capture() as one:
            box(s, x, y, w, h, fill=WHITE, line=LINE, rounded=True, radius=0.05)
            badge(s, x + 0.26, y + 0.26, 0.4, str(i + 1), fill=color, size=12.5)
            chip(s, x + w - 0.26 - (0.2 + 0.085 * len(tag)), y + 0.32, tag, fill=color, size=8)
            text(s, x + 0.26, y + 0.82, w - 0.52, 0.4, title, size=16, color=NAVY,
                 font=FONT_SEMI)
            text(s, x + 0.26, y + 1.27, w - 0.52, 1.0, body, size=13.5, color=INK,
                 spacing=1.12)
        card_steps.append(step(one, dur=380))
    footer(s, n)
    animate(s, [step([intro], dur=450)] + card_steps)
    notes(s, "Correctness traps: biased backtracking, re-drawing disconnected pairs, and "
             "reading a partial snapshot. Performance problems: uneven BFS cost per sample and "
             "the cost of checking the stopping rule too often or too rarely. Plus sigma "
             "overflow and setup cost.")


def slide_parallel(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Implementation plan", "Parallel design and our contribution")

    sched_png = ASSETS / "schedule.png"
    k_png = ASSETS / "batch_length.png"
    schedule_chart(sched_png, 5.55, 2.75)
    k_chart(k_png, 5.55, 2.75)

    with capture() as knob1:
        card(s, 0.6, 1.5, 6.0, 4.0, None)
        text(s, 0.88, 1.66, 5.5, 0.3, "STUDY 2  ·  OPENMP SCHEDULE", size=10.5, color=TEAL,
             font=FONT_SEMI)
        text(s, 0.88, 1.93, 5.5, 0.35, "Even sample counts, uneven work", size=15,
             color=NAVY, font=FONT_SEMI)
    sched_pic = _track(s.shapes.add_picture(str(sched_png), Inches(0.82), Inches(2.4),
                                            Inches(5.55), Inches(2.75)))
    sched_note = text(s, 0.88, 5.17, 5.5, 0.3,
                      "Hatched = idle at the barrier. Illustrative costs.",
                      size=10.5, color=MUTED)

    with capture() as knob2:
        card(s, 6.73, 1.5, 6.0, 4.0, None)
        text(s, 7.01, 1.66, 5.5, 0.3, "STUDY 3  ·  BATCH LENGTH k", size=10.5, color=ORANGE,
             font=FONT_SEMI)
        text(s, 7.01, 1.93, 5.5, 0.35, "How often to run the stopping test", size=15,
             color=NAVY, font=FONT_SEMI)
    k_pic = _track(s.shapes.add_picture(str(k_png), Inches(6.95), Inches(2.4), Inches(5.55),
                                        Inches(2.75)))
    k_note = text(s, 7.01, 5.17, 5.5, 0.3,
                  "Sweep: static · dynamic · guided × 1, 2, 4, all physical cores × fixed set "
                  "of k.", size=10.5, color=MUTED)

    rules = [
        ("Study 1: barrier vs lock-free",
         "local-frame drops the barrier with epochs and release/acquire. Does the 2019 win "
         "survive at 1 to 8 cores?"),
        ("Same paths every run",
         "Sample i uses the RNG stream (seed, i), not the thread id, so a timing gap is what "
         "we changed, not the workload."),
        ("Stop test sees a whole prefix",
         "A legal stopping time for Theorem 1. Testing every k can only stop later, by ≤ k − 1 "
         "samples."),
    ]
    w = 3.93
    rule_steps = []
    for i, (title, body) in enumerate(rules):
        x = 0.6 + i * (w + 0.17)
        with capture() as one:
            box(s, x, 5.68, w, 1.12, fill=PANEL, rounded=True, radius=0.1)
            text(s, x + 0.2, 5.76, w - 0.4, 0.3, title, size=12.5, color=NAVY,
                 font=FONT_SEMI)
            text(s, x + 0.2, 6.07, w - 0.4, 0.7, body, size=10.5, color=INK, spacing=1.08)
        rule_steps.append(step(one, dur=400))
    footer(s, n)
    animate(s, [
        step(knob1, dur=400),
        step([sched_pic], effect="wipe_left", dur=1400),
        step([sched_note], dur=300),
        step(knob2, dur=400),
        step([k_pic], effect="wipe_left", dur=1400),
        step([k_note], dur=300),
    ] + rule_steps)
    notes(s, "Threads keep private counts. The barrier version merges them at a barrier; the "
             "lock-free local-frame version publishes them per epoch with release/acquire, no "
             "barrier. The stopping test only ever sees a whole finished prefix, so the "
             "guarantee holds either way. Our three studies: barrier vs lock-free across cores, "
             "the OpenMP schedule for uneven BFS cost, and the batch length k that trades "
             "synchronization against samples wasted after the stop. The charts are what we "
             "expect, not results.")


def slide_evaluation(prs, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    heading(s, "Evaluation plan", "How we will check correctness and measure performance")

    with capture() as corr_card:
        top = card(s, 0.6, 1.5, 5.97, 4.55, "Correctness", accent=ORANGE)
    checks = [
        "Hand-solved path graph, plus a disconnected pair.",
        "Grid over many seeds: catches biased backtracking.",
        "Same normalization, then max error vs λ; failure rate ≤ δ with a Clopper–Pearson "
        "interval.",
        "Mean error, Kendall τ, and top-k overlap.",
        "Every parallel configuration passes the same check before its timings count.",
    ]
    y = top
    check_steps = []
    for i, c in enumerate(checks):
        with capture() as item:
            badge(s, 0.88, y + 0.02, 0.33, str(i + 1), fill=ORANGE, size=10.5)
            text(s, 1.38, y, 4.95, 0.75, c, size=14, color=INK, spacing=1.08)
        check_steps.append(step(item, dur=350))
        y += 0.88 if len(c) > 58 else 0.6

    with capture() as perf_card:
        top = card(s, 6.76, 1.5, 5.97, 4.55, "Performance", accent=TEAL)
    f_speed = math_img("speedup", r"S=\frac{T_{\mathrm{serial}}}{T_{\mathrm{parallel}}}"
                                  r"\qquad E=\frac{S}{P}", size=21)
    with capture() as speed_img:
        picture(s, f_speed, 6.76, top - 0.02, center_in=5.97, max_w=4.2)
    perf_text = text(s, 7.04, top + 0.85, 5.4, 2.8, [
        {"t": "**Fixed budget:** identical paths serial and parallel, barrier paid every k. "
              "Compares schedules and k at equal work.", "after": 9},
        {"t": "**Adaptive:** time to a valid stop, samples taken, and samples past the stop.",
         "after": 9},
        {"t": "**Method:** sampling loop timed alone; ≥ 20 interleaved runs; medians and "
              "spread; pinned threads; CPU, compiler, flags reported."},
    ], size=14, bullet="•", spacing=1.08)

    with capture() as risk:
        box(s, 0.6, 6.2, 12.13, 0.62, fill=ORANGE_LIGHT, rounded=True, radius=0.2)
        text(s, 0.88, 6.2, 11.6, 0.62,
             "**Main risk:** schedule and k may barely matter on a laptop. We would still "
             "report idle time, barrier cost, and extra samples as the finding.",
             size=12.5, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    footer(s, n)
    animate(s, [step(corr_card, dur=400)] + check_steps + [
        step(perf_card, dur=400),
        step(speed_img, effect="wipe_left", dur=700),
        step([perf_text], effect="wipe_down", dur=1000),
        step(risk, dur=500),
    ])
    notes(s, "Correctness is statistical: the fraction of seeds whose max error exceeds lambda "
             "must stay at or below delta, after both outputs use the same normalization. "
             "Performance uses a fixed sample budget for clean speedup, and a separate "
             "adaptive mode for time to a valid stop.")


def slide_closing(prs, n):
    s = navy_slide(prs)
    background, walk, caption = network(s)

    with capture() as title_block:
        text(s, 0.85, 0.95, 7, 0.3, "KADABRA  ·  PAPER 44  ·  MILESTONE 2",
             size=11, color="7FD1CF", font=FONT_SEMI)
        text(s, 0.85, 1.4, 6.9, 1.2, "Thank you", size=60, color=WHITE, bold=True,
             spacing=1.0)
        box(s, 0.88, 2.65, 0.9, 0.06, fill="35B8B5")
    question = text(s, 0.85, 2.85, 6.6, 0.6, "Questions?", size=26, color="7FD1CF",
                    font=FONT_SEMI)
    recap = []
    for i, line in enumerate([
        "Sample shortest paths instead of running every BFS",
        "Run the samples in parallel with OpenMP",
        "Stay within λ of exact Brandes, with probability 1 − δ",
    ]):
        y = 3.85 + i * 0.62
        with capture() as row:
            badge(s, 0.88, y, 0.4, str(i + 1), fill="35B8B5", size=13)
            text(s, 1.45, y - 0.03, 6.0, 0.46, line, size=16, color="DCE4EE",
                 anchor=MSO_ANCHOR.MIDDLE)
        recap.append(row)
    names = text(s, 0.85, 5.95, 6.5, 0.8, [
        {"t": "Ibraheem Farooq  ·  Musab Saleem", "size": 14, "color": WHITE, "after": 2},
        {"t": "Section D  ·  CS-3006 Parallel and Distributed Computing", "size": 12,
         "color": "A9B7CA"},
    ])

    animate(s, [
        step(background, dur=600),
        step(title_block, dur=700),
        step(walk, dur=300, stagger=150),
        step([caption], dur=400),
        *[step(row, effect="wipe_left", dur=450) for row in recap],
        step([question], dur=500),
        step([names], dur=400),
    ])
    notes(s, "Close in one line: sample paths, run them in parallel, and stay within λ of "
             "Brandes. Then take questions.")


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide_title(prs)
    builders = [slide_problem, slide_algorithm, slide_review, slide_scope, slide_hard,
                slide_parallel, slide_evaluation, slide_closing]
    for i, build in enumerate(builders, start=2):
        build(prs, i)
    out = HERE / "presentation.pptx"
    prs.save(out)
    print(out)


if __name__ == "__main__":
    main()
