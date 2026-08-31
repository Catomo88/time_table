# -*- coding: utf-8 -*-
"""서원 주간 시간표 → 신용카드 크기(85.6x54mm) 카드. SVG로 그려 PDF/PNG로 변환."""
import json, cairosvg

W,H=85.6,54.0
NAME="서원"; WHO="첫째"
DAYS=["월","화","수","목","금","토","일"]
F="Noto Sans CJK KR"
ACC="#3B4CB8"; INK="#23262D"; MUT="#8B8F98"
COL={"학원":"#3B4CB8","방과후":"#7C8BD9","기타":"#A9B0BF"}
SHORT={"방과후 아나운서":"아나운서","방과후 큐보로봇":"큐보로봇","맞춤형 종이접기":"종이접기",
       "한글수업":"한글","영어수업":"영어","화상영어":"화상영어","미술학원":"미술"}

S=[x for x in json.load(open("schedule.json",encoding="utf-8")) if x["who"]==WHO]
def acts(d): return sorted([x for x in S if x["day"]==d and x["cat"] not in ("정규수업","돌봄/픽업")],key=lambda r:r["s"])
def school(d):
    s=[x for x in S if x["day"]==d and x["cat"]=="정규수업"]
    return s[0] if s else None
def wid(t,size):  # 한글 폭 근사
    w=0
    for ch in t: w += size*(0.98 if ord(ch)>0x1100 else 0.52)
    return w

def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def card(ox=0,oy=0):
    o=[f'<g transform="translate({ox},{oy})">']
    o.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="2.6" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="0.3"/>')
    o.append(f'<path d="M0 7.6 L{W} 7.6 L{W} 2.6 A2.6 2.6 0 0 0 {W-2.6} 0 L2.6 0 A2.6 2.6 0 0 0 0 2.6 Z" fill="{ACC}"/>')
    o.append(f'<text x="3.2" y="5.3" font-family="{F}" font-size="4.5" font-weight="bold" fill="#FFFFFF">{NAME} 주간 시간표</text>')
    o.append(f'<text x="{W-3.2}" y="5.2" font-family="{F}" font-size="2.9" fill="#CBD2F2" text-anchor="end">등교 08:20 · 숫자=하교</text>')
    top=9.4; rowh=6.25
    for i,d in enumerate(DAYS):
        y=top+i*rowh
        if i%2==0:
            o.append(f'<rect x="1.6" y="{y-0.2:.2f}" width="{W-3.2}" height="{rowh-0.5:.2f}" rx="1" fill="#F5F6FA"/>')
        dcol="#C0392B" if i>4 else INK
        o.append(f'<text x="3.4" y="{y+3.9:.2f}" font-family="{F}" font-size="3.8" font-weight="bold" fill="{dcol}">{d}</text>')
        sc=school(d)
        o.append(f'<text x="7.2" y="{y+3.9:.2f}" font-family="{F}" font-size="2.5" fill="{MUT}">{sc["e"] if sc else "—"}</text>')
        x=21.5
        for it in acts(d):
            nm=SHORT.get(it["title"],it["title"])
            c=COL.get(it["cat"],COL["기타"])
            bw=max(wid(nm,2.75),wid(it["s"],2.3))+2.0
            if x+bw>W-3.0: break
            o.append(f'<rect x="{x:.2f}" y="{y+0.25:.2f}" width="{bw:.2f}" height="5.15" rx="0.9" fill="{c}"/>')
            o.append(f'<text x="{x+bw/2:.2f}" y="{y+2.55:.2f}" font-family="{F}" font-size="2.75" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{esc(nm)}</text>')
            o.append(f'<text x="{x+bw/2:.2f}" y="{y+4.9:.2f}" font-family="{F}" font-size="2.3" fill="#DDE3F8" text-anchor="middle">{it["s"]}</text>')
            x+=bw+0.9
        if not acts(d):
            o.append(f'<text x="21.5" y="{y+3.9:.2f}" font-family="{F}" font-size="2.5" fill="#C3C6CD">일정 없음</text>')
    o.append("</g>")
    return "".join(o)

svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">{card()}</svg>'
open("서원_카드.svg","w",encoding="utf-8").write(svg)
cairosvg.svg2pdf(bytestring=svg.encode(),write_to="서원_카드.pdf")
cairosvg.svg2png(bytestring=svg.encode(),write_to="서원_카드.png",dpi=300,output_width=int(W/25.4*300),output_height=int(H/25.4*300))

# A4 인쇄용 (10장)
AW,AH=210,297; cols,rows=2,5; gx,gy=6,4
tw=cols*W+(cols-1)*gx; th=rows*H+(rows-1)*gy
sx=(AW-tw)/2; sy=(AH-th)/2
parts=[]
for r in range(rows):
    for c2 in range(cols):
        x=sx+c2*(W+gx); y=sy+r*(H+gy)
        parts.append(card(x,y))
        parts.append(f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="2.6" fill="none" stroke="#C9CCD2" stroke-width="0.15" stroke-dasharray="1,1.5"/>')
sheet=f'<svg xmlns="http://www.w3.org/2000/svg" width="{AW}mm" height="{AH}mm" viewBox="0 0 {AW} {AH}">{"".join(parts)}</svg>'
cairosvg.svg2pdf(bytestring=sheet.encode(),write_to="서원_카드_A4인쇄.pdf")
print("saved: 서원_카드.pdf / .png / 서원_카드_A4인쇄.pdf")
