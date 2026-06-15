# -*- coding: utf-8 -*-
# requests.json 의 미처리 자연어 요청을 Gemini로 분석해 schedule.json 에 반영한다.
import json, os, sys, urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KEY = os.environ.get("GEMINI_API_KEY")

def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default

reqs = load("requests.json", [])
pending = [r for r in reqs if not r.get("done")]
if not pending:
    print("no pending requests"); sys.exit(0)
if not KEY:
    print("GEMINI_API_KEY missing", file=sys.stderr); sys.exit(1)

sched = load("schedule.json", [])

prompt = (
"당신은 두 아이의 주간 시간표 편집기입니다. 아래 '현재 시간표'(JSON 배열)에 '변경 요청'(한국어)을 반영하여, "
"반영된 전체 시간표 JSON 배열만 출력하세요.\n"
"각 항목 필드: who(\"첫째\"|\"둘째\"), day(\"월\"|\"화\"|\"수\"|\"목\"|\"금\"|\"토\"|\"일\"), "
"s(\"HH:MM\"), e(\"HH:MM\"), title(문자열), cat(\"정규수업\"|\"방과후\"|\"학원\"|\"돌봄/픽업\"|\"기타\"), "
"place(문자열), assumed(true/false), note(문자열).\n"
"규칙:\n"
"- 어린이집·학교 정규수업은 cat \"정규수업\". 태권도·피아노·미술·영어·수영·첼로·한글 등 사교육은 \"학원\".\n"
"- 끝나는 시간이 명시되지 않으면 30~60분으로 합리적으로 정하고 assumed=true, note에 \"추정\"을 넣으세요.\n"
"- 추가/변경/취소(삭제)를 정확히 반영하고, 관련 없는 기존 항목은 그대로 유지하세요.\n"
"- 출력은 JSON 배열만. 마크다운/설명/주석 없이.\n\n"
"현재 시간표:\n" + json.dumps(sched, ensure_ascii=False) + "\n\n"
"변경 요청 목록:\n" + json.dumps([p["text"] for p in pending], ensure_ascii=False)
)

body = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}
}).encode()

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
raw = urllib.request.urlopen(req, timeout=120).read()
out = json.loads(raw)
text = out["candidates"][0]["content"]["parts"][0]["text"].strip()
if text.startswith("```"):
    text = text.split("```")[1]
    text = text[4:] if text.startswith("json") else text
new = json.loads(text)

assert isinstance(new, list) and len(new) >= 1, "result not a non-empty list"
for x in new:
    assert all(k in x for k in ("who", "day", "s", "e", "title", "cat")), "missing fields"
    x.setdefault("place", ""); x.setdefault("assumed", False); x.setdefault("note", "")

json.dump(new, open("schedule.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in reqs:
    if not r.get("done"):
        r["done"] = True
json.dump(reqs, open("requests.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"applied {len(pending)} request(s); schedule now {len(new)} rows")
