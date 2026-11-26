# -*- coding: utf-8 -*-
"""서원 주간 카드 72x45mm (가방용) — schedule.json → PDF/PNG

    python make_card_small.py
    → 서원_카드_72x45.pdf / .png (300dpi), 서원_카드_A4인쇄.pdf (A4 세로 2열x5행, 재단선)

우리집 주간표(make_family_a4.py)와 같은 규칙:
  요일 행 x 시간순 칩(시간 비례 없음). 방과후(학교 안)=테두리 칩, 학원·과외(밖·집·온라인)=꽉 찬 칩,
  서원 색 #8E3A8A, 서원 칩은 둥근 모서리. 학교는 요일 옆 빗금 꼬리표 '하교 13:30'.
  이름 줄임·데이터 읽기는 make_family_a4.py의 함수를 그대로 쓴다.
글자 하한: 수업명 8pt, 시간 6.5pt, 칩 위아래 여백 0.5mm. 칩이 줄을 넘치면 버리지 않고 '+N'.
"""
import sys, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from make_family_a4 import load, short_name, hm, tw, esc, hatch_svg, CHROME, PT  # 같은 규칙(빗금 SVG 포함)

WHO = "첫째"
W, H = 72.0, 45.0
PAD_X, PAD_T, PAD_B = 1.6, 0.8, 0.7
HEAD_H = 3.4
FS_NAME, FS_TIME = 8.0, 6.5          # 하한 (크리틱 요구)
CHIP_PAD_Y, CHIP_PAD_X, CHIP_GAP = 0.5, 0.75, 0.7
ROW_GAP = 0.15
DAY_COL = 13.4

CSS = """
@font-face{font-family:"NotoKR";src:local("Noto Sans KR"),url("file:///C:/Windows/Fonts/NotoSansKR-VF.ttf") format("truetype");font-weight:100 900;}
:root{--ink:#111;--ink-2:#3A3A3A;--ink-3:#8A8A8A;--won:#9C4C98;
  --font:"NotoKR","Noto Sans KR","Malgun Gothic",sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
html,body{background:#fff;}
body{font-family:var(--font);color:var(--ink);font-variant-numeric:tabular-nums;}
.card{position:absolute;width:72mm;height:45mm;background:#fff;overflow:hidden;}
.card.single{border:0.3pt solid #C8C8C8;border-radius:2.2mm;}
.hd{position:absolute;left:1.6mm;right:1.6mm;top:0.8mm;height:3.4mm;display:flex;align-items:center;gap:1.2mm;
  border-bottom:0.6pt solid var(--ink);padding-bottom:0.3mm;white-space:nowrap;}
.hd .bd{width:3.4mm;height:3.4mm;border-radius:50%;background:var(--won);color:#fff;font-size:6.5pt;font-weight:900;
  display:flex;align-items:center;justify-content:center;line-height:1;}
.hd .t{font-size:8pt;font-weight:800;letter-spacing:-0.02em;line-height:1;}
.hd .r{margin-left:auto;display:flex;align-items:center;gap:1.3mm;font-size:6.5pt;font-weight:500;color:var(--ink-2);line-height:1;}
.hd .sw{display:inline-block;width:2.6mm;height:2mm;border-radius:0.6mm;vertical-align:-0.2mm;margin-right:0.5mm;}
.hd .sw.after{border:0.8pt solid var(--won);background:#fff;} .hd .sw.out{background:var(--won);}
.row{position:absolute;left:1.6mm;right:1.6mm;display:flex;align-items:stretch;}
.day{width:4.2mm;flex:none;font-size:9.5pt;font-weight:900;line-height:1;display:flex;align-items:center;}
.day.wk{font-size:8pt;width:13.4mm;letter-spacing:-0.04em;}
.sch{flex:none;width:8.6mm;margin-right:0.6mm;display:flex;align-items:stretch;border-top:0.6pt solid var(--ink);border-bottom:1.4pt solid var(--ink);overflow:hidden;}
.sch .hx{width:1.5mm;flex:none;position:relative;overflow:hidden;border-right:0.4pt solid var(--ink-3);border-left:0.4pt solid var(--ink-3);}
.sch .tx{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;line-height:1;}
.sch .k{font-size:6.5pt;font-weight:500;color:var(--ink-2);}
.sch .v{font-size:6.5pt;font-weight:800;margin-top:0.25mm;letter-spacing:-0.02em;}
.chips{display:flex;gap:0.7mm;align-items:stretch;min-width:0;}
.chip{flex:none;display:flex;flex-direction:column;justify-content:center;padding:0.5mm 0.75mm;border-radius:1.2mm;white-space:nowrap;}
.chip.out{background:var(--won);color:#fff;}
.chip.after{background:#fff;border:0.8pt solid var(--won);}
.chip .n{font-size:8pt;font-weight:800;letter-spacing:-0.02em;line-height:1;}
.chip .m{font-size:6.5pt;font-weight:500;line-height:1;margin-top:0.2mm;}
.chip.out .m{color:#fff;}
.chip.after .m{color:var(--ink);}
.chip .m .p{font-weight:700;}
.more{flex:none;display:flex;align-items:center;justify-content:center;padding:0 0.8mm;border:0.8pt dashed var(--ink);
  border-radius:1.2mm;font-size:8pt;font-weight:900;}
.none{font-size:6.5pt;color:var(--ink-2);font-weight:500;display:flex;align-items:center;white-space:nowrap;}
"""

_WARNED = set()

def chip_w(a, place):
    nm = tw(short_name(a), FS_NAME, 800, -0.02)
    mt = tw(hm(a["S"]) + (" " + place if place else ""), FS_TIME, 700 if place else 500)
    return max(nm, mt) + 2 * CHIP_PAD_X + (2 * 0.28 if a["kind"] == "after" else 0) + 0.3

def chips_html(items, avail, prefix=None):
    """items: [(event, place)] → 넘치면 뒤에서부터 빼고 '+N'"""
    ws = [chip_w(a, p) + (tw((prefix(a) or "") + " ", FS_TIME, 500) if prefix else 0) for a, p in items]
    n = len(items)
    more_w = tw("+9", 8, 900) + 2.2
    def fits(k):
        tot = sum(ws[:k]) + CHIP_GAP * max(k - 1, 0)
        return tot + ((CHIP_GAP + more_w) if k < n else 0) <= avail
    k = n
    while k > 0 and not fits(k):
        k -= 1
    out = []
    for (a, p), w in zip(items[:k], ws[:k]):
        pre = (prefix(a) + " ") if prefix else ""
        pl = f' <span class="p">{esc(p)}</span>' if p else ""
        out.append(f'<div class="chip {a["kind"]}" style="width:{w:.2f}mm">'
                   f'<div class="n">{esc(short_name(a))}</div><div class="m">{esc(pre)}{hm(a["S"])}{pl}</div></div>')
    if k < n:
        out.append(f'<div class="more">+{n - k}</div>')
        msg = f"[알림] 칩 {n - k}개가 칸을 넘쳐 '+{n - k}'로 표시: " + ", ".join(short_name(a) for a, _ in items[k:])
        if msg not in _WARNED:
            _WARNED.add(msg); print(msg)
    return "".join(out)

def card_html(days, empty, x=0.0, y=0.0, single=True):
    by_day = {d["day"]: next((l for l in d["lanes"] if l["kid"][0] == WHO), None) for d in days}
    weekdays = ["월", "화", "수", "목", "금"]
    picks = [p for l in by_day.values() if l for p in l["pick"]]
    go = f'등교 {hm(min(p["S"] for p in picks))}' if picks else ""
    o = [f'<div class="card{" single" if single else ""}" style="left:{x:.2f}mm;top:{y:.2f}mm">',
         '<div class="hd"><div class="bd">원</div><div class="t">서원 주간표</div>'
         f'<div class="r"><span>{go}</span><span><i class="sw after"></i>방과후</span>'
         '<span><i class="sw out"></i>학원·과외</span></div></div>']
    rows = 6
    top = PAD_T + HEAD_H + 0.4
    rh = (H - top - PAD_B - ROW_GAP * (rows - 1)) / rows
    chip_area = W - 2 * PAD_X - DAY_COL
    for i, dname in enumerate(weekdays):
        ry = top + i * (rh + ROW_GAP)
        l = by_day.get(dname)
        cells = [f'<div class="day">{dname}</div>']
        if l and l["inst"]:
            word = "하원" if "유치원" in l["inst"]["title"] else "하교"
            cells.append(f'<div class="sch"><div class="hx">{hatch_svg(1.5, rh)}</div><div class="tx"><span class="k">{word}</span>'
                         f'<span class="v">{hm(l["inst"]["E"])}</span></div></div>')
        else:
            cells.append('<div style="width:9.2mm;flex:none"></div>')
        acts = l["acts"] if l else []
        if acts:
            items = [(a, (a.get("place", "") or "") if a["kind"] == "after" else "") for a in acts]
            cells.append(f'<div class="chips">{chips_html(items, chip_area)}</div>')
        else:
            cells.append('<div class="none">끝나고 일정 없음</div>')
        o.append(f'<div class="row" style="top:{ry:.2f}mm;height:{rh:.2f}mm">{"".join(cells)}</div>')
    # 주말 한 줄
    ry = top + 5 * (rh + ROW_GAP)
    wk_items = []
    for dname in ("토", "일"):
        l = by_day.get(dname)
        for a in (l["acts"] if l else []):
            wk_items.append((a, ""))
    wk_empty = [d for d in ("토", "일") if not (by_day.get(d) and by_day[d]["acts"])]
    label = '<div class="day wk">토·일</div>'
    lab_w = DAY_COL
    none = f'<div class="none" style="margin-left:1mm">{"·".join(wk_empty)} 없음</div>' if wk_empty and wk_items else ""
    if wk_items:
        none_w = tw(f'{"·".join(wk_empty)} 없음', FS_TIME, 500) + 1.2 if none else 0
        body = chips_html(wk_items, W - 2 * PAD_X - lab_w - none_w, prefix=lambda a: a["day"])
    else:
        body = '<div class="none">일정 없음</div>'
    o.append(f'<div class="row" style="top:{ry:.2f}mm;height:{rh:.2f}mm">{label}<div class="chips">{body}</div>{none}</div>')
    o.append("</div>")
    return "".join(o), rh

def page(body, size):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>서원 카드</title>'
            f'<style>@page{{size:{size};margin:0;}}{CSS}</style></head><body>'
            f'<div style="position:relative">{body}</div></body></html>')

def sheet(days, empty, cols=2, rows=5):
    AW, AH = 210.0, 297.0
    gx, gy = 6.0, 5.0
    tw_ = cols * W + (cols - 1) * gx
    th = rows * H + (rows - 1) * gy
    sx, sy = (AW - tw_) / 2, (AH - th) / 2
    parts = []
    for r in range(rows):
        for c in range(cols):
            x, y = sx + c * (W + gx), sy + r * (H + gy)
            parts.append(card_html(days, empty, x, y, single=False)[0])
            parts.append(f'<div style="position:absolute;left:{x:.2f}mm;top:{y:.2f}mm;width:{W}mm;height:{H}mm;'
                         f'border:0.3pt dashed #A0A0A0;border-radius:2.2mm"></div>')
            # 모서리 재단 표시 (카드 밖 2mm)
            for cx, cy in ((x, y), (x + W, y), (x, y + H), (x + W, y + H)):
                dx = -1 if cx == x else 1
                dy = -1 if cy == y else 1
                parts.append(f'<div style="position:absolute;left:{min(cx, cx + dx * 2.2):.2f}mm;top:{cy:.2f}mm;width:2.2mm;height:0;'
                             f'border-top:0.3pt solid #555"></div>')
                parts.append(f'<div style="position:absolute;left:{cx:.2f}mm;top:{min(cy, cy + dy * 2.2):.2f}mm;width:0;height:2.2mm;'
                             f'border-left:0.3pt solid #555"></div>')
    parts.append(f'<div style="position:absolute;left:{sx + 3:.2f}mm;top:{sy - 4.2:.2f}mm;font-size:7pt;color:#666">'
                 f'점선을 따라 자르세요 · 72x45mm (모서리 둥글게 2.2mm)</div>')
    return "".join(parts)

def chrome(args):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=3000"] + args, check=True, capture_output=True)

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else None
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT
    _, days, empty = load(data)
    card, rh = card_html(days, empty)
    need = FS_NAME * PT + 0.2 + FS_TIME * PT + 2 * CHIP_PAD_Y
    print(f"[치수] 줄 높이 {rh:.2f}mm, 칩에 필요한 높이 {need:.2f}mm(위아래 여백 {CHIP_PAD_Y}mm 포함)")
    if need > rh + 0.01:
        print("[경고] 줄 높이가 칩 하한보다 작음")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        h1 = td / "card.html"; h1.write_text(page(card, "72mm 45mm"), encoding="utf-8")
        h2 = td / "sheet.html"; h2.write_text(page(sheet(days, empty), "A4 portrait"), encoding="utf-8")
        chrome(["--no-pdf-header-footer", f"--print-to-pdf={out_dir / '서원_카드_72x45.pdf'}", h1.as_uri()])
        # 72x45mm = 272x170 CSS px → x3.125 = 850x531 (300dpi)
        chrome([f"--screenshot={out_dir / '서원_카드_72x45.png'}", "--window-size=272,170",
                "--force-device-scale-factor=3.125", h1.as_uri()])
        chrome(["--no-pdf-header-footer", f"--print-to-pdf={out_dir / '서원_카드_A4인쇄.pdf'}", h2.as_uri()])
    print("완료 → 서원_카드_72x45.pdf/.png, 서원_카드_A4인쇄.pdf")

if __name__ == "__main__":
    main()
