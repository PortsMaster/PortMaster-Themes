#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# Makes the pictures in CREATING_A_THEME.md (docs/images/): the tutorial's steps (docs/tutorial/)
# and every theme in themes/, rendered by PortMaster's theme server from a PortMaster-GUI checkout.
#
#     python3 tools/render_docs.py --gui ../PortMaster-GUI
#
# It needs Pillow, in the Python that runs it, and the GUI checkout's .venv (requirements-dev.txt)
# for the theme server. --renders DIR reuses an earlier run's renders.

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TUTORIAL = ROOT / "docs" / "tutorial"
OUT = ROOT / "docs" / "images"
STEPS = sorted((p.name for p in TUTORIAL.iterdir() if p.is_dir()), key=lambda name: int(name.split("-")[1])) if TUTORIAL.is_dir() else []
BOX_COLOURS = [(255, 99, 71), (64, 196, 255), (124, 252, 0), (255, 215, 0), (238, 130, 238),
               (0, 255, 200), (255, 160, 60), (180, 160, 255), (255, 105, 180), (150, 230, 120)]


class Pictures:
    def __init__(self, gui, renders):
        self.gui = Path(gui)
        self.renders = Path(renders)
        self.font_file = str(self.gui / "PortMaster" / "pylibs" / "resources" / "DejaVuSans.ttf")

    def font(self, size):
        return ImageFont.truetype(self.font_file, size)

    def path(self, theme, screen, size="640x480", scheme=None, lang="en_US"):
        folder = self.renders / theme / size
        if scheme is None:
            scheme = sorted(p.name for p in folder.iterdir())[0]
        return folder / scheme / lang / f"{screen}.png"

    def image(self, theme, screen, **where):
        return Image.open(str(self.path(theme, screen, **where))).convert("RGB")

    def regions(self, theme, screen, **where):
        return json.loads(self.path(theme, screen, **where).with_suffix(".json").read_text(encoding="utf-8"))["regions"]

    def caption(self, image, text, size=18):
        bar = size + 20
        out = Image.new("RGB", (image.width, image.height + bar), (30, 30, 30))
        out.paste(image, (0, 0))
        ImageDraw.Draw(out).text((image.width // 2, image.height + bar // 2), text, font=self.font(size), fill=(235, 235, 235), anchor="mm")
        return out

    @staticmethod
    def grid(images, columns, gap=12):
        rows = [images[i:i + columns] for i in range(0, len(images), columns)]
        cell_w = max(im.width for im in images)
        cell_h = max(im.height for im in images)
        out = Image.new("RGB", (columns * cell_w + (columns + 1) * gap, len(rows) * cell_h + (len(rows) + 1) * gap), (18, 18, 18))
        for r, row in enumerate(rows):
            for c, im in enumerate(row):
                out.paste(im, (gap + c * (cell_w + gap) + (cell_w - im.width) // 2, gap + r * (cell_h + gap)))
        return out

    @staticmethod
    def save(image, name):
        OUT.mkdir(parents=True, exist_ok=True)
        if name.endswith(".jpg"):           ## the themes' art: a fraction of the size of a PNG
            image.save(str(OUT / name), quality=85, optimize=True)
        else:
            image.save(str(OUT / name), optimize=True)
        print(f"docs/images/{name}  {image.width}x{image.height}  {(OUT / name).stat().st_size // 1024} KB")

    def boxes(self, image, regions, scale=2, legend_width=300, only=None):
        """Each region outlined and numbered, the names beside it (only: just these, in this order)."""
        image = image.resize((image.width * scale, image.height * scale), Image.LANCZOS)
        shown = [r for r in regions if r["rect"][2] > 0 and r["rect"][3] > 0]
        if only is not None:
            shown = sorted((r for r in shown if r["name"] in only), key=lambda r: only.index(r["name"]))
        draw = ImageDraw.Draw(image)
        for number, region in enumerate(shown, 1):
            x, y, w, h = [v * scale for v in region["rect"]]
            colour = BOX_COLOURS[(number - 1) % len(BOX_COLOURS)]
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline=colour, width=2)
            draw.ellipse([x + 2, y + 2, x + 24, y + 24], fill=colour)
            draw.text((x + 13, y + 13), str(number), font=self.font(13), fill=(0, 0, 0), anchor="mm")
        out = Image.new("RGB", (image.width + legend_width, image.height), (18, 18, 18))
        out.paste(image, (0, 0))
        draw = ImageDraw.Draw(out)
        line = min(30, max(18, (image.height - 20) // max(len(shown), 1)))
        for number, region in enumerate(shown, 1):
            colour = BOX_COLOURS[(number - 1) % len(BOX_COLOURS)]
            y = 10 + (number - 1) * line
            draw.ellipse([image.width + 14, y, image.width + 6 + line, y + line - 8], fill=colour)
            draw.text((image.width + 10 + line // 2, y + (line - 8) // 2), str(number), font=self.font(max(10, line // 2 - 1)), fill=(0, 0, 0), anchor="mm")
            draw.text((image.width + 22 + line, y + (line - 8) // 2), region["name"], font=self.font(min(17, line - 6)), fill=(230, 230, 230), anchor="lm")
        return out


def render(gui, renders):
    python = str(Path(gui) / ".venv" / "bin" / "python")
    serve = [python, str(Path(gui) / "tools" / "theme_server" / "serve.py")]
    steps = [arg for step in STEPS for arg in ("--theme", step)]
    subprocess.run(serve + ["--themes", str(TUTORIAL), "--export", str(renders)] + steps +
                   ["--resolutions", "640x480", "--schemes", "all", "--langs", "en_US"], check=True)
    subprocess.run(serve + ["--themes", str(TUTORIAL), "--export", str(renders), "--theme", STEPS[-1],
                            "--resolutions", "480x320,720x720,1280x720", "--langs", "en_US,ja_JP"], check=True)
    themes = [arg for theme in sorted(p.name for p in (ROOT / "themes").iterdir() if p.is_dir()) for arg in ("--theme", theme)]
    subprocess.run(serve + ["--themes", str(ROOT / "themes"), "--export", str(renders)] + themes +
                   ["--resolutions", "640x480", "--langs", "en_US"], check=True)


def make(p):
    last = STEPS[-1]
    p.save(p.grid([p.caption(p.image(last, "main_menu", scheme="Night"), "Main menu · Night"),
                   p.caption(p.image(last, "ports_all", scheme="Night"), "Ports list · Night"),
                   p.caption(p.image(last, "port_info", scheme="Day"), "Port info · Day"),
                   p.caption(p.image(last, "filters", scheme="Day"), "Filters · Day")], 2), "hero.png")

    ## Each step: the screens it changed.
    shown = {"step-1": ("main_menu", "ports_all", "filters"), "step-2": ("main_menu", "ports_all", "message_box"),
             "step-3": ("main_menu", "ports_all"), "step-4": ("port_info", "filters", "messages"),
             "step-6": ("main_menu", "filters")}
    for step, screens in shown.items():
        if step in STEPS:
            p.save(p.grid([p.caption(p.image(step, s), s) for s in screens], len(screens)), f"{step}.png")
    if "step-2" in STEPS:
        p.save(p.boxes(p.image("step-2", "main_menu"), p.regions("step-2", "main_menu")), "step-2-regions.png")
    if "step-3" in STEPS:
        p.save(p.boxes(p.image("step-3", "ports_all"), p.regions("step-3", "ports_all")), "step-3-regions.png")
        p.save(p.boxes(p.image("step-3", "main_menu"), p.regions("step-3", "main_menu"),
                       only=["header", "left_pane", "right_pane", "footer"]), "step-3-panes.png")
    atlas(p)
    if "step-5" in STEPS:
        p.save(p.grid([p.caption(p.image("step-5", "ports_all", scheme=s), s) for s in ("Night", "Day")], 2), "step-5.png")

    sizes = [p.caption(scaled(p.image(last, "ports_all", size=size, scheme="Night"), 360), size)
             for size in ("480x320", "640x480", "720x720", "1280x720")]
    p.save(p.grid(sizes, 4), "step-7-sizes.png")
    p.save(p.grid([p.caption(p.image(last, "ports_all", scheme="Night"), "en_US"),
                   p.caption(p.image(last, "ports_all", size="1280x720", scheme="Night", lang="ja_JP").resize((640, 360)), "ja_JP, 1280x720")], 2), "step-7-languages.png")

    ## Every theme in the repository.
    themes = sorted(p.name for p in (ROOT / "themes").iterdir() if p.is_dir())
    cells = []
    for theme in themes:
        name = json.loads((ROOT / "themes" / theme / "theme.json").read_text(encoding="utf-8"))["#info"]["name"]
        try:
            cells.append(p.caption(p.image(theme, "ports_all").resize((480, 360), Image.LANCZOS), name, 16))
        except FileNotFoundError:
            pass
    p.save(p.grid(cells, 3), "gallery.jpg")


def atlas(p):
    """The tutorial's buttons.png, bigger, each piece outlined with its [ x, y, width, height ]."""
    source = TUTORIAL / STEPS[-1] / "buttons.png"
    if not source.exists():
        return
    zoom = 2
    image = Image.open(str(source)).convert("RGBA")
    big = image.resize((image.width * zoom, image.height * zoom), Image.LANCZOS)
    out = Image.new("RGB", (big.width + 40, big.height + 110), (24, 26, 32))
    out.paste(big, (20, 20), big)
    draw = ImageDraw.Draw(out)
    names = ["_A", "_B", "_X", "_Y", "_CHECKED", "_UNCHECKED"]
    for n, name in enumerate(names):
        x = 20 + n * 64 * zoom
        draw.rectangle([x, 20, x + 64 * zoom - 1, 20 + 64 * zoom - 1], outline=(255, 99, 71), width=2)
        draw.text((x + 64 * zoom // 2, 20 + 64 * zoom + 22), name, font=p.font(15), fill=(235, 235, 235), anchor="mm")
        draw.text((x + 64 * zoom // 2, 20 + 64 * zoom + 46), f"[ {n * 64}, 0, 64, 64 ]", font=p.font(13), fill=(160, 170, 185), anchor="mm")
    p.save(out, "atlas.png")


def scaled(image, height):
    return image.resize((round(image.width * height / image.height), height), Image.LANCZOS)


def editor_shot(gui, port=8099):
    """The theme server's editor, with the tutorial's last step open."""
    chrome = sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))
    if not chrome:
        print("no headless Chromium (playwright's): skipping the editor picture")
        return
    work = Path(tempfile.mkdtemp(prefix="render-docs-"))
    try:
        shutil.copytree(str(TUTORIAL / STEPS[-1]), str(work / "harbour_lights"))
        ## Step 1 with a mistake in it, for the editor's problem list: a comma left out.
        shutil.copytree(str(TUTORIAL / STEPS[0]), str(work / "my_first_theme"))
        first = (work / "my_first_theme" / "theme.json")
        first.write_text(first.read_text(encoding="utf-8").replace('"name": "Harbour Lights",', '"name": "Harbour Lights"', 1), encoding="utf-8")
        server = subprocess.Popen([str(Path(gui) / ".venv" / "bin" / "python"), str(Path(gui) / "tools" / "theme_server" / "serve.py"),
                                   "--themes", str(work), "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            import time
            import urllib.request
            for _ in range(100):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
                    break
                except OSError:
                    time.sleep(0.2)
            for name, query in (("editor.png", "#view=edit&theme=harbour_lights&res=640x480&scheme=Night"),
                                ("server.png", "#view=preview&mode=screens&theme=harbour_lights&res=640x480&scheme=Night"),
                                ("server-sizes.png", "#view=preview&mode=resolutions&modeShot=ports_all&theme=harbour_lights&scheme=Night"),
                                ("json-mistake.png", "#view=edit&theme=my_first_theme&res=640x480")):
                subprocess.run([str(chrome[-1]), "--headless", "--no-sandbox", "--hide-scrollbars", "--window-size=1440,900",
                                "--virtual-time-budget=25000", f"--screenshot={OUT / name}", f"http://127.0.0.1:{port}/{query}"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                print(f"docs/images/{name}")
        finally:
            server.terminate()
            server.wait()
    finally:
        shutil.rmtree(str(work), ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Makes CREATING_A_THEME.md's pictures (docs/images/).")
    parser.add_argument("--gui", type=Path, default=ROOT.parent / "PortMaster-GUI", help="a PortMaster-GUI checkout with its .venv")
    parser.add_argument("--renders", type=Path, help="an earlier run's renders, instead of rendering again")
    parser.add_argument("--no-editor", action="store_true", help="skip the pictures of the theme server's page")
    options = parser.parse_args(argv)

    renders = options.renders
    temporary = None
    if renders is None:
        temporary = renders = Path(tempfile.mkdtemp(prefix="render-docs-renders-"))
        render(options.gui, renders)
    try:
        make(Pictures(options.gui, renders))
        if not options.no_editor:
            editor_shot(options.gui)
    finally:
        if temporary is not None:
            shutil.rmtree(str(temporary), ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
