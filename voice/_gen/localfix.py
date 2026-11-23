# Точечная пересборка участка фраз [i0..i1]: распознаёт участок короткими кусками
# (резка только по тишине), выравнивает слова с текстом, режет по границам слов,
# потом заново распознаёт каждый новый кусок для проверки.
import os
_D = r"C:\Users\User\AppData\Local\Programs\Ollama\lib\ollama\cuda_v12"
os.add_dll_directory(_D); os.environ["PATH"] = _D + ";" + os.environ["PATH"]
import json, subprocess, sys, re, difflib
import numpy as np
from faster_whisper import WhisperModel

CUTS = sys.argv[1]; i0, i1 = int(sys.argv[2]), int(sys.argv[3]); OUT = sys.argv[4]
SRC = r"E:\chasiki\voice\ОЗВУЧКА.mp3"
ns = {}; exec(open(r"E:\Claude-temp\chasiki\align.py", encoding="utf-8").read().split("key = lambda")[0], ns)
norm = ns["norm_words"]
cuts = json.load(open(CUTS, encoding="utf-8"))
phr = {it["id"]: it["text"] for b in json.load(open(r"E:\chasiki\voice\phrases.json", encoding="utf-8")) for it in b["items"]}
txt = open(r"E:\Claude-temp\chasiki\sil_01.txt", encoding="utf-8", errors="ignore").read()
sil = [(float(a), float(b)) for a, b in zip(re.findall(r"silence_start: ([\d.]+)", txt), re.findall(r"silence_end: ([\d.]+)", txt))]

T0, T1 = cuts[i0]["a"], cuts[i1]["b"]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
m = WhisperModel("medium", device="cuda", compute_type="float16")

# куски по ~8 с, границы в середине пауз
ss = [((a + b) / 2) for a, b in sil if T0 < (a + b) / 2 < T1 and b - a > 0.3]
bounds = [T0]
for s in ss:
    if s - bounds[-1] > 8: bounds.append(s)
bounds.append(T1)
words = []
for a, b in zip(bounds, bounds[1:]):
    seg = pcm[int(a * 16000):int(b * 16000)]
    segs, _ = m.transcribe(seg, language="ru", beam_size=5, word_timestamps=True, condition_on_previous_text=False, vad_filter=False)
    for s in segs:
        for w in s.words:
            for k, x in enumerate(norm(w.word)):
                words.append((a + w.start, a + w.end, x))
ids = [cuts[i]["id"] for i in range(i0, i1 + 1)]
exp, own = [], []
for j, pid in enumerate(ids):
    for x in norm(phr[pid]): exp.append(x); own.append(j)
sm = difflib.SequenceMatcher(None, [x[:4] for x in exp], [w[2][:4] for w in words], autojunk=False)
first, last = {}, {}
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        j = own[a + k]; t = words[b + k]
        first.setdefault(j, t[0]); last[j] = t[1]
print("matched phrases", len(first), "/", len(ids))
new = [dict(cuts[i]) for i in range(i0, i1 + 1)]
for j in range(len(ids) - 1):
    if j in last and (j + 1) in first and first[j + 1] > last[j] - 0.1:
        lo, hi = last[j], first[j + 1]
        cand = [(min(b, hi + .15) - max(a, lo - .15), a, b) for a, b in sil if b > lo - .15 and a < hi + .15]
        if cand:
            _, a, b = max(cand); cut0, cut1 = max(a, lo - .05), min(b, hi + .05)
        else:
            cut0 = cut1 = (lo + hi) / 2
        new[j]["b"] = round(min(cut1, cut0 + 0.12), 3); new[j + 1]["a"] = round(max(cut0, cut1 - 0.06), 3)
    else:
        print("no anchor between", ids[j], ids[j + 1])
bad = 0
for j, c in enumerate(new):
    seg = np.concatenate([np.zeros(4000, np.float32), pcm[int(c["a"] * 16000):int(c["b"] * 16000)], np.zeros(4000, np.float32)])
    segs, _ = m.transcribe(seg, language="ru", beam_size=5, condition_on_previous_text=False, vad_filter=False, without_timestamps=True)
    got = " ".join(s.text for s in segs).strip()
    r = difflib.SequenceMatcher(None, " ".join(norm(phr[c["id"]])), " ".join(norm(got))).ratio()
    c["score"] = round(r, 2)
    if r < 0.8:
        bad += 1; print(i0 + j, c["id"], round(r, 2), round(c["b"] - c["a"], 2), "|", phr[c["id"]], "|", got)
for j, c in enumerate(new): cuts[i0 + j] = c
json.dump(cuts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("bad after fix", bad)
