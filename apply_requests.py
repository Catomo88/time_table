# -*- coding: utf-8 -*-
# requests.json 의 미처리 자연어 요청을 Gemini로 '연산(추가/삭제/변경)'으로 변환해
# schedule.json 에 안전하게 반영한다. 관련 없는 항목은 절대 건드리지 않는다.
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
orig_count = len(sched)

prompt = (
"당신은 두 아이 주간 시간표 편집기입니다. '현재 시간표'와 '변경 요청'을 보고, "
"수행할 '연산 목록'(JSON 배열)만 출력하세요. 전체 시간표를 다시 쓰지 말고, 바꿀 부분만 연산으로 표현하세요.\n"
"연산 형식 (op 별):\n"
'- 추가: {"op":"add","item":{"who":..,"day":..,"s":"HH:MM","e":"HH:MM","title":..,"cat":..,"place":..,"assumed":false,"note":""}}\n'
'- 삭제: {"op":"remove","match":{"who":..,"day":..,"title":..}}  (필요시 "s"도 포함해 특정)\n'
'- 변경: {"op":"update","match":{"who":..,"day":..,"title":..},"set":{바꿀 필드만}}\n'
"필드 규칙: who=\"첫째\"|\"둘째\"; day=\"월\"~\"일\"; cat=\"정규수업\"|\"방과후\"|\"학원\"|\"돌봄/픽업\"|\"기타\" "
"(어린이집·학교수업=\"정규수업\", 사교육=\"학원\"); 끝시간 불명이면 30~60분으로 잡고 assumed=true, note=\"추정\".\n"
"요청과 무관한 항목은 연산에 넣지 마세요. 출력은 JSON 배열만(마크다운/설명 금지).\n\n"
"현재 시간표:\n" + json.dumps(sched, ensure_ascii=False) + "\n\n"
"변경 요청 목록:\n" + json.dumps([p["text"] for p in pending], ensure_ascii=False)
)

body = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}
}).encode()
url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
raw = urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=120).read()
text = json.loads(raw)["candidates"][0]["content"]["parts"][0]["text"].strip()
if text.startswith("```"):
    text = text.split("```")[1]; text = text[4:] if text.startswith("json") else text
ops = json.loads(text)
assert isinstance(ops, list), "ops not a list"

def match(x, m):
    return all(x.get(k) == v for k, v in m.items())

added = removed = updated = 0
log_lines = []
for o in ops:
    op = o.get("op")
    if op == "add":
        it = dict(o["item"]); it.setdefault("place", ""); it.setdefault("assumed", False); it.setdefault("note", "")
        for k in ("who", "day", "s", "e", "title", "cat"):
            assert k in it, "add 항목 필드 누락"
        sched.append(it); added += 1
        log_lines.append(f"+ 추가 {it['who']} {it['day']} {it['s']}-{it['e']} {it['title']}")
    elif op == "remove":
        keep = [x for x in sched if not match(x, o["match"])]
        n = len(sched) - len(keep); removed += n; sched = keep
        log_lines.append(f"- 삭제 {o['match']} ({n}건)")
    elif op == "update":
        for x in sched:
            if match(x, o["match"]):
                x.update(o["set"]); updated += 1
                log_lines.append(f"~ 변경 {o['match']} → {o['set']}")

# ---- 안전장치 ----
assert sched, "결과 시간표가 비었습니다 — 중단"
assert removed <= 8, f"한 번에 삭제 {removed}건은 비정상으로 판단 — 중단"

json.dump(sched, open("schedule.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- 변경이력 ----
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
hist = load("history.json", [])
hist.append({"time": now, "requests": [p["text"] for p in pending],
             "added": added, "removed": removed, "updated": updated,
             "rows_before": orig_count, "rows_after": len(sched), "ops": ops})
json.dump(hist, open("history.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open("변경이력.md", "a", encoding="utf-8") as f:
    f.write(f"\n### {now}  (행 {orig_count}→{len(sched)})\n")
    for p in pending:
        f.write(f"- 요청: {p['text']}\n")
    for l in log_lines:
        f.write(f"  - {l}\n")

for r in reqs:
    if not r.get("done"):
        r["done"] = True
json.dump(reqs, open("requests.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"ops applied: +{added} -{removed} ~{updated}; rows {orig_count}->{len(sched)}")
