import os
_D = r"C:\Users\User\AppData\Local\Programs\Ollama\lib\ollama\cuda_v12"
os.add_dll_directory(_D); os.environ["PATH"] = _D + ";" + os.environ["PATH"]
import json, subprocess, sys, time, difflib
sys.path.insert(0, r"E:\Claude-temp\chasiki")
import numpy as np
from faster_whisper import WhisperModel

SRC = r"E:\chasiki\voice\ОЗВУЧКА.mp3"
cuts = json.load(open(r"E:\Claude-temp\chasiki\cuts.json", encoding="utf-8"))
phr = {it["id"]: it["text"] for b in json.load(open(r"E:\chasiki\voice\phrases.json", encoding="utf-8")) for it in b["items"]}
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
m = WhisperModel("medium", device="cuda", compute_type="float16")
src_norm = open(r"E:\Claude-temp\chasiki\align.py", encoding="utf-8").read()
ns = {}
exec(src_norm.split("key = lambda")[0], ns)  # только функции нормализации
norm = ns["norm_words"]
out = []
t0 = time.time()
for n, c in enumerate(cuts):
    a, b = int(c["a"] * 16000), int(c["b"] * 16000)
    seg = np.concatenate([np.zeros(4000, np.float32), pcm[a:b], np.zeros(4000, np.float32)])
    segs, _ = m.transcribe(seg, language="ru", beam_size=5, condition_on_previous_text=False, vad_filter=False, without_timestamps=True)
    got = " ".join(s.text for s in segs).strip()
    want = phr[c["id"]]
    r = difflib.SequenceMatcher(None, " ".join(norm(want)), " ".join(norm(got))).ratio()
    out.append({"i": n, "id": c["id"], "a": c["a"], "b": c["b"], "r": round(r, 2), "want": want, "got": got})
    if n % 100 == 0: print(n, round(time.time() - t0), flush=True)
json.dump(out, open(r"E:\Claude-temp\chasiki\verify.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("done", round(time.time() - t0), "bad<0.8:", sum(x["r"] < 0.8 for x in out), flush=True)
