#!/usr/bin/env python3

"""

This is used to create the themes.json and themes.pot file on PR.

"""

import datetime
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import urllib
import urllib.request
import zipfile

from pathlib import Path


TRANSLATION_HEADER = r"""# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2023-09-09 16:35+0800\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"Language: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"

"""


def fetch_url(url):
    try:
        # Open the URL
        with urllib.request.urlopen(url) as response:
            # Read the content of the file
            file_content = response.read()

        # Decode the bytes to a string (assuming the file is in UTF-8 encoding)
        return file_content.decode('utf-8')

    except urllib.error.URLError as e:
        return None

    except UnicodeDecodeError as e:
        return None


def hash_file(file):
    md5 = hashlib.md5()
    with open(file, 'rb') as fh:
        while True:
            data = fh.read(1024 * 1024)
            if len(data) == 0:
                break

            md5.update(data)

    return md5.hexdigest()


def hash_text(text):
    md5 = hashlib.md5()
    if isinstance(text, str):
        md5.update(text.encode('utf-8'))
    else:
        md5.update(text)

    return md5.hexdigest()


def parse_translations(zip_file_name, translations, text):
    source_name = f"{zip_file_name}/theme.json"

    for lineno, line in enumerate(text.split('\n'), 1):
        line_1=line.strip()
        if not line_1.startswith('"text":'):
            continue

        line_2 = line_1.split('"', 3)[-1]
        line_3 = line_2.rsplit('"', 1)[0]

        if line_3.strip() == "":
            continue

        if re.match(r"^\{[^}]+\}$", line_3):
            continue

        if re.match(r"^#[0-9a-f]+$", line_3, re.I):
            continue

        source = f"{source_name}:{lineno}"
        translations.setdefault(line_3, []).append(source)


def dump_tr_string(string):
    if "\\n" in string:
        result = ['""']
        items = string.split("\\n")
        for line in items[:-1]:
            result.append(f'"{line}\\n"')
        result.append(f'"{items[-1]}"')
        return "\n".join(result)

    return f'"{string}"'


def dump_translations(file_name, translations):
    with open(file_name, "w") as fh:
        print(TRANSLATION_HEADER, file=fh)

        for translation, sources in translations.items():
            for offset in range(0, len(sources), 5):
                print(f"#: {', '.join(sources[offset:(offset+5)])}", file=fh)

            print(f"msgid {dump_tr_string(translation)}", file=fh)
            print(f"msgstr {dump_tr_string('')}", file=fh)
            print("", file=fh)


def zip_get_theme_info(zip_file, translations):
    theme_info = {
        "name": None,
        "creator": None,
        "image": None,
        "file": zip_file.name,
        "md5": hash_file(zip_file),
        }

    try:
        base_name = zip_file.name.rsplit('.', 2)[0]

        with zipfile.ZipFile(zip_file, 'r') as zf:
            for file_info in zf.infolist():

                if file_info.filename.endswith('/'):
                    continue

                file_name = file_info.filename.rsplit('/', 1)[-1].lower()

                if file_name == 'theme.json':
                    theme_data = json.loads(zf.read(file_info.filename).decode('utf-8'))

                    parse_translations(zip_file.name, translations, zf.read(file_info.filename).decode('utf-8'))

                    theme_info["name"] = theme_data.get("#info", {}).get("name", base_name)
                    theme_info["creator"] = theme_data.get("#info", {}).get("creator", "")
                    theme_info["description"] = theme_data.get("#info", {}).get("description", "")

                    continue

                if file_name in ('screenshot.jpg', 'screenshot.png'):
                    image_file = zip_file.parent / (zip_file.name.rsplit('.', 2)[0] + '.' + file_name)

                    with open(image_file, 'wb') as fh:
                        fh.write(zf.read(file_info.filename))

                    theme_info["image"] = image_file.name

                    continue

    except Exception as err:
        print(f"{zip_file}: {err}")
        return None

    if theme_info["name"] is None or theme_info["creator"] is None:
        print(f'{zip_file}: Bad theme file, no "name" or "creator" info.')
        return None

    # if theme_info["image"] is None:
    #     print(f'{zip_file}: Bad theme file, no preview image found.')
    #     return None

    return theme_info


def main():
    git_path = Path('.')

    themes = {
        "version": 1,
        "themes": {}
        }

    translations = {
        }

    default_theme = fetch_url("https://github.com/kloptops/harbourmaster/raw/main/pylibs/default_theme/theme.json")
    if default_theme is not None:
        parse_translations("default_theme", translations, default_theme)

    for theme_zip in git_path.glob("*.theme.zip"):
        theme_info = zip_get_theme_info(theme_zip, translations)
        if theme_info is None:
            continue

        themes["themes"][theme_info["file"].rsplit('.', 2)[0]] = theme_info

    # print(json.dumps(themes, indent=4))
    with open("themes.json", "w") as fh:
        json.dump(themes, fh, indent=4)

    dump_translations("themes.pot", translations)


if __name__ == '__main__':
    main()
