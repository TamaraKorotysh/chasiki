# Сопоставляет распознанные слова (words.json) с фразами сценария (phrases.json)
# и находит точки разреза в паузах. Пишет cuts.json и отчёт report.txt.
import json, re, sys, difflib

PH = r"E:\chasiki\voice\phrases.json"
W = r"E:\Claude-temp\chasiki\words.json"
SIL = r"E:\Claude-temp\chasiki\sil_02.txt"
OUT = r"E:\Claude-temp\chasiki\cuts.json"
REP = r"E:\Claude-temp\chasiki\report.txt"

ONES = "ноль один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать тринадцать четырнадцать пятнадцать шестнадцать семнадцать восемнадцать девятнадцать".split()
TENS = {2: "двадцать", 3: "тридцать", 4: "сорок", 5: "пятьдесят", 6: "шестьдесят", 7: "семьдесят", 8: "восемьдесят", 9: "девяносто"}
def n2w(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 200: return "сто" + ("" if n == 100 else " " + n2w(n - 100))
    return str(n)

def norm_words(s):
    s = re.sub(r"\[[^\]]*\]", " ", s).lower().replace("ё", "е")
    # время 12:30 -> двенадцать тридцать
    s = re.sub(r"(\d{1,2}):(\d\d)", lambda m: n2w(int(m.group(1))) + " " + ("ноль ноль" if m.group(2) == "00" else n2w(int(m.group(2)))), s)
    s = re.sub(r"\d+", lambda m: " " + n2w(int(m.group(0))) + " ", s)
    s = re.sub(r"[^а-яa-z]+", " ", s)
    return s.split()

key = lambda w: w[:4]

blocks = json.load(open(PH, encoding="utf-8"))
phr = []
for b in blocks:
    for it in b["items"]:
        phr.append({"id": it["id"], "text": it["text"], "file": b["file"]})
exp, owner = [], []
for i, p in enumerate(phr):
    ws = norm_words(p["text"])
    p["nw"] = len(ws)
    for w in ws:
        exp.append(w); owner.append(i)

words = json.load(open(W, encoding="utf-8"))
rec, rt = [], []
for st, en, w in words:
    ws = norm_words(w)
    for k, x in enumerate(ws):
        # раскладываем время слова равномерно, если из одного «слова» получилось несколько
        a = st + (en - st) * k / len(ws); b2 = st + (en - st) * (k + 1) / len(ws)
        rec.append(x); rt.append((a, b2))

sm = difflib.SequenceMatcher(None, [key(x) for x in exp], [key(x) for x in rec], autojunk=False)
match = [None] * len(exp)
for a, b, n in sm.get_matching_blocks():
    for k in range(n): match[a + k] = b + k

# время каждой фразы по совпавшим словам
for p in phr: p["m"] = []
for ei, ri in enumerate(match):
    if ri is not None: phr[owner[ei]]["m"].append(ri)

sil = []
txt = open(SIL, encoding="utf-8", errors="ignore").read()
for s, e in zip(re.findall(r"silence_start: ([\d.]+)", txt), re.findall(r"silence_end: ([\d.]+)", txt)):
    sil.append((float(s), float(e)))

N = len(phr)
for p in phr:
    if p["m"]:
        p["t0"] = rt[min(p["m"])][0]; p["t1"] = rt[max(p["m"])][1]
    else:
        p["t0"] = p["t1"] = None
# заполняем пропуски интерполяцией
known = [i for i in range(N) if phr[i]["t0"] is not None]
for i in range(N):
    if phr[i]["t0"] is None:
        prev = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
        a = phr[prev]["t1"] if prev is not None else 0
        b = phr[nxt]["t0"] if nxt is not None else words[-1][1]
        phr[i]["t0"] = phr[i]["t1"] = (a + b) / 2
        phr[i]["guess"] = True

cuts = []
for i in range(N - 1):
    e, s = phr[i]["t1"], phr[i + 1]["t0"]
    lo, hi = min(e, s) - 0.35, max(e, s) + 0.35
    cand = [(min(se, hi) - max(ss, lo), ss, se) for ss, se in sil if se > lo and ss < hi]
    if cand:
        _, ss, se = max(cand, key=lambda c: c[2] - c[1])
        cuts.append(((ss + se) / 2, ss, se))
    else:
        m = (e + s) / 2; cuts.append((m, m, m))

dur = words[-1][1] + 2
segs = []
for i in range(N):
    c0 = cuts[i - 1] if i > 0 else (0, 0, 0)
    c1 = cuts[i] if i < N - 1 else (dur, dur, dur)
    a = max(c0[0], c0[2] - 0.06)   # конец паузы перед фразой, с запасом
    b = min(c1[0], c1[1] + 0.12)   # начало паузы после фразы, с запасом
    if i == 0:
        first = next((ss, se) for ss, se in sil)
        a = max(0, first[1] - 0.06) if first[0] < 0.05 else 0
    segs.append([round(a, 3), round(b, 3)])

# проверка: распознанный текст внутри куска против ожидаемого
rep = []
bad = 0
for i, p in enumerate(phr):
    a, b = segs[i]
    got = [rec[k] for k in range(len(rec)) if a - 0.05 <= (rt[k][0] + rt[k][1]) / 2 <= b + 0.05]
    want = norm_words(p["text"])
    r = difflib.SequenceMatcher(None, " ".join(want), " ".join(got)).ratio()
    p["score"] = round(r, 2); p["got"] = " ".join(got)
    if r < 0.75 or b - a < 0.3:
        bad += 1
        rep.append(f"{i:4d} {p['id']:<16} {r:.2f} {a:8.2f}-{b:8.2f}\n     ждали: {' '.join(want)}\n     слышно: {' '.join(got)}")
if __name__ == "__main__": json.dump([{"id": p["id"], "a": segs[i][0], "b": segs[i][1], "score": p["score"]} for i, p in enumerate(phr)],
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
if __name__ == "__main__": open(REP, "w", encoding="utf-8").write(f"фраз {N}, подозрительных {bad}\n\n" + "\n".join(rep))
print("phrases", N, "matched words", sum(m is not None for m in match), "/", len(exp), "rec words", len(rec), "suspicious", bad)
