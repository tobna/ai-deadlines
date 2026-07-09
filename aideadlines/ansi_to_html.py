"""Convert an ANSI-colored log stream (stdin) into a standalone colored HTML page.

Used by make_website.sh to turn the update pipeline's colored output into the served
status page: ``python3 aideadlines/ansi_to_html.py html/status.html < status.ansi``

Stdlib only (no ansi2html/aha dependency). Handles the basic SGR codes loguru emits
(fg colors, bold, dim, reset); unknown codes (e.g. 256-color) are ignored.
"""

import html
import re
import sys

# Basic 8/16-color foreground palette (One-Dark-ish, readable on a dark background).
FG = {
    30: "#3f4451", 31: "#e05561", 32: "#8cc265", 33: "#d18f52",
    34: "#4aa5f0", 35: "#c162de", 36: "#42b3c2", 37: "#d7dae0",
    90: "#6b7280", 91: "#e05561", 92: "#8cc265", 93: "#d18f52",
    94: "#4aa5f0", 95: "#c162de", 96: "#42b3c2", 97: "#ffffff",
}


def render(text):
    """Turn ANSI SGR sequences into nested <span> styles; escape everything else."""
    fg, bold, dim = None, False, False

    def span(chunk):
        styles = []
        if fg:
            styles.append(f"color:{fg}")
        if bold:
            styles.append("font-weight:bold")
        if dim:
            styles.append("opacity:.6")
        attr = f' style="{";".join(styles)}"' if styles else ""
        return f"<span{attr}>{html.escape(chunk)}</span>"

    out = []
    # re.split with a capture group alternates: text, codes, text, codes, ...
    for idx, part in enumerate(re.split(r"\x1b\[([0-9;]*)m", text)):
        if idx % 2 == 0:
            if part:
                out.append(span(part))
            continue
        for raw in (part or "0").split(";"):
            code = int(raw or 0)
            if code == 0:
                fg, bold, dim = None, False, False
            elif code == 1:
                bold = True
            elif code == 2:
                dim = True
            elif code == 22:
                bold = dim = False
            elif code == 39:
                fg = None
            elif code in FG:
                fg = FG[code]
    return "".join(out)


_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<title>pipeline status</title>
<style>
  body {{ background:#1e2127; color:#d7dae0; margin:0; padding:1rem;
          font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  pre {{ white-space:pre-wrap; word-break:break-word; margin:0; }}
</style>
<pre>{body}</pre>
"""


def main(argv):
    with open(argv[1], "w") as f:
        f.write(_PAGE.format(body=render(sys.stdin.read())))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        r = render("\x1b[31m<b>\x1b[0m ok")
        assert "color:" in r and "&lt;b&gt;" in r and "ok" in r, r
        assert "=== PIPELINE OK ===" in render("=== PIPELINE OK ===")  # keyword survives verbatim
        print("selftest ok")
    else:
        main(sys.argv)
