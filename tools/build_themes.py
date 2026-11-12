#!/usr/bin/env python3
"""
Builds the release from the theme folders: themes/<name>/ becomes release/<name>.theme.zip
(with a <name>/ folder inside, as PortMaster installs it), plus what PortMaster's theme list
reads from the release:

  themes.json               every theme's name, creator, description, zip, md5 and preview image
  <name>.screenshot.png     each theme's preview (or .jpg)
  images.zip                the previews, together
  theme_translations.json   the "text" of every theme, and where it's used (for translators)
  *.md5                     next to every zip

The zips are made the same way every time (files in order, fixed dates and modes), so a
theme nobody changed keeps its md5 and PortMaster doesn't offer it as an update.

Checks, which fail the build: theme.json parses and has #info name and creator, and every
font file a theme carries is listed in its CREDITS.md with its license.

    python3 tools/build_themes.py [--out release] [--check-only] [--theme NAME...]
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES_DIR = ROOT / "themes"

## Every entry gets this date: the zip's bytes then depend only on the files.
ZIP_DATE = (2021, 1, 1, 0, 0, 0)
## theme.md5: PortMaster writes it when it installs a theme (the zip's md5); in a theme it's stale.
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", "theme.md5"}
FONT_SUFFIXES = (".ttf", ".otf", ".ttc")


def theme_files(theme_dir):
    """The theme's files, as (path, name in the zip), sorted by the name in the zip."""
    files = []
    for path in theme_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(theme_dir)
        ## Zone.Identifier: Windows' "downloaded from the internet" note, copied from WSL as a file of its own.
        if any(part in SKIP_NAMES or part.startswith(("._", ".git")) or part.endswith("Zone.Identifier")
               for part in relative.parts):
            continue
        files.append((path, theme_dir.name + "/" + relative.as_posix()))

    return sorted(files, key=lambda item: item[1].casefold())


def write_zip(zip_path, entries):
    """entries: (zip name, bytes). Deflated, fixed date, mode 644."""
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 << 16)
            info.create_system = 3      ## Unix, so the mode is read on every platform
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def md5_file(path):
    digest = hashlib.md5()
    with open(str(path), "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def theme_texts(theme_name, text, translations):
    """Every "text" value in theme.json, with its line, as themes.py collected them."""
    source = f"{theme_name}.theme.zip/theme.json"
    for lineno, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if not stripped.startswith('"text":'):
            continue
        value = stripped.split('"', 3)[-1].rsplit('"', 1)[0]
        if value.strip() == "" or re.match(r"^\{[^}]+\}$", value) or re.match(r"^#[0-9a-f]+$", value, re.I):
            continue
        translations.setdefault(value, []).append(f"{source}:{lineno}")


def check_theme(theme_dir):
    """The problems that stop a theme from being released."""
    problems = []
    theme_file = theme_dir / "theme.json"
    if not theme_file.is_file():
        return ["no theme.json"]

    try:
        data = json.loads(theme_file.read_text(encoding="utf-8"))
    except ValueError as error:
        return [f"theme.json: {error}"]

    info = data.get("#info", {}) if isinstance(data, dict) else {}
    for key in ("name", "creator"):
        if not info.get(key):
            problems.append(f'theme.json: #info has no "{key}"')

    fonts = sorted(path.name for path in theme_dir.rglob("*") if path.suffix.lower() in FONT_SUFFIXES)
    credits = theme_dir / "CREDITS.md"
    credits_text = credits.read_text(encoding="utf-8") if credits.is_file() else ""
    for font in fonts:
        lines = [line for line in credits_text.splitlines() if font in line]
        if not lines:
            problems.append(f"{font}: not in CREDITS.md (each font needs its author, license and license file)")
        elif any("unknown license" in line.lower() for line in lines):
            problems.append(f"{font}: its license is unknown (CREDITS.md): replace it with a font that has one")

    for license_file in re.findall(r"\((LICENSE[^)\s]*)\)", credits_text):
        if not (theme_dir / license_file).is_file():
            problems.append(f"CREDITS.md names {license_file}, which isn't there")

    return problems


def build(out_dir, check_only=False, only=()):
    out_dir.mkdir(parents=True, exist_ok=True)
    themes = {"version": 1, "themes": {}}
    translations = {}
    previews = []
    failed = False

    for theme_dir in sorted((p for p in THEMES_DIR.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
        if only and theme_dir.name not in only:
            continue
        problems = check_theme(theme_dir)
        if problems:
            failed = True
            for problem in problems:
                print(f"{theme_dir.name}: {problem}")
            continue

        if check_only:
            continue

        name = theme_dir.name
        theme_text = (theme_dir / "theme.json").read_text(encoding="utf-8")
        info = json.loads(theme_text).get("#info", {})
        theme_texts(name, theme_text, translations)

        zip_path = out_dir / f"{name}.theme.zip"
        write_zip(zip_path, [(zip_name, path.read_bytes()) for path, zip_name in theme_files(theme_dir)])
        md5 = md5_file(zip_path)
        (out_dir / f"{zip_path.name}.md5").write_text(md5 + "\n")

        image = None
        for preview in ("screenshot.png", "screenshot.jpg"):
            if (theme_dir / preview).is_file():
                image = f"{name}.{preview}"
                (out_dir / image).write_bytes((theme_dir / preview).read_bytes())
                previews.append((image, (theme_dir / preview).read_bytes()))
                break

        themes["themes"][name] = {
            "name": info.get("name", name),
            "creator": info.get("creator", ""),
            "image": image,
            "file": zip_path.name,
            "md5": md5,
            "description": info.get("description", ""),
            }
        print(f"{zip_path.name}: {md5}")

    if failed:
        print("build failed: fix the problems above")
        return 1

    if check_only:
        print("all themes pass")
        return 0

    write_zip(out_dir / "images.zip", sorted(previews))
    (out_dir / "images.zip.md5").write_text(md5_file(out_dir / "images.zip") + "\n")
    (out_dir / "themes.json").write_text(json.dumps(themes, indent=4) + "\n")
    (out_dir / "theme_translations.json").write_text(json.dumps(translations, indent=4) + "\n")
    print(f"{len(themes['themes'])} themes -> {out_dir}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Builds the themes release from themes/<name>/.")
    parser.add_argument("--out", type=Path, default=ROOT / "release")
    parser.add_argument("--check-only", action="store_true", help="only run the checks")
    parser.add_argument("--theme", action="append", default=[], help="only this theme (a folder in themes/): to try one")
    options = parser.parse_args(argv)
    return build(options.out, options.check_only, set(options.theme))


if __name__ == "__main__":
    sys.exit(main())
