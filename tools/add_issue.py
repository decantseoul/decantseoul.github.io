#!/usr/bin/env python3
"""디캔트 서울 데일리 뉴스 한 호를 사이트에 추가한다.

사용법: python3 tools/add_issue.py <뉴스레터 HTML 파일>
- 입력은 아티팩트에 올리는 decant-daily-news.html(또는 아티팩트를 읽어 저장한 전체 HTML).
- 날짜는 HTML의 .date(YYYY.MM.DD)에서 읽는다.
- 결과: issues/YYYY-MM-DD/index.html, index.html(최신호), archive/index.html, assets/fonts/*.woff2
"""
import base64, hashlib, html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://decantseoul.com"
FONTS = ROOT / "assets" / "fonts"
DATA = ROOT / "issues" / "issues.json"


def extract(src: str):
    # 아티팩트 뼈대(<!doctype…<body>)가 있으면 걷어내기
    if "<body>" in src:
        src = src.split("<body>", 1)[1]
    src = re.sub(r"</body>\s*</html>\s*$", "", src.strip())
    src = re.sub(r"<title>.*?</title>", "", src, flags=re.S)
    src = re.sub(r'<meta name="claude:[^>]*>', "", src)
    styles = "\n".join(re.findall(r"<style>(.*?)</style>", src, flags=re.S))
    body = re.sub(r"<style>.*?</style>", "", src, flags=re.S).strip()
    return styles, body


def externalize_fonts(css: str) -> str:
    FONTS.mkdir(parents=True, exist_ok=True)

    def repl(m):
        data = base64.b64decode(m.group(1))
        name = hashlib.sha1(data).hexdigest()[:12] + ".woff2"
        p = FONTS / name
        if not p.exists():
            p.write_bytes(data)
        return f"url('/assets/fonts/{name}')"

    return re.sub(r"url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)", repl, css)


def page(title, desc, url, css, body):
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="decant.seoul">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}">
<link rel="canonical" href="{url}">
<style>{css}
body{{margin:0}}
.site-nav{{display:flex;justify-content:center;gap:18px;margin-top:22px}}
.site-nav a{{font-size:12px;letter-spacing:.08em;color:#8f8f8f;border-bottom:1px solid #555;padding-bottom:2px}}
</style>
</head><body>
{body}
</body></html>
"""


def nav(prefix=""):
    return ('<nav class="site-nav"><a href="/">최신호</a>'
            '<a href="/archive/">지난 호 보기</a></nav>')


def main(path):
    src = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r'class="?date"?><i>\|</i>([0-9]{4})\.([0-9]{2})\.([0-9]{2})', src)
    if not m:
        sys.exit("날짜(.date)를 찾지 못했습니다")
    y, mo, d = m.groups()
    iso, dot = f"{y}-{mo}-{d}", f"{y}.{mo}.{d}"
    css, body = extract(src)
    css = externalize_fonts(css)
    # 푸터에 최신호·지난 호 링크 추가
    body = re.sub(r'(<span class="?cap"?>See you tomorrow morning</span>)', nav() + r"\1", body, count=1)
    picks = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
             for p in re.findall(r'class="?pick-h"?>(.*?)</div>', body, flags=re.S)]
    desc = "오늘의 픽 · " + " / ".join(picks[:3]) if picks else "소믈리에와 에디터의 미식 매거진"
    title = f"디캔트 서울 데일리 뉴스 {dot}"

    out = ROOT / "issues" / iso
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(title, desc, f"{SITE}/issues/{iso}/", css, body), encoding="utf-8")

    data = json.loads(DATA.read_text()) if DATA.exists() else {}
    data[iso] = {"date": dot, "picks": picks[:5]}
    DATA.write_text(json.dumps(dict(sorted(data.items(), reverse=True)), ensure_ascii=False, indent=1))

    latest = max(data)
    lsrc = (ROOT / "issues" / latest / "index.html").read_text(encoding="utf-8")
    lsrc = lsrc.replace(f'href="{SITE}/issues/{latest}/"', f'href="{SITE}/"').replace(
        f'content="{SITE}/issues/{latest}/"', f'content="{SITE}/"')
    (ROOT / "index.html").write_text(lsrc, encoding="utf-8")
    build_archive(data, css)
    print("added", iso, "latest", latest)


def build_archive(data, css):
    fontcss = "\n".join(re.findall(r"@font-face\{.*?\}", css, flags=re.S))
    rows = []
    for iso, v in sorted(data.items(), reverse=True):
        p = "".join(f"<li>{html.escape(x)}</li>" for x in v["picks"][:3])
        rows.append(f'<a class="row" href="/issues/{iso}/"><span class="d">{v["date"]}</span>'
                    f'<ul>{p}</ul><span class="go">읽기 →</span></a>')
    body = f"""<header class="mast"><div class="folio"><span class="cap">Wine &amp; Gourmet Magazine</span>
<a href="https://www.instagram.com/decant.seoul/">@decant.seoul</a></div>
<a class="logo" href="/">decant.<small>seoul</small></a>
<div class="tag">소믈리에와 에디터의 미식 매거진</div></header>
<main><h1>Daily News <em>Archive</em></h1><p class="sub">지난 데일리 뉴스</p>
{''.join(rows)}</main>
<footer><a href="/">최신호 보기</a> · <a href="https://www.instagram.com/decant.seoul/">@decant.seoul</a></footer>"""
    acss = fontcss + """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;color:#0a0a0a;font-family:'Pretendard','Noto Sans CJK KR',sans-serif;word-break:keep-all;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.mast,main,footer{max-width:640px;margin:0 auto;padding-left:max(18px,env(safe-area-inset-left,0px));padding-right:max(18px,env(safe-area-inset-right,0px))}
.mast{text-align:center;padding-top:20px;padding-bottom:36px}
.folio{display:flex;justify-content:space-between;font-size:11px;font-weight:600;padding-bottom:11px;border-bottom:1px solid #0a0a0a}
.cap{font-size:9px;letter-spacing:.32em;text-transform:uppercase}
.logo{display:block;font-family:'Playfair';font-style:italic;font-weight:900;font-size:clamp(56px,14vw,88px);line-height:1;margin-top:30px}
.logo small{font-weight:400;font-size:.36em}
.tag{margin-top:14px;font-size:13px;letter-spacing:.16em;color:#5e5e5e}
h1{font-family:'Playfair';font-weight:400;font-size:40px;text-align:center;border-top:2px solid #0a0a0a;padding-top:28px}
h1 em{font-style:italic}
.sub{text-align:center;font-size:12px;color:#8c8c8c;margin:8px 0 22px}
.row{display:grid;grid-template-columns:96px 1fr auto;gap:14px;align-items:start;padding:18px 0;border-top:1px solid #e4e2de}
.row:last-of-type{border-bottom:1px solid #0a0a0a}
.d{font-family:'Playfair';font-style:italic;font-size:17px}
.row ul{list-style:none;font-size:13px;line-height:1.6;color:#3d3d3d;min-width:0}
.row li{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.go{font-size:11px;font-weight:600;border-bottom:1px solid #0a0a0a}
footer{text-align:center;font-size:12px;color:#8c8c8c;padding-top:40px;padding-bottom:60px}
@media (max-width:480px){.row{grid-template-columns:1fr}.go{justify-self:start}}
"""
    out = ROOT / "archive"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(
        page("디캔트 서울 데일리 뉴스 아카이브", "decant.seoul 데일리 와인·미식 뉴스 지난 호",
             f"{SITE}/archive/", acss, body).replace(".site-nav", ".x-nav"), encoding="utf-8")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
