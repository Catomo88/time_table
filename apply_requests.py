# -*- coding: utf-8 -*-
# requests.json 의 미처리 자연어 요청을 Gemini로 '연산'으로 변환해 반영한다.
# scope="base" -> schedule.json(기본 시간표), scope="week" -> overrides.json(이번 주 예외).
import json, os, sys, urllib.request, datetime

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KEY = os.environ.get("GEMINI_API_KEY")

def load(p, d):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d

reqs = load("requests.json", [])
pending = [r for r in reqs if not r.get("done")]
if not pending:
    print("no pending requests"); sys.exit(0)
if not KEY:
    print("GEMINI_API_KEY missing", file=sys.stderr); sys.exit(1)

sched = load("schedule.json", [])
overrides = load("overrides.json", {})
orig_count = len(sched)

today = datetime.date.today()
monday = today - datetime.timedelta(days=today.weekday())
WK = monday.isoformat()

prompt = (
"당신은 두 아이 주간 시간표 편집기입니다. '현재 기본 시간표'와 '변경 요청'을 보고 수행할 '연산 목록'(JSON 배열)만 출력하세요.\n"
"각 연산에 반드시 \"scope\" 를 넣으세요: 요청에 '이번 주/금주/this week' 같은 표현이 있으면 \"week\"(그 주만 적용), 없으면 \"base\"(매주 반복되는 기본 변경).\n"
"연산 형식:\n"
'- {"op":"add","scope":"base|week","item":{"who":"첫째|둘째","day":"월~일","s":"HH:MM","e":"HH:MM","title":..,"cat":"정규수업|방과후|학원|돌봄/픽업|기타","place":..,"assumed":false,"note":""}}\n'
'- {"op":"remove","scope":"base|week","match":{"who":..,"day":..,"title":..}}   (휴강·취소)\n'
'- {"op":"update","scope":"base|week","match":{"who":..,"day":..,"title":..},"set":{바꿀 필드만}}\n'
"규칙: 어린이집·학교수업=cat \"정규수업\", 사교육=cat \"학원\". 끝시간 불명이면 30~60분으로 잡고 assumed=true, note=\"추정\".\n"
"요청과 무관한 항목은 연산에 넣지 마세요. 출력은 JSON 배열만.\n\n"
"현재 기본 시간표:\n" + json.dumps(sched, ensure_ascii=False) + "\n\n"
"변경 요청 목록:\n" + json.dumps([p["text"] for p in pending], ensure_ascii=False)
)

body = json.dumps({"contents":[{"parts":[{"text":prompt}]}],
                   "generationConfig":{"temperature":0,"responseMimeType":"application/json"}}).encode()
url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
raw = urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"}), timeout=120).read()
text = json.loads(raw)["candidates"][0]["content"]["parts"][0]["text"].strip()
if text.startswith("```"):
    text = text.split("```")[1]; text = text[4:] if text.startswith("json") else text
ops = json.loads(text)
assert isinstance(ops, list), "ops not a list"

def match(x, m): return all(x.get(k) == v for k, v in m.items())

base_added=base_removed=base_updated=0
wk_ops=[]
log=[]
for o in ops:
    scope=o.get("scope","base")
    op=o.get("op")
    if scope=="week":
        clean={k:v for k,v in o.items() if k!="scope"}
        wk_ops.append(clean)
        log.append(f"[이번주] {op} {clean.get('match') or clean.get('item',{}).get('title','')}")
        continue
    if op=="add":
        it=dict(o["item"]); it.setdefault("place","");it.setdefault("assumed",False);it.setdefault("note","")
        for k in ("who","day","s","e","title","cat"): assert k in it,"add 필드 누락"
        sched.append(it); base_added+=1; log.append(f"+ {it['who']} {it['day']} {it['s']}-{it['e']} {it['title']}")
    elif op=="remove":
        keep=[x for x in sched if not match(x,o["match"])]; n=len(sched)-len(keep); base_removed+=n; sched=keep
        log.append(f"- 삭제 {o['match']} ({n})")
    elif op=="update":
        for x in sched:
            if match(x,o["match"]): x.update(o["set"]); base_updated+=1; log.append(f"~ {o['match']}→{o['set']}")

# 안전장치 (기본 시간표)
assert sched, "기본 시간표가 비었습니다 — 중단"
assert base_removed <= 8, f"기본 삭제 {base_removed}건은 비정상 — 중단"

# 이번 주 예외 누적 + 만료 정리
if wk_ops:
    overrides.setdefault(WK, []).extend(wk_ops)
overrides = {k:v for k,v in overrides.items() if k >= WK}   # 지난 주 자동 제거

json.dump(sched, open("schedule.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(overrides, open("overrides.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
hist=load("history.json",[])
hist.append({"time":now,"requests":[p["text"] for p in pending],
             "base":{"added":base_added,"removed":base_removed,"updated":base_updated},
             "week":{"key":WK,"ops":len(wk_ops)},"ops":ops})
json.dump(hist, open("history.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
with open("변경이력.md","a",encoding="utf-8") as f:
    f.write(f"\n### {now}\n")
    for p in pending: f.write(f"- 요청: {p['text']}\n")
    for l in log: f.write(f"  - {l}\n")

for r in reqs:
    if not r.get("done"): r["done"]=True
json.dump(reqs, open("requests.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"base +{base_added} -{base_removed} ~{base_updated}; week({WK}) ops {len(wk_ops)}; rows {orig_count}->{len(sched)}")
