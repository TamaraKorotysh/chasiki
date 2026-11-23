# Нарезка по паузам с динамическим программированием.
# Опоры: фразы, которые Whisper распознал уверенно. Между опорами разрезы выбираются
# среди реальных пауз так, чтобы паузы были длинными, а длины кусков похожи на ожидаемые.
import json, re, difflib, math, sys, os
sys.path.insert(0, r"E:\Claude-temp\chasiki")
from align import norm_words, key  # noqa (align.py выполняется при импорте — это нормально, он быстрый)
import align as A

phr, rec, rt, sil, words = A.phr, A.rec, A.rt, A.sil, A.words
N = len(phr)
dur_total = words[-1][1] + 1.5

# 1. уверенные фразы: совпало >=70% слов, и совпавшие слова идут плотно
for p in phr:
    m = p["m"]
    p["conf"] = False
    if m and len(m) >= max(1, 0.7 * p["nw"]):
        span = rt[max(m)][1] - rt[min(m)][0]
        if span < 0.6 * p["nw"] + 1.5:
            p["conf"] = True
            p["c0"], p["c1"] = rt[min(m)][0], rt[max(m)][1]
# убираем опоры, нарушающие порядок
last = -1
for p in phr:
    if p["conf"]:
        if p["c0"] < last: p["conf"] = False
        else: last = p["c1"]

# 2. скорость речи: секунд на букву по уверенным фразам
chars = [max(2, len(re.sub(r"[^а-яё]", "", p["text"].lower()))) for p in phr]
rates = [(p["c1"] - p["c0"]) / chars[i] for i, p in enumerate(phr) if p["conf"] and chars[i] > 8]
rates.sort(); rate = rates[len(rates) // 2]
exp = [0.25 + chars[i] * rate for i in range(N)]
print("sec/char", round(rate, 4), "confident", sum(p["conf"] for p in phr))

# 3. кандидаты разрезов — середины пауз (короткие паузы -36dB тоже)
txt = open(r"E:\Claude-temp\chasiki\sil_01.txt", encoding="utf-8", errors="ignore").read()
sil2 = [(float(a), float(b)) for a, b in zip(re.findall(r"silence_start: ([\d.]+)", txt), re.findall(r"silence_end: ([\d.]+)", txt))]
C = sorted(((s + e) / 2, e - s, s, e) for s, e in sil2)
mids = [c[0] for c in C]
import bisect

# 4. ориентир g[i] для разреза i и допустимый коридор [lo, hi] от опор
cum = [0.0]
for i in range(N): cum.append(cum[-1] + exp[i] + 0.8)
anc = [(0, 0.0)]  # (номер разреза+1 как позиция в cum, время)
for i in range(N):
    if phr[i]["conf"]:
        anc.append((i, phr[i]["c0"])); anc.append((i + 1, phr[i]["c1"]))
anc.append((N, dur_total))
anc.sort()
g = []
for i in range(N - 1):
    pos = i + 1
    j = bisect.bisect_right([a[0] for a in anc], pos) - 1
    (p0, t0), (p1, t1) = anc[j], anc[min(j + 1, len(anc) - 1)]
    if p1 == p0: g.append(t0); continue
    f = (cum[pos] - cum[p0]) / max(1e-6, cum[p1] - cum[p0])
    g.append(t0 + f * (t1 - t0))
PEN = float(os.environ.get("PEN", "3"))
TOL = float(os.environ.get("TOL", "0.6"))
lo = [None] * (N - 1); hi = [None] * (N - 1)
for i in range(N - 1):
    if phr[i]["conf"]: lo[i] = phr[i]["c1"] - TOL
    if phr[i + 1]["conf"]: hi[i] = phr[i + 1]["c0"] + TOL

W = 15.0
cand = []
for i in range(N - 1):
    a = bisect.bisect_left(mids, g[i] - W); b = bisect.bisect_right(mids, g[i] + W)
    cand.append(list(range(a, b)))

def seg_cost(t0, t1, i):
    L = t1 - t0
    return ((L - exp[i]) / (0.4 + 0.3 * exp[i])) ** 2

def cut_cost(i, k):
    t, d = C[k][0], C[k][1]
    c = -3.0 * min(d, 1.2)
    if lo[i] is not None and t < lo[i]: c += PEN * (lo[i] - t)
    if hi[i] is not None and t > hi[i]: c += PEN * (t - hi[i])
    return c

INF = 1e18
back = []
prev_list = [(-1, 0.0)]
for i in range(N - 1):
    cur = []; bk = {}
    pk = sorted(prev_list)
    for k in cand[i]:
        t = C[k][0]; best, arg = INF, None
        for kp, cp in pk:
            if kp >= k: break
            tp = 0.0 if kp < 0 else C[kp][0]
            c = cp + seg_cost(tp, t, i)
            if c < best: best, arg = c, kp
        if arg is not None:
            cur.append((k, best + cut_cost(i, k))); bk[k] = arg
    if not cur:
        print("dead end at", i, phr[i]["id"]); sys.exit(1)
    cur.sort(key=lambda x: x[1]); prev_list = cur[:300]
    back.append(bk)
best, arg = INF, None
for k, c in prev_list:
    c2 = c + seg_cost(C[k][0], dur_total, N - 1)
    if c2 < best: best, arg = c2, k
cuts = [None] * (N - 1); k = arg
for i in range(N - 2, -1, -1):
    cuts[i] = k; k = back[i][k]

segs = []
for i in range(N):
    if i == 0:
        s0 = next(((s, e) for s, e in sil if s < 0.05), None)
        a = max(0, s0[1] - 0.06) if s0 else 0
    else:
        a = max(C[cuts[i - 1]][0], C[cuts[i - 1]][3] - 0.06)
    b = dur_total - 1.0 if i == N - 1 else min(C[cuts[i]][0], C[cuts[i]][2] + 0.12)
    segs.append([round(a, 3), round(b, 3)])

rep, bad = [], []
for i, p in enumerate(phr):
    a, b = segs[i]
    got = [rec[k] for k in range(len(rec)) if a - 0.05 <= (rt[k][0] + rt[k][1]) / 2 <= b + 0.05]
    want = norm_words(p["text"])
    r = difflib.SequenceMatcher(None, " ".join(want), " ".join(got)).ratio()
    p["score"] = round(r, 2)
    ratio = (b - a) / exp[i]
    if r < 0.75 or ratio < 0.5 or ratio > 2.2:
        bad.append(i)
        rep.append(f"{i:4d} {p['id']:<16} {r:.2f} len {b-a:5.2f}/{exp[i]:5.2f} {a:8.2f}-{b:8.2f}\n     ждали: {' '.join(want)}\n     слышно: {' '.join(got)}")
json.dump([{"id": p["id"], "a": segs[i][0], "b": segs[i][1], "score": p["score"], "bad": i in bad} for i, p in enumerate(phr)],
          open(r"E:\Claude-temp\chasiki\cuts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
open(r"E:\Claude-temp\chasiki\report2.txt", "w", encoding="utf-8").write(f"подозрительных {len(bad)}\n\n" + "\n".join(rep))
print("suspicious", len(bad))
