# PortMaster-Themes

The themes PortMaster lists in **Options › Select Theme**. Each one is a folder in `themes/`:

```
themes/<name>/
  theme.json        the theme (see PortMaster-GUI's THEME.md)
  screenshot.png    its preview in the theme list (or .jpg)
  CREDITS.md        every font it carries: its author and license, and the license file
  LICENSE.*.txt     those license files
  ...               its images, fonts and sounds
```

A push to `main` makes a release: `tools/build_themes.py` zips each folder into `<name>.theme.zip`
(a `<name>/` folder inside, as PortMaster installs it) with its md5, and writes `themes.json`,
`images.zip` and `theme_translations.json`, which PortMaster reads from the latest release. The zips
come out the same every time, so a theme nobody changed keeps its md5 and PortMaster doesn't offer
it as an update.

## Adding or changing a theme

1. Put the theme's folder in `themes/`, named as its zip should be (no spaces).
2. `#info` in `theme.json` needs a `name` and a `creator`; a `description` shows in the theme list.
3. **Every font in the folder needs a license that lets PortMaster share it** (freeware,
   non-commercial is fine), listed in `CREDITS.md` with the license file next to it, like:

   ```
   | File | Font | Author | License |
   |---|---|---|---|
   | `Inter-Medium.otf` | Inter Medium | Rasmus Andersson | SIL Open Font License 1.1 ([LICENSE.inter.txt](LICENSE.inter.txt)) |
   ```

   PortMaster's own fonts (DejaVu Sans, and Noto Sans CJK for Chinese, Japanese and Korean) are
   in every PortMaster, so a theme can name them without carrying them.
4. Check it: `python3 tools/build_themes.py --check-only`, then the layout with PortMaster's
   theme server (in a PortMaster-GUI checkout):

   ```
   python3 tools/theme_server/serve.py --themes ../PortMaster-Themes/themes --export /tmp/out \
       --theme <name> --resolutions 640x480,1280x720,1240x1080,720x1280 --schemes all --check
   ```

   It lists text and images of two regions on top of each other, and content off the screen or
   outside its region, at screen sizes the theme doesn't name. A pull request runs both.
