# Режет ОЗВУЧКА.mp3 по cuts.json и собирает спрайты: один mp3 на блок сценария
# + voice/vox.json со смещениями. Между фразами в спрайте 0.3 с тишины.
import json, subprocess, os, sys
import numpy as np

SRC = r"E:\chasiki\voice\ОЗВУЧКА.mp3"
PH = r"E:\chasiki\voice\phrases.json"
CUTS = r"E:\chasiki\voice\_gen\cuts.json"
OUTD = r"E:\chasiki\voice\sprites"
VOX = r"E:\chasiki\voice\vox.json"
SR = 24000
GAP = int(0.3 * SR)

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

# общая нормализация громкости по пику речи (без клиппинга)
peak = np.percentile(np.abs(pcm), 99.95)
gain = min(4.0, 0.7 * 32767 / max(peak, 1))
pcm = pcm * gain

blocks = json.load(open(PH, encoding="utf-8"))
cuts = {c["id"]: c for c in json.load(open(CUTS, encoding="utf-8"))}
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix")
os.makedirs(OUTD, exist_ok=True)
for f in os.listdir(OUTD):
    if f.endswith(".mp3"): os.remove(os.path.join(OUTD, f))

fade = int(0.01 * SR)
ramp = np.linspace(0, 1, fade, dtype=np.float32)
items, sprites = [], []
for bi, b in enumerate(blocks):
    name = f"s{bi + 1:02d}.mp3"
    parts, pos = [np.zeros(GAP, np.float32)], GAP
    for it in b["items"]:
        c = cuts[it["id"]]
        a, e = int(c["a"] * SR), int(c["b"] * SR)
        seg = pcm[a:e].copy()
        fx = os.path.join(FIX, it["id"] + ".mp3")
        if os.path.exists(fx):  # перезаписанная фраза: громкость как у старого куска
            nraw = subprocess.run(["ffmpeg", "-v", "error", "-i", fx, "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse",
                                   "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
            nseg = np.frombuffer(nraw, dtype=np.int16).astype(np.float32)
            rms = lambda x: float(np.sqrt(np.mean(x[np.abs(x) > 300] ** 2)))
            seg = nseg * (rms(seg) / max(1.0, rms(nseg)))
            print("override", it["id"], round(len(seg) / SR, 2), "s")
        if len(seg) > 2 * fade:
            seg[:fade] *= ramp; seg[-fade:] *= ramp[::-1]
        items.append([it["id"], bi, round(pos / SR, 3), round(len(seg) / SR, 3), it["text"]])
        parts += [seg, np.zeros(GAP, np.float32)]
        pos += len(seg) + GAP
    data = np.clip(np.concatenate(parts), -32767, 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "48k", os.path.join(OUTD, name)], input=data, check=True)
    sprites.append(name)

json.dump({"sprites": sprites, "items": items}, open(VOX, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
tot = sum(os.path.getsize(os.path.join(OUTD, s)) for s in sprites)
print("sprites", len(sprites), "items", len(items), "MB", round(tot / 1e6, 1), "gain", round(gain, 2))
