#!/usr/bin/env python3
"""Turn a two-host dialogue script into one MP3.

Script format: one line per turn, starting with the speaker's name and a colon:
    RYAN: Good morning, and welcome to Tech Unzip.
    HEART: Morning, Ryan. What's the big story today?
Blank lines are ignored. Lines without a speaker go to RYAN.

Voices:
    RYAN  = Piper "en_US-ryan-high", slowed to 0.8x speed
    HEART = Kokoro "af_heart", slowed to 0.85x speed

Usage:
    python3 scripts/make_audio.py script.txt "out.mp3"
Needs: pip install --break-system-packages piper-tts kokoro-onnx soundfile scipy
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np
import scipy.signal as ss
import soundfile as sf

CACHE = os.path.expanduser("~/.cache/morning-voices")
SR = 24000
PAUSE_BETWEEN_TURNS = 0.45  # seconds

FILES = {
    "en_US-ryan-high.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx",
    "en_US-ryan-high.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json",
    "kokoro-v1.0.onnx": "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/voices-v1.0.bin",
}


def fetch_voices():
    os.makedirs(CACHE, exist_ok=True)
    for name, url in FILES.items():
        path = os.path.join(CACHE, name)
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            subprocess.run(["curl", "-sSL", "-m", "600", "-o", path, url], check=True)


def ryan(text, tmpdir, i):
    out = os.path.join(tmpdir, f"r{i}.wav")
    subprocess.run(
        ["python3", "-m", "piper", "-m", os.path.join(CACHE, "en_US-ryan-high.onnx"),
         "--length-scale", "1.25", "--sentence-silence", "0.3", "-f", out],
        input=text.encode("utf-8"), stderr=subprocess.DEVNULL, check=True)
    d, s = sf.read(out)
    if d.ndim > 1:
        d = d.mean(axis=1)
    return ss.resample(d, int(len(d) * SR / s)) if s != SR else d


def parse(path):
    turns = []
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(RYAN|HEART)\s*[:|]\s*(.+)$", line, re.I)
        if m:
            turns.append((m.group(1).upper(), m.group(2).strip()))
        else:
            turns.append(("RYAN", line))
    return turns


def main(src, dst):
    fetch_voices()
    from kokoro_onnx import Kokoro
    kok = Kokoro(os.path.join(CACHE, "kokoro-v1.0.onnx"), os.path.join(CACHE, "voices-v1.0.bin"))
    pieces = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (who, text) in enumerate(parse(src)):
            if who == "HEART":
                audio, _ = kok.create(text, voice="af_heart", speed=0.85, lang="en-us")
            else:
                audio = ryan(text, tmp, i)
            pieces.append(np.asarray(audio, dtype="float32"))
            pieces.append(np.zeros(int(SR * PAUSE_BETWEEN_TURNS), dtype="float32"))
        wav = os.path.join(tmp, "all.wav")
        sf.write(wav, np.concatenate(pieces), SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "40k", dst], check=True)
    print(dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
