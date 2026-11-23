import os
_D = r"C:\Users\User\AppData\Local\Programs\Ollama\lib\ollama\cuda_v12"
os.add_dll_directory(_D); os.environ["PATH"] = _D + ";" + os.environ["PATH"]
import json, sys, time, os
from faster_whisper import WhisperModel
src = sys.argv[1]; out = sys.argv[2]
t0 = time.time()
try:
    m = WhisperModel("medium", device="cuda", compute_type="float16")
    dev = "cuda"
except Exception as e:
    print("cuda fail:", e, flush=True)
    m = WhisperModel("medium", device="cpu", compute_type="int8"); dev = "cpu"
print("device", dev, flush=True)
def run(model):
    segs, info = model.transcribe(src, language="ru", word_timestamps=True, beam_size=5,
                                  condition_on_previous_text=False, vad_filter=False)
    words = []
    for s in segs:
        for w in s.words:
            words.append([round(w.start, 3), round(w.end, 3), w.word])
        if len(words) % 500 < len(s.words):
            print(f"{s.end:.0f}s", flush=True)
    return words
try:
    words = run(m)
except Exception as e:
    print("run fail on", dev, e, flush=True)
    m = WhisperModel("medium", device="cpu", compute_type="int8"); words = run(m)
json.dump(words, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print("done", len(words), "words", round(time.time() - t0), "s", flush=True)
