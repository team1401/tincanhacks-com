#!/usr/bin/env python3
"""Build tincanhacks.com static site from content/posts/*.md into site/.

Zero dependencies: a small markdown subset parser (frontmatter, headings,
paragraphs, fenced code, lists, bold/italic/inline-code/links).
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content" / "posts"
OUT = ROOT

CSS = """
:root{--bg:#141619;--panel:#1c1f24;--ink:#d8dade;--dim:#8b9099;--silver:#c0c5cc;
--amber:#e8a33d;--line:#2b2f36;--code:#181a1e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 ui-serif,Georgia,"Times New Roman",serif}
.wrap{max-width:720px;margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--line);padding:36px 0 20px}
header.site h1{margin:0;font:700 28px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;
letter-spacing:.06em;color:var(--silver)}
header.site h1 .can{color:var(--amber)}
header.site p.tag{margin:6px 0 0;color:var(--dim);font-size:14px;font-style:italic}
nav.site{font:13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;margin-top:14px}
nav.site a{color:var(--dim);text-decoration:none;margin-right:18px}
nav.site a.on,nav.site a:hover{color:var(--amber)}
main{padding:36px 0 60px}
article.post h2{font:600 22px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;
color:var(--silver);margin:0 0 4px}
.post-meta{color:var(--dim);font:12px/1 ui-monospace,SFMono-Regular,Menlo,monospace;
margin-bottom:22px}
.post-meta .date{color:var(--amber)}
article.post p{margin:0 0 18px}
article.post h3{font:600 17px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--silver)}
article.post ul{padding-left:22px}
article.post li{margin-bottom:6px}
a{color:var(--amber)}
.post-list{list-style:none;margin:0;padding:0}
.post-list li{border-bottom:1px solid var(--line);padding:18px 0}
.post-list a.title{font:600 18px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;
color:var(--silver);text-decoration:none}
.post-list a.title:hover{color:var(--amber)}
.post-list .date{display:block;font:12px/1 ui-monospace,Menlo,monospace;color:var(--dim);
margin-bottom:6px}
.post-list .summary{color:var(--dim);margin:6px 0 0;font-size:15px}
pre{background:var(--code);border:1px solid var(--line);border-radius:6px;
padding:14px 16px;overflow-x:auto;font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;
color:#c8e1b8;margin:0 0 18px}
code{font:13.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--code);
padding:1px 5px;border-radius:4px;color:#c8e1b8}
pre code{background:none;padding:0}
footer.site{border-top:1px solid var(--line);padding:20px 0 40px;color:var(--dim);
font-size:13px}
.back{font:13px ui-monospace,Menlo,monospace;display:inline-block;margin-bottom:26px;
color:var(--dim);text-decoration:none}
.back:hover{color:var(--amber)}
@media(max-width:600px){body{font-size:15px}header.site h1{font-size:22px}}
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<div class="wrap">
<header class="site">
<h1>TIN<span class="can">CAN</span>HACKS</h1>
<p class="tag">Tech and AI work logged from a 1979 Airstream and wherever it's parked.</p>
<nav class="site"><a class="{home}" href="{root}index.html">index</a><a href="{root}about.html">about</a></nav>
</header>
<main>
{body}
</main>
<footer class="site">tincanhacks.com &middot; Brian Smith &middot; built with Helix, an AI agent</footer>
</div>
</body>
</html>
"""

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def inline(text):
    esc = html.escape(text, quote=False)
    esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", esc)
    esc = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', esc)
    return esc


def md_to_html(md):
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="{lang}"' if lang else ""
            out.append(f"<pre{cls}>{html.escape(chr(10).join(buf))}</pre>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            lvl = min(len(m.group(1)) + 1, 5)  # h1 taken by page title
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append(f"<li>{inline(re.sub(r'^[-*]\\s+', '', lines[i]))}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if not line.strip():
            i += 1
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|```|[-*]\s)", lines[i]
        ):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def build():
    posts = []
    for p in sorted(CONTENT.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if not fm.get("title") or not fm.get("date"):
            print(f"SKIP {p.name}: missing title/date frontmatter", file=sys.stderr)
            continue
        posts.append({"file": p, "fm": fm, "body": body})
    if not posts:
        sys.exit("no posts found in content/posts/")
    posts.sort(key=lambda x: x["fm"]["date"], reverse=True)

    OUT.mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS, encoding="utf-8")

    items = []
    for post in posts:
        fm = post["fm"]
        slug = post["file"].stem + ".html"
        body = md_to_html(post["body"])
        page = PAGE.format(
            title=html.escape(fm["title"]) + " · TinCanHacks",
            root="",
            home="",
            body=(
                f'<a class="back" href="index.html">&larr; index</a>\n'
                f'<article class="post"><h2>{html.escape(fm["title"])}</h2>'
                f'<div class="post-meta"><span class="date">{html.escape(fm["date"])}</span>'
                + (f' · {html.escape(fm["category"])}' if fm.get("category") else "")
                + f"</div>{body}</article>"
            ),
        )
        (OUT / slug).write_text(page, encoding="utf-8")
        summary = fm.get("summary", "")
        if not summary:
            first = next(
                (ln for ln in post["body"].splitlines() if ln.strip()), ""
            )
            summary = re.sub(r"[#*`>-]", "", first).strip()[:160]
        items.append(
            f'<li><span class="date">{html.escape(fm["date"])}</span>'
            f'<a class="title" href="{slug}">{html.escape(fm["title"])}</a>'
            + (f'<p class="summary">{html.escape(summary)}</p>' if summary else "")
            + "</li>"
        )

    index = PAGE.format(
        title="TinCanHacks",
        root="",
        home="on",
        body='<ul class="post-list">' + "".join(items) + "</ul>",
    )
    (OUT / "index.html").write_text(index, encoding="utf-8")

    about = PAGE.format(
        title="About · TinCanHacks",
        root="",
        home="",
        body=(
            "<article class=\"post\"><h2>About</h2>"
            "<p>Tin Can Hacks is where Brian Smith logs the tech and AI work done from a "
            "1979 Airstream Sovereign: the projects that shipped, the ones that got "
            "abandoned honestly, and the ones that were only ever talked about at 60 mph. "
            "Most of it is built with Helix, an AI agent who writes the code, runs the "
            "tests, and occasionally writes the prose.</p>"
            "<p>The archive is backfilled from the real work log, so dates match when the "
            "work actually happened rather than when the site went up.</p></article>"
        ),
    )
    (OUT / "about.html").write_text(about, encoding="utf-8")
    print(f"built {len(posts)} posts -> {OUT}")


if __name__ == "__main__":
    build()
