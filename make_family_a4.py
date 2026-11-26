# -*- coding: utf-8 -*-
"""우리집 주간표 (서원·서준 통합, A4 세로) — schedule.json → PDF/PNG

    python make_family_a4.py          # 저장소 루트에서 실행
    → 우리집_주간표_A4.pdf, 우리집_주간표_A4.png

요일 = 열(월~금), 열 안에 서원(왼쪽·둥근 칩)·서준(오른쪽·각진 칩) 레인, 세로 시간 비례축.
오전은 접어서 띠로, 모든 요일이 비는 40분 이상 구간은 '일정 없음' 띠로 접는다(데이터로 계산).
주말은 아래 '주말' 줄. 구분: 빗금=학교·유치원, 테두리=방과후, 꽉 찬=학원·과외(밖·집·온라인).
글자 폭은 Noto Sans KR 가변 폰트로 실측해 14→13→12pt, 한 줄→두 줄 순으로 맞춘다.
중간 HTML은 임시 폴더에 만들고 크롬 헤드리스로 인쇄한다.
"""
import json, sys, re, subprocess, html, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent      # Time_table (저장소 루트)
DATA = ROOT / "schedule.json"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONT_FILE = "C:/Windows/Fonts/NotoSansKR-VF.ttf"

DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
KIDS = [  # who, 이름, 배지 글자, css 키, 설명
    ("첫째", "서원", "원", "won", "초2"),
    ("둘째", "서준", "준", "jun", "유치원"),
]
PT = 0.3528  # mm per pt

# ---------------------------------------------------------------- 글자 폭 실측
_fonts = {}
def tw(text, pt, wght=400, ls=0.0):
    """text 폭(mm). ls = letter-spacing(em)."""
    try:
        from PIL import ImageFont
        f = _fonts.get(wght)
        if f is None:
            f = ImageFont.truetype(FONT_FILE, 200)
            try:
                f.set_variation_by_axes([wght])
            except Exception:
                pass
            _fonts[wght] = f
        em = f.getlength(text) / 200
    except Exception:
        em = sum(0.98 if ord(c) > 0x1100 else 0.56 for c in text)
    return (em + ls * len(text)) * pt * PT

# ---------------------------------------------------------------- 데이터
def mins(t):
    h, m = t.split(":"); return int(h) * 60 + int(m)

def hm(m):
    return f"{m // 60}:{m % 60:02d}"

def short_name(ev):
    if ev.get("short"):
        return ev["short"]
    t = ev["title"]
    for p in ("방과후 ", "맞춤형 "):
        if t.startswith(p):
            t = t[len(p):]
    return t.strip()

def short_place(ev):
    if ev.get("place_short") is not None:
        return ev["place_short"]
    p = ev.get("place", "") or ""
    p = re.sub(r"\s*\(.*?\)", "", p).strip()
    p = re.sub(r"\s*(미술|음악)?학원$", "", p).strip() or p
    if p and p.replace("장", "") == ev["title"]:   # 태권도 · 태권도장 같은 중복 제거
        p = ""
    return p

def note_bits(ev):
    """note → (함께 여부, 픽업 문구, 기타 메모)"""
    note = ev.get("note", "") or ""
    parts = [x.strip() for x in note.split("·") if x.strip()]
    joint = any("함께" in x for x in parts)
    pickup = next((x for x in parts if "픽업" in x), "")
    rest = [x for x in parts if "함께" not in x and "픽업" not in x and x != "추정"]
    return joint, pickup, " ".join(rest)

def load(data=None):
    raw = json.loads(Path(data or DATA).read_text(encoding="utf-8"))
    who_map = {k[0]: k for k in KIDS}
    evs = []
    for r in raw:
        if r["who"] not in who_map or r["day"] not in DAY_ORDER:
            continue
        e = dict(r)
        e["S"], e["E"] = mins(r["s"]), mins(r["e"])
        e["kid"] = who_map[r["who"]]
        cat = r.get("cat", "")
        e["kind"] = ("pickup" if cat in ("돌봄/픽업", "care") else
                     "inst" if cat in ("정규수업", "school") else
                     "after" if cat in ("방과후", "afterschool") else "out")
        e["joint"], e["pickup"], e["memo"] = note_bits(r)
        evs.append(e)
    # '함께'는 note에 적힌 것만 인정(같은 시각·같은 제목이라도 따로 하는 수업일 수 있음)
    days = []
    for d in DAY_ORDER:
        lanes = []
        for k in KIDS:
            mine = [e for e in evs if e["day"] == d and e["kid"] == k]
            weekday = d not in ("토", "일")
            if mine or weekday:
                acts = sorted([e for e in mine if e["kind"] in ("after", "out")], key=lambda e: e["S"])
                for a, b in zip(acts, acts[1:]):
                    if b["S"] < a["E"]:
                        print(f"[경고] {d} {k[1]} 일정 겹침: {a['title']} / {b['title']}")
                lanes.append({
                    "kid": k,
                    "inst": next((e for e in mine if e["kind"] == "inst"), None),
                    "pick": sorted([e for e in mine if e["kind"] == "pickup"], key=lambda e: e["S"]),
                    "acts": acts,
                })
        if any(l["inst"] or l["acts"] for l in lanes):
            days.append({"day": d, "lanes": lanes})
    empty = [d for d in DAY_ORDER if d not in [x["day"] for x in days]]
    return evs, days, empty

def esc(s):
    return html.escape(str(s), quote=True)

# ---------------------------------------------------------------- 공통 CSS
BASE_CSS = """
@font-face{font-family:"NotoKR";src:local("Noto Sans KR"),url("file:///C:/Windows/Fonts/NotoSansKR-VF.ttf") format("truetype");font-weight:100 900;}
:root{
  --paper:#FFFFFF; --ink:#111111; --ink-2:#4A4A4A; --ink-3:#8A8A8A;
  --grid-hour:#9A9A9A; --grid-half:#C8C8C8; --hatch:#B5B5B5;
  --won:#9C4C98; --won-tint:#F3E6F2;   /* 회색 약 109 */
  --jun:#173F78; --jun-tint:#E4EDF8;   /* 회색 약 58 */
  --rule-day:1.2pt solid var(--ink);
  --rule-lane:0.5pt solid var(--ink-3);
  --chip-outline:1.6pt;
  --r-won:2.5mm; --r-jun:0;
  --badge:6.6mm;
  --font:"NotoKR","Noto Sans KR","Malgun Gothic",sans-serif;
  --fs-day:28pt; --fs-title:20pt; --fs-name:14pt; --fs-time:9.5pt; --fs-meta:7.5pt;
  --ls-name:-0.02em;
}
@page{size:A4 landscape;margin:0;}
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
html,body{background:var(--paper);}
body{font-family:var(--font);color:var(--ink);font-variant-numeric:tabular-nums;}
.page{position:relative;width:297mm;height:210mm;overflow:hidden;background:var(--paper);}
.abs{position:absolute;}

/* 머리 */
.head{left:8mm;top:7mm;right:8mm;height:12mm;display:flex;align-items:flex-end;gap:5mm;border-bottom:var(--rule-day);padding-bottom:1.6mm;}
.head h1{font-size:var(--fs-title);font-weight:800;letter-spacing:-0.03em;line-height:1;}
.head .sub{font-size:9pt;font-weight:500;color:var(--ink-2);line-height:1.2;}
.head .kids{margin-left:auto;display:flex;gap:5mm;align-items:center;}
.kidkey{display:flex;align-items:center;gap:1.6mm;font-size:9pt;font-weight:500;color:var(--ink-2);line-height:1.15;}
.kidkey b{font-size:12pt;font-weight:800;color:var(--ink);}

/* 배지 */
.badge{width:var(--badge);height:var(--badge);display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:12.5pt;font-weight:900;line-height:1;flex:none;}
.badge.won{background:var(--won);border-radius:50%;}
.badge.jun{background:var(--jun);border-radius:0;}

/* 요일 */
.dayname{display:flex;align-items:center;justify-content:center;font-size:var(--fs-day);font-weight:900;line-height:1;letter-spacing:-0.02em;}
.rule-day{height:0;border-top:var(--rule-day);}
.rule-lane{height:0;border-top:0.5pt dashed var(--ink-3);}

/* 학교·유치원 = 빗금 띠 */
.inst{background:#fff;overflow:hidden;border-top:0.5pt solid var(--ink-3);border-bottom:0.5pt solid var(--ink-3);}
.won .inst, .inst.won{border-radius:var(--r-won);}
.pill{background:#fff;border:0.8pt solid var(--ink);display:flex;align-items:baseline;gap:1mm;
  padding:0.5mm 1.4mm;line-height:1;white-space:nowrap;}
.pill.won{border-radius:3mm;} .pill.jun{border-radius:0;}
.pill .k{font-size:9pt;font-weight:700;}
.pill .t{font-size:12pt;font-weight:800;letter-spacing:-0.02em;}
.tag{background:#fff;border:1pt dashed var(--ink);font-size:var(--fs-meta);font-weight:600;line-height:1;
  padding:0.6mm 1.1mm;white-space:nowrap;}
.tag.won{border-radius:2mm;}

/* 칩 */
.chip{display:flex;flex-direction:column;justify-content:center;padding:0 1.1mm;overflow:hidden;white-space:nowrap;}
.chip.won{border-radius:var(--r-won);} .chip.jun{border-radius:var(--r-jun);}
.chip.out.won{background:var(--won);color:#fff;} .chip.out.jun{background:var(--jun);color:#fff;}
.chip.after{background:#fff;color:var(--ink);border:var(--chip-outline) solid;}
.chip.after.won{border-color:var(--won);} .chip.after.jun{border-color:var(--jun);}
.nm{font-size:var(--fs-name);font-weight:800;letter-spacing:var(--ls-name);line-height:1.08;}
.nm.s{font-size:11.5pt;}
.tm{font-size:var(--fs-time);font-weight:500;line-height:1.15;margin-top:0.4mm;}
.tm .pl{font-size:var(--fs-meta);font-weight:400;}
.chip.out .tm{color:rgba(255,255,255,.92);}
.chip.after .tm,.outlbl .tm{color:var(--ink-2);}
.outlbl{background:#fff;display:flex;flex-direction:column;justify-content:center;white-space:nowrap;}
.jbar{background:var(--ink);}
.jcap{background:var(--ink);color:#fff;font-size:10pt;font-weight:900;line-height:1.05;display:flex;flex-direction:column;
  align-items:center;justify-content:center;border-radius:0.6mm;}
.tag.big{font-size:9pt;font-weight:600;border-width:1pt;}
.together{background:var(--ink);color:#fff;font-size:8pt;font-weight:800;line-height:1;
  padding:0.7mm 1.3mm;border:0.9pt solid #fff;outline:0.9pt solid var(--ink);display:flex;align-items:center;gap:0.8mm;}
.together i{display:inline-block;width:0;height:2.6mm;border-left:0.8pt solid #fff;border-right:0.8pt solid #fff;padding-left:0.6mm;font-style:normal;}

/* 범례 */
.legend{left:8mm;right:8mm;bottom:5mm;height:9mm;display:flex;align-items:center;gap:4.2mm;
  border-top:var(--rule-day);padding-top:1.6mm;font-size:8pt;font-weight:500;color:var(--ink-2);white-space:nowrap;}
.legend .it{display:flex;align-items:center;gap:1.4mm;}
.legend .sw{width:9mm;height:4.6mm;flex:none;}
.legend .sw.inst{border-radius:0;}
.legend b{color:var(--ink);font-weight:800;}
.legend .end{margin-left:auto;color:var(--ink-3);}
"""

def head_html(title_sub, pos=("위 줄", "아래 줄")):
    kids = "".join(
        f'<div class="kidkey"><div class="badge {k[3]}">{k[2]}</div>'
        f'<div><b>{k[1]}</b> {k[4]}<br>{pos[i]} · {"둥근" if i == 0 else "각진"} 칩</div></div>'
        for i, k in enumerate(KIDS))
    return (f'<div class="abs head"><h1>우리집 주간표</h1>'
            f'<div class="sub">{title_sub}</div><div class="kids">{kids}</div></div>')

def legend_html(empty, extra=""):
    k0 = KIDS[0][3]
    items = [
        f'<div class="it"><div class="sw inst" style="position:relative">{hatch_svg(8, 4)}</div><b>학교·유치원</b></div>',
        f'<div class="it"><div class="sw chip after {k0}" style="padding:0"></div><b>방과후</b>(학교 안)</div>',
        f'<div class="it"><div class="sw chip out {k0}" style="padding:0"></div><b>학원·과외</b>(밖·집·온라인)</div>',
        f'<div class="it"><span class="tag {k0}">등교·픽업</span>데려다주기</div>',
        f'<div class="it"><span style="display:inline-block;width:3mm;height:4.6mm;background:var(--ink)"></span><b>함께</b>(검정 막대) 둘이 같이</div>',
    ]
    if extra:
        items.append(extra)
    if empty:
        items.append(f'<div class="it end">{"·".join(empty)} 일정 없음 · 끝시간 뒤 ?는 추정</div>')
    return '<div class="abs legend">' + "".join(items) + "</div>"

HATCH_PITCH, HATCH_W, HATCH_COLOR = 2.0, 0.35, "#B5B5B5"   # 선 0.35mm, 간격(수직) 2mm, 45도

def hatch_svg(w, h, pitch=HATCH_PITCH, lw=HATCH_W, color=HATCH_COLOR):
    """45도 빗금을 실제 선으로 그린 SVG(PDF에서 벡터). 영역 밖은 SVG 뷰포트가 잘라낸다."""
    step = pitch * 2 ** 0.5             # 가로 방향 간격
    lines = []
    c = -h
    while c < w + step:
        lines.append(f"M{c:.2f} {h:.2f}L{c + h:.2f} 0")
        c += step
    return (f'<svg width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}" '
            f'style="display:block;position:absolute;left:0;top:0">'
            f'<path d="{"".join(lines)}" stroke="{color}" stroke-width="{lw}" fill="none"/></svg>')

def div(cls, x, y, w, h, inner="", style=""):
    return (f'<div class="abs {cls}" style="left:{x:.2f}mm;top:{y:.2f}mm;width:{w:.2f}mm;height:{h:.2f}mm;{style}">'
            f'{inner}</div>')

def time_txt(e):
    return f'{hm(e["S"])}–{hm(e["E"])}{"?" if e.get("assumed") else ""}'

def meta_txt(e):
    bits = [b for b in (short_place(e), e["memo"]) if b]
    return " · ".join(bits)

def tm_html(time, meta):
    m = f' <span class="pl">· {esc(meta)}</span>' if meta else ""
    return f'<div class="tm">{esc(time)}{m}</div>'

# ================================================================ 레이아웃 (A4 세로, 요일 = 열)
PORTRAIT_CSS = """
@page{size:A4 portrait;margin:0;}
.page{width:210mm;height:297mm;}
.head{left:5mm;right:5mm;top:4mm;height:10.5mm;gap:4mm;padding-bottom:1.2mm;}
.head h1{font-size:18pt;}
.head .sub{font-size:8.5pt;}
.head .kids{gap:4mm;}
.kidkey{font-size:8pt;gap:1.3mm;} .kidkey b{font-size:11pt;}
.head .badge{width:5.8mm;height:5.8mm;font-size:11pt;}
.legend{left:5mm;right:5mm;height:6.6mm;padding-top:1.1mm;gap:3.6mm;font-size:7.5pt;}
.legend .sw{width:8mm;height:4mm;}
.legend .end{margin-left:auto;}
.hg{background:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;line-height:1;
  white-space:nowrap;letter-spacing:-0.02em;z-index:2;}
.hg.lite{font-weight:600;}
.fold{background:#ECECEC;display:flex;align-items:center;justify-content:center;
  font-size:7.5pt;font-weight:600;color:var(--ink-2);letter-spacing:0.02em;white-space:nowrap;}
.chip.v{justify-content:flex-start;padding:0.45mm 0.9mm;white-space:nowrap;}
.chip.v .nm{line-height:1.02;}
.chip.v .tm{margin-top:0.5mm;line-height:1.12;}
.chip.v .pl{display:block;font-size:var(--fs-meta);font-weight:400;margin-top:0.3mm;line-height:1.1;}
.chip.out .pl{color:rgba(255,255,255,.9);} .chip.after .pl{color:var(--ink-2);}
.dayhead{display:flex;align-items:flex-end;justify-content:center;font-size:22pt;font-weight:900;line-height:1;}
.badge.sm{width:5mm;height:5mm;font-size:9pt;}
.wk{border-top:var(--rule-day);}
.wk .lbl{font-size:10pt;font-weight:800;width:9mm;flex:none;}
.wk .row{display:flex;align-items:center;gap:2mm;}
.wk .d{font-size:16pt;font-weight:900;width:8mm;text-align:center;line-height:1;}
.chip.h{flex-direction:row;align-items:baseline;gap:1.6mm;padding:0 1.8mm;justify-content:flex-start;align-items:center;}
.chip.h .tm{margin-top:0;}
.wk .none{font-size:8.5pt;color:var(--ink-2);font-weight:500;}
"""

def split2(name):
    if " " in name:
        a, b = name.split(" ", 1); return [a, b]
    n = (len(name) + 1) // 2
    return [name[:n], name[n:]]

def fit_v(e, inner_w, inner_h):
    """세로 칩 내용: 14→13→12pt, 한 줄→두 줄. 12pt 아래로는 줄이지 않는다.
    반환 (fs, name_lines, time_lines, meta) 또는 None"""
    name = short_name(e)
    S, E = hm(e["S"]), hm(e["E"]) + ("?" if e.get("assumed") else "")
    TFS = 9.0
    t_h = TFS * PT * 1.12
    q = "?" if e.get("assumed") else ""
    same_h = e["S"] // 60 == e["E"] // 60
    time_opts = [[f"{S}–{E}"], [S, f"–{E}"]] + ([[f"{S}–{e['E'] % 60:02d}{q}"]] if same_h else []) + [[f"{S}~{q}"]]
    meta = meta_txt(e)
    for need_time in (True, False):
        for fs in (14, 13, 12):
            for nl in (1, 2):
                if nl == 2 and len(name) < 3:
                    continue
                lines = [name] if nl == 1 else split2(name)
                if max(tw(x, fs, 800, -0.02) for x in lines) > inner_w:
                    continue
                nh = nl * fs * PT * 1.02
                if nh > inner_h:
                    continue
                if not need_time:
                    return fs, lines, [], ""
                for tl in time_opts:
                    if max(tw(x, TFS, 500) for x in tl) > inner_w:
                        continue
                    th = 0.5 + len(tl) * t_h
                    if nh + th <= inner_h:
                        m = meta if meta and tw(meta, 7.5, 400) <= inner_w and nh + th + 3.3 <= inner_h else ""
                        return fs, lines, tl, m
    return None

def axis_info(days):
    acts = [a for d in days for l in d["lanes"] for a in l["acts"]]
    insts = [l["inst"] for d in days for l in d["lanes"] if l["inst"]]
    picks = [p for d in days for l in d["lanes"] for p in l["pick"]]
    pm = [a["S"] for a in acts if a["S"] >= 12 * 60]
    a_start = (min(pm) // 30) * 30 if pm else 12 * 60 + 30
    a_end = -(-max([a["E"] for a in acts] + [i["E"] for i in insts] + [a_start + 60]) // 15) * 15
    m_start = (min([i["S"] for i in insts] + [p["S"] for p in picks] + [a_start - 60]) // 60) * 60
    busy = sorted((max(e["S"], a_start), min(e["E"], a_end)) for e in acts + insts if e["E"] > a_start)
    cuts, cur = [], a_start
    for s0, e0 in busy:
        if s0 - cur >= 40:
            g0, g1 = -(-cur // 15) * 15, (s0 // 15) * 15
            if g1 - g0 >= 30:
                cuts.append((g0, g1))
        cur = max(cur, e0)
    vis, c = [], a_start
    for g0, g1 in cuts:
        vis.append((c, g0)); c = g1
    vis.append((c, a_end))
    return a_start, a_end, m_start, vis

def _fit(text, maxw, sizes=(11, 10.5, 10, 9.5, 9, 8.5, 8), wght=800):
    for pt in sizes:
        if tw(text, pt, wght, -0.02) <= maxw:
            return pt
    return sizes[-1]

def school_marks(k, x, y1, y2, W, word, ins, lab):
    """학교·유치원 빗금 블록의 등·하교 표시 = 위·아래 칸 너비 흰 띠(아래 띠는 굵은 끝선)."""
    t = f"{word} {hm(ins['E'])}"
    pt = _fit(t, W - 1.2)
    pt2 = min(_fit(lab, W - 1.2, wght=600), 9)
    return [div("hg", x, y2 - 6.0, W, 5.7, f"<span>{esc(t)}</span>",
                f"font-size:{pt}pt;border-top:1pt solid var(--ink);border-bottom:2pt solid var(--ink)"),
            div("hg lite", x, y1 + 0.3, W, 4.8, f"<span>{esc(lab)}</span>",
                f"font-size:{pt2}pt;border-bottom:1pt solid var(--ink)")]

def build_c(days_all, empty):
    X0, X1 = 5.0, 205.0
    RULER = 7.5
    xg0 = X0 + RULER
    weekdays = [d for d in days_all if d["day"] not in ("토", "일")]
    weekend = [d for d in days_all if d["day"] in ("토", "일")]
    wk_empty = [d for d in ("토", "일") if d in empty]
    DAY_W = (X1 - xg0) / max(len(weekdays), 1)
    DPAD, LGAP = 0.5, 0.8
    nk = len(KIDS)
    LANE_W = (DAY_W - 2 * DPAD - (nk - 1) * LGAP) / nk
    BRK = 4.6          # 접힌 구간 띠 높이
    out = []

    # ---- 주말 상자 (아래) : 높이를 먼저 정해야 세로축이 정해진다
    LEG_TOP = 297 - 4.0 - 6.6
    WK_ROW = 8.4
    wk_rows = [d for d in weekend if any(l["acts"] or l["inst"] for l in d["lanes"])]
    wk_h = 0.8 + WK_ROW * max(len(wk_rows), 1)
    wk_top = LEG_TOP - 1.0 - wk_h
    HEAD_Y = 15.0       # 요일 머리
    BADGE_Y = 23.8
    GY0 = 29.0          # 오전 띠 위
    MORN_H = 10.0
    MFOLD = 3.2         # 오전 접힘 글자 띠
    ya0 = GY0 + MORN_H + MFOLD + 0.4
    gy1 = wk_top - 1.6
    print(f"[치수] 레인 폭 {LANE_W:.1f}mm")

    a_start, a_end, m_start, vis = axis_info(weekdays)
    total = sum(b - a for a, b in vis)
    scale = (gy1 - ya0 - BRK * (len(vis) - 1)) / total
    print(f"[치수] 30분 칸 높이 {30 * scale:.1f}mm (1시간 {60 * scale:.1f}mm)")

    def Y(t):
        y = ya0
        for i, (a, b) in enumerate(vis):
            if t <= b or i == len(vis) - 1:
                return y + (max(t, a) - a) * scale
            y += (b - a) * scale + BRK
        return y

    def YM(t):
        if t >= a_start:
            return Y(t)
        return GY0 + max(0, t - m_start) / (a_start - m_start) * MORN_H

    def vspan(a, lane):
        if a["E"] <= a_start:
            morn = [o for o in lane["acts"] if o["E"] <= a_start]
            i, n = morn.index(a), len(morn)
            hh = MORN_H / n
            return GY0 + i * hh + 0.3, GY0 + (i + 1) * hh - 0.3
        return YM(a["S"]) + 0.3, Y(a["E"]) - 0.3

    # ---- 눈금 (가로선 + 왼쪽 시각)
    out.append(div("", xg0, GY0, X1 - xg0, MORN_H, style="background:#F4F4F4"))
    out.append(div("", X0, GY0, RULER - 0.8, MORN_H,
                   '<span style="font-size:7.5pt;font-weight:700">오전</span>',
                   "text-align:right;line-height:1;padding-top:3.6mm"))
    for a, b in vis:
        t = -(-a // 30) * 30
        while t <= b:
            y = Y(t)
            if t % 60 == 0:
                out.append(div("", X0 + RULER - 1.0, y, X1 - X0 - RULER + 1.0, 0,
                               style="border-top:0.5pt solid var(--grid-hour)"))
                # 접힌 띠에 붙은 시각은 띠를 피해 아래(또는 위)로
                ly = y - 2.6
                if t == a and a != vis[0][0]:
                    ly = y - 0.4
                elif t == b and b != vis[-1][1]:
                    ly = y - 4.8
                out.append(div("", X0 - 1.0, ly, RULER - 0.2, 5.2,
                               f'<span style="font-size:10pt;font-weight:800">{t // 60}</span>'
                               f'<span style="font-size:6pt;font-weight:500;color:var(--ink-2)">시</span>',
                               "text-align:right;line-height:5.2mm;letter-spacing:-0.03em"))
            else:
                out.append(div("", xg0, y, X1 - xg0, 0, style="border-top:0.35pt dotted var(--grid-half)"))
            t += 30
    if a_start % 60:
        out.append(div("", X0 - 1.0, Y(a_start) - 0.4, RULER - 0.2, 4.0,
                       f'<span style="font-size:8pt;font-weight:800;color:var(--ink)">{hm(a_start)}</span>',
                       "text-align:right;line-height:4mm;letter-spacing:-0.05em"))
    cuts = [Y(vis[i][1]) for i in range(len(vis) - 1)]

    # ---- 요일 열
    for di, d in enumerate(weekdays):
        x0 = xg0 + di * DAY_W
        if di:
            out.append(div("", x0, HEAD_Y, 0, gy1 - HEAD_Y, style="border-left:var(--rule-day)"))
        out.append(div("dayhead", x0, HEAD_Y + 0.6, DAY_W, 7.8, esc(d["day"])))
        lanes = d["lanes"]
        lx = {id(l): x0 + DPAD + i * (LANE_W + LGAP) for i, l in enumerate(lanes)}
        obst = {id(l): [] for l in lanes}
        for l in lanes:
            out.append(div("", lx[id(l)], BADGE_Y, LANE_W, 4.6,
                           f'<div class="badge sm {l["kid"][3]}">{l["kid"][2]}</div>',
                           "display:flex;justify-content:center"))
            for a in l["acts"]:
                obst[id(l)].append(vspan(a, l))
            if l["inst"]:
                obst[id(l)].append((YM(l["inst"]["S"]), Y(l["inst"]["E"])))
        for i in range(1, len(lanes)):
            xx = lx[id(lanes[i])] - LGAP / 2
            out.append(div("", xx, BADGE_Y, 0, gy1 - BADGE_Y, style="border-left:0.5pt dashed var(--ink-3)"))
        # 함께 + 픽업 (두 레인을 가로로 잇는다)
        marks = []
        for i in range(len(lanes) - 1):
            l, nl = lanes[i], lanes[i + 1]
            for a in l["acts"]:
                if not a["joint"]:
                    continue
                b = next((o for o in nl["acts"] if o["joint"] and o["S"] == a["S"]), None)
                if not b:
                    continue
                ya, yb = max(Y(a["S"]), Y(b["S"])) + 0.3, min(Y(a["E"]), Y(b["E"])) - 0.3
                xc = lx[id(nl)] - LGAP / 2          # 두 레인 경계
                BAR = 3.0
                marks.append(div("jbar", xc - BAR / 2, ya, BAR, yb - ya))
                # '함께' 세로쓰기: 칩 글자 아래(칩 아래쪽)에 둔다
                cap_w, cap_h = 4.2, 2 * 10 * PT * 1.05 + 1.6
                text_bottom = ya + 0.45 + 14 * PT * 1.02 + 0.5 + 2 * 9 * PT * 1.12 + 0.6
                cy = max(text_bottom, (text_bottom + yb - cap_h) / 2)
                if cy + cap_h <= yb:
                    marks.append(div("jcap", xc - cap_w / 2, cy, cap_w, cap_h, "함<br>께"))
                else:   # 칩이 짧으면 막대 끝 아래로
                    marks.append(div("jcap", xc - cap_w / 2, yb + 0.4, cap_w, cap_h, "함<br>께"))
                    yb += cap_h + 0.4
                end = yb
                pk = a["pickup"] or b["pickup"]
                if pk:
                    pw = tw(pk, 9, 600) + 3.0
                    marks.append(div("tag big", xc - pw / 2, yb + 0.5, pw, 5.0, esc(pk),
                                     "display:flex;align-items:center;justify-content:center"))
                    end = yb + 5.5
                a["_rw"] = BAR / 2 + 0.2 - LGAP / 2      # 막대가 칩을 덮는 폭
                b["_rw"] = BAR / 2 + 0.2 - LGAP / 2
                b["_rw_left"] = True
                for ll in (l, nl):
                    obst[id(ll)].append((yb, end + 0.6))
        for l in lanes:
            k = l["kid"][3]; x = lx[id(l)]
            ins = l["inst"]
            if ins:
                y1, y2 = YM(ins["S"]), Y(ins["E"])
                out.append(div(f"inst {k}", x, y1 + 0.3, LANE_W, y2 - y1 - 0.6, hatch_svg(LANE_W, y2 - y1 - 0.6),
                               "border-left:0.5pt solid var(--ink-3);border-right:0.5pt solid var(--ink-3)"))
                word = "하원" if "유치원" in ins["title"] else "하교"
                first = l["pick"][0] if l["pick"] else None
                lab = (f'{first["title"]} {hm(first["S"])}' if first
                       else f'{"등원" if word == "하원" else "등교"} {hm(ins["S"])}')
                out.extend(school_marks(k, x, y1, y2, LANE_W, word, ins, lab))
            for a in l["acts"]:
                y1, y2 = vspan(a, l)
                h = y2 - y1
                border = 2 * 0.56 if a["kind"] == "after" else 0
                rw = a.get("_rw", 0)
                inner_w = LANE_W - 1.8 - border - rw
                inner_h = h - 1.0 - border
                cls = f"chip v {a['kind']} {k}"
                f = fit_v(a, inner_w, inner_h)
                if f:
                    fs, lines, tl, meta = f
                    body = (f'<div class="nm" style="font-size:{fs}pt">{"<br>".join(esc(x_) for x_ in lines)}</div>'
                            + (f'<div class="tm" style="font-size:9pt">{"<br>".join(esc(x_) for x_ in tl)}</div>' if tl else "")
                            + (f'<div class="pl">{esc(meta)}</div>' if meta else ""))
                    if fs < 14 or len(lines) > 1:
                        print(f"[판단] {d['day']} {l['kid'][1]} '{short_name(a)}' {fs}pt {len(lines)}줄")
                    out.append(div(cls, x, y1, LANE_W, h, body,
                                   f"padding-left:{0.9 + rw:.2f}mm" if a.get("_rw_left") else ""))
                    continue
                # 칸이 너무 짧음 → 칩 아래/위 빈 곳에 12pt 라벨
                out.append(div(cls, x, y1, LANE_W, h))
                name = short_name(a)
                lines = [name] if tw(name, 12, 800, -0.02) <= LANE_W - 0.6 else split2(name)
                need = len(lines) * 12 * PT * 1.06 + 0.5 + 9 * PT * 1.12 + 0.8
                mine = obst[id(l)]
                nxt = min([s0 for s0, e0 in mine if s0 >= y2 - 0.01] + [gy1])
                prv = max([e0 for s0, e0 in mine if e0 <= y1 + 0.01] + [GY0])
                if nxt - (y2 + 0.6) >= need:
                    ly = y2 + 0.6
                elif (y1 - 0.6) - prv >= need:
                    ly = y1 - 0.6 - need
                else:
                    print(f"[경고] {d['day']} {l['kid'][1]} '{name}' 칸·빈 곳 모두 부족 → 12pt 잘라 씀")
                    out[-1] = div(cls, x, y1, LANE_W, h,
                                  f'<div class="nm" style="font-size:12pt">{esc(lines[0])}…</div>')
                    continue
                mine.append((ly, ly + need))
                print(f"[판단] {d['day']} {l['kid'][1]} '{name}' 칸 밖({'아래' if ly > y1 else '위'}) 라벨")
                out.append(div("outlbl", x, ly, LANE_W, need,
                               f'<div class="nm" style="font-size:12pt">{"<br>".join(esc(x_) for x_ in lines)}</div>'
                               f'<div class="tm" style="font-size:9pt">{hm(a["S"])}~</div>',
                               "justify-content:flex-start;padding-left:0.4mm"))
        out.extend(marks)
    m_from = min([l["pick"][0]["S"] for d in weekdays for l in d["lanes"] if l["pick"]]
                 + [l["inst"]["S"] for d in weekdays for l in d["lanes"] if l["inst"]] + [a_start])
    out.append(div("fold", X0, GY0 + MORN_H + 0.2, X1 - X0, MFOLD, f"↑ 오전 {hm(m_from)}~{hm(a_start)} 접음"))
    # 접힌 구간: 폭 전체 연회색 띠 + "18:15~19:00 일정 없음" (범례 없이 읽힌다)
    for i, cy in enumerate(cuts):
        g0, g1 = vis[i][1], vis[i + 1][0]
        out.append(div("fold", X0, cy + 0.3, X1 - X0, BRK - 0.6, f"{hm(g0)}~{hm(g1)} 일정 없음"))

    # ---- 주말 줄 (평일 열을 좁히지 않고 아래에). 일정 있는 요일만 한 줄씩, 빈 요일은 글로.
    avail = X1 - X0 - 9.0 - 9.0
    none_txt = f'<span class="none">{"·".join(wk_empty)} 일정 없음</span>' if wk_empty else ""
    rows_html = []
    for ri, d in enumerate(wk_rows or [None]):
        lbl = f'<div class="lbl">{"주말" if ri == 0 else ""}</div>'
        if d is None:
            rows_html.append(f'<div class="row" style="height:{WK_ROW - 0.8:.1f}mm">{lbl}{none_txt}</div>')
            continue
        items = sorted(((l["kid"], a) for l in d["lanes"] for a in l["acts"]), key=lambda t: t[1]["S"])
        for fs, show_meta in ((13, True), (13, False), (11, False), (10, False)):
            widths = []
            for kid, a in items:
                m = meta_txt(a) if show_meta else ""
                widths.append(5.8 + tw(short_name(a), fs, 800, -0.02) + 1.6 + tw(time_txt(a), 9, 500)
                              + (tw(" · " + m, 7.5, 400) if m else 0) + 3.6 + (2.6 if a["kind"] == "after" else 0))
            if sum(widths) + 2 * len(widths) <= avail - (tw(none_txt, 8.5, 500) / 2 if ri == 0 and none_txt else 0):
                break
        else:
            print(f"[경고] 주말 {d['day']} 일정이 줄 폭을 넘침")
        chips = []
        for (kid, a), w_ in zip(items, widths):
            m = meta_txt(a) if show_meta else ""
            chips.append(f'<div class="chip h {a["kind"]} {kid[3]}" style="height:7.0mm;width:{w_:.1f}mm;flex:none">'
                         f'<div class="badge sm {kid[3]}" style="width:4.2mm;height:4.2mm;font-size:8pt;border:0.6pt solid #fff">{kid[2]}</div>'
                         f'<div class="nm" style="font-size:{fs}pt">{esc(short_name(a))}</div>'
                         f'<div class="tm">{esc(time_txt(a))}' + (f' <span class="pl" style="display:inline">· {esc(m)}</span>' if m else "")
                         + '</div></div>')
        rows_html.append(f'<div class="row" style="height:{WK_ROW - 0.8:.1f}mm;margin-top:0.8mm">{lbl}<div class="d">{d["day"]}</div>'
                         + "".join(chips) + (f'<span class="none" style="margin-left:2mm">{none_txt}</span>' if ri == 0 and none_txt else "")
                         + "</div>")
    out.append(div("wk", X0, wk_top, X1 - X0, wk_h, "".join(rows_html)))

    assumed = any(a.get("assumed") for d in days_all for l in d["lanes"] for a in l["acts"])
    extra = '<div class="it end">끝시간 뒤 ?는 추정</div>' if assumed else ""
    leg = legend_html([], extra).replace('class="abs legend"', f'class="abs legend" style="top:{LEG_TOP:.1f}mm;bottom:auto"')
    body = (head_html("같은 가로선 = 같은 시각 · 매주 반복", ("왼쪽", "오른쪽")) + "".join(out) + leg)
    return body

# ---------------------------------------------------------------- 출력
def page(body, title, portrait=False):
    css = BASE_CSS + (PORTRAIT_CSS if portrait else "")
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f'<style>{css}</style></head><body><div class="page">{body}</div></body></html>')

OUT_STEM = "우리집_주간표_A4"

def render(html_path, out_dir):
    pdf = out_dir / f"{OUT_STEM}.pdf"; png = out_dir / f"{OUT_STEM}.png"
    url = html_path.as_uri()
    common = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
              "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw",
              "--virtual-time-budget=3000"]
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={pdf}", url],
                   check=True, capture_output=True)
    # A4 세로 794x1123 CSS px → 약 1131x1600 PNG
    subprocess.run(common + [f"--screenshot={png}", "--window-size=794,1123",
                             "--force-device-scale-factor=1.4248", url], check=True, capture_output=True)
    return pdf, png

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else None
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT
    _, days, empty = load(data)
    body = build_c(days, empty)
    with tempfile.TemporaryDirectory() as td:
        hp = Path(td) / "family_a4.html"
        hp.write_text(page(body, "우리집 주간표", portrait=True), encoding="utf-8")
        pdf, png = render(hp, out_dir)
    print("완료 →", pdf.name, png.name)

if __name__ == "__main__":
    main()
