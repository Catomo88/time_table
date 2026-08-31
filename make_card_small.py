# -*- coding: utf-8 -*-
"""서원 주간 시간표 → 45x72mm(세로) / 72x45mm(가로) 카드"""
import json, cairosvg
NAME="서원"; WHO="첫째"; F="Noto Sans CJK KR"
DAYS=["월","화","수","목","금","토","일"]
ACC="#3B4CB8"; INK="#23262D"; MUT="#8B8F98"
COL={"학원":"#3B4CB8","방과후":"#5D6FC9","기타":"#8D95A6"}
SHORT={"방과후 아나운서":"아나운서","방과후 큐보로봇":"큐보로봇","맞춤형 종이접기":"종이접기",
       "한글수업":"한글","영어수업":"영어","미술학원":"미술"}
S=[x for x in json.load(open("schedule.json",encoding="utf-8")) if x["who"]==WHO]
def acts(d): return sorted([x for x in S if x["day"]==d and x["cat"] not in ("정규수업","돌봄/픽업")],key=lambda r:r["s"])
def sch(d):
    v=[x for x in S if x["day"]==d and x["cat"]=="정규수업"]; return v[0] if v else None
def wid(t,size):
    return sum(size*(0.98 if ord(c)>0x1100 else 0.52) for c in t)
def nm(x): return SHORT.get(x["title"],x["title"])

def portrait(W=45.0,H=72.0,ox=0,oy=0):
    o=[f'<g transform="translate({ox},{oy})">',
       f'<rect width="{W}" height="{H}" rx="2.2" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="0.3"/>',
       f'<path d="M0 8.2 L{W} 8.2 L{W} 2.2 A2.2 2.2 0 0 0 {W-2.2} 0 L2.2 0 A2.2 2.2 0 0 0 0 2.2 Z" fill="{ACC}"/>',
       f'<text x="2.6" y="4.3" font-family="{F}" font-size="3.4" font-weight="bold" fill="#FFFFFF">{NAME} 주간 시간표</text>',
       f'<text x="2.6" y="7.1" font-family="{F}" font-size="2.2" fill="#C6CDF0">등교 08:20 · 회색=하교</text>']
    y=10.6; LH=3.02
    for i,d in enumerate(DAYS):
        it=acts(d); s=sch(d); n=max(1,len(it))
        blk=n*LH+0.9
        if i%2==0:
            o.append(f'<rect x="1.5" y="{y-2.45:.2f}" width="{W-3}" height="{blk:.2f}" rx="1" fill="#F5F6FA"/>')
        o.append(f'<text x="3.0" y="{y:.2f}" font-family="{F}" font-size="2.9" font-weight="bold" fill="{"#C0392B" if i>4 else INK}">{d}</text>')
        o.append(f'<text x="7.2" y="{y:.2f}" font-family="{F}" font-size="2.2" fill="{MUT}">{s["e"] if s else "—"}</text>')
        if it:
            for k,x in enumerate(it):
                ly=y+k*LH
                o.append(f'<circle cx="14.4" cy="{ly-0.85:.2f}" r="0.7" fill="{COL.get(x["cat"],COL["기타"])}"/>')
                o.append(f'<text x="15.8" y="{ly:.2f}" font-family="{F}" font-size="2.35" font-weight="bold" fill="{INK}">{x["s"]}</text>')
                o.append(f'<text x="23.2" y="{ly:.2f}" font-family="{F}" font-size="2.45" fill="#3A3F49">{nm(x)}</text>')
        else:
            o.append(f'<text x="15.8" y="{y:.2f}" font-family="{F}" font-size="2.3" fill="#C3C6CD">일정 없음</text>')
        y+=blk+0.28
    o.append("</g>")
    return "".join(o)

def landscape(W=72.0,H=45.0,ox=0,oy=0):
    o=[f'<g transform="translate({ox},{oy})">',
       f'<rect width="{W}" height="{H}" rx="2.2" fill="#FFFFFF" stroke="#D6D9E0" stroke-width="0.3"/>',
       f'<path d="M0 6.6 L{W} 6.6 L{W} 2.2 A2.2 2.2 0 0 0 {W-2.2} 0 L2.2 0 A2.2 2.2 0 0 0 0 2.2 Z" fill="{ACC}"/>',
       f'<text x="2.6" y="4.6" font-family="{F}" font-size="3.2" font-weight="bold" fill="#FFFFFF">{NAME} 주간 시간표</text>',
       f'<text x="{W-2.6}" y="4.5" font-family="{F}" font-size="2.2" font-weight="bold" fill="#E4E9FB" text-anchor="end">등교 08:20</text>']
    top=8.2; rowh=5.15
    for i,d in enumerate(DAYS):
        y=top+i*rowh
        if i%2==0:
            o.append(f'<rect x="1.5" y="{y-0.2:.2f}" width="{W-3}" height="{rowh-0.45:.2f}" rx="0.9" fill="#F5F6FA"/>')
        o.append(f'<text x="2.9" y="{y+3.3:.2f}" font-family="{F}" font-size="3.0" font-weight="bold" fill="{"#C0392B" if i>4 else INK}">{d}</text>')
        s=sch(d)
        o.append(f'<text x="6.4" y="{y+3.3:.2f}" font-family="{F}" font-size="2.2" font-weight="bold" fill="#5A5F68">{s["e"] if s else "—"}</text>')
        x=17.0
        for it in acts(d):
            label=nm(it); c=COL.get(it["cat"],COL["기타"])
            pl=it["place"] if (it.get("place") and it["cat"]=="방과후") else ""
            sub=it["s"]+((" "+pl) if pl else "")
            bw=max(wid(label,2.35),(wid(it["s"],1.9)+(wid(pl,2.0)+1.4 if pl else 0))*1.2)+2.4
            if x+bw>W-2.4: break
            o.append(f'<rect x="{x:.2f}" y="{y+0.25:.2f}" width="{bw:.2f}" height="4.4" rx="0.8" fill="{c}"/>')
            o.append(f'<text x="{x+bw/2:.2f}" y="{y+2.25:.2f}" font-family="{F}" font-size="2.35" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{label}</text>')
            o.append(f'<text x="{x+bw/2:.2f}" y="{y+4.3:.2f}" font-family="{F}" font-size="1.9" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{it["s"]}<tspan dx="0.7" fill="#FFD966" font-weight="bold">{pl}</tspan></text>')
            x+=bw+0.8
        if not acts(d):
            o.append(f'<text x="17.0" y="{y+3.3:.2f}" font-family="{F}" font-size="2.2" fill="#C3C6CD">일정 없음</text>')
    o.append("</g>")
    return "".join(o)

def out(name,W,H,body):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">{body}</svg>'
    cairosvg.svg2pdf(bytestring=svg.encode(),write_to=f"{name}.pdf")
    cairosvg.svg2png(bytestring=svg.encode(),write_to=f"{name}.png",dpi=300,
                     output_width=int(W/25.4*300),output_height=int(H/25.4*300))

def sheet(name,W,H,fn,cols,rows):
    AW,AH=210,297; gx,gy=6,5
    tw=cols*W+(cols-1)*gx; th=rows*H+(rows-1)*gy
    sx=(AW-tw)/2; sy=(AH-th)/2
    p=[]
    for r in range(rows):
        for c in range(cols):
            x=sx+c*(W+gx); y=sy+r*(H+gy)
            p.append(fn(W,H,x,y))
            p.append(f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="2.2" fill="none" stroke="#C9CCD2" stroke-width="0.15" stroke-dasharray="1,1.5"/>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">{"".join(p)}</svg>'
    cairosvg.svg2pdf(bytestring=svg.encode(),write_to=f"{name}.pdf")

out("서원_카드_72x45",72,45,landscape())
sheet("서원_카드_A4인쇄",72,45,landscape,2,5)
print("완료")
