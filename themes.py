#!/usr/bin/env python3

"""

This is used to create the themes.json file on PR.

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
import zipfile

from pathlib import Path


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


def zip_get_theme_info(zip_file):
    theme_info = {
        "name": None,
        "creator": None,
        "image": None,
        "file": zip_file.name,
        "md5": hash_file(zip_file),
        }

    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for file_info in zf.infolist():

                if file_info.filename.endswith('/'):
                    continue

                file_name = file_info.filename.rsplit('/', 1)[-1].lower()

                if file_name == 'theme.json':
                    theme_data = json.loads(zf.read(file_info.filename).decode('utf-8'))

                    theme_info["name"] = theme_data.get("#info", {}).get("name", None)
                    theme_info["creator"] = theme_data.get("#info", {}).get("creator", None)

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

    for theme_zip in git_path.glob("*.theme.zip"):
        theme_info = zip_get_theme_info(theme_zip)
        if theme_info is None:
            continue

        themes["themes"][theme_info["file"].rsplit('.', 2)[0]] = theme_info

    # print(json.dumps(themes, indent=4))
    with open("themes.json", "w") as fh:
        json.dump(themes, fh, indent=4)


if __name__ == '__main__':
    main()
