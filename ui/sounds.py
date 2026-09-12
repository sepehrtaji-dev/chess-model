"""Synthesized sound effects — no binary assets, generated at startup.

Tries QSoundEffect (volume control, overlap); falls back to winsound; if both
are unavailable it degrades to silence.
"""

import struct
import tempfile
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
SOUND_DIR = Path(tempfile.gettempdir()) / "chessnet_sounds"


def _wav_bytes(samples):
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype("<i2")
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(pcm.tobytes()), b"WAVE",
        b"fmt ", 16, 1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16,
        b"data", len(pcm.tobytes()),
    )
    return header + pcm.tobytes()


def _tone(freq, dur, decay=12.0, amp=0.6, attack=0.004, sweep_to=None):
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n) / SAMPLE_RATE
    f = freq if sweep_to is None else np.linspace(freq, sweep_to, n)
    phase = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    env = np.minimum(t / (attack * SAMPLE_RATE + 1e-9), 1.0) * np.exp(-decay * t)
    return amp * env * np.sin(phase)


def _noise_burst(dur, amp=0.25, decay=60.0):
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n) / SAMPLE_RATE
    rng = np.random.default_rng(7)
    return amp * np.exp(-decay * t) * rng.uniform(-1, 1, n)


def _make_sounds():
    move = _tone(760, 0.09, decay=34, amp=0.5, sweep_to=480) \
        + _noise_burst(0.025, amp=0.12)
    capture = _tone(300, 0.14, decay=22, amp=0.65, sweep_to=160) \
        + _noise_burst(0.05, amp=0.3, decay=40)
    check = _tone(660, 0.12, decay=18, amp=0.4) \
        + np.concatenate([np.zeros(int(SAMPLE_RATE * 0.09)),
                          _tone(880, 0.14, decay=16, amp=0.4)])
    end = _tone(523, 0.5, decay=6, amp=0.3) + _tone(659, 0.5, decay=6, amp=0.25) \
        + _tone(784, 0.6, decay=5, amp=0.22)
    return {"move": move, "capture": capture, "check": check, "end": end}


class SoundEngine:
    def __init__(self):
        self.enabled = True
        self._players = {}
        self._fallback = None
        try:
            from PySide6.QtMultimedia import QSoundEffect
            from PySide6.QtCore import QUrl
            SOUND_DIR.mkdir(exist_ok=True)
            for name, samples in _make_sounds().items():
                path = SOUND_DIR / f"{name}.wav"
                path.write_bytes(_wav_bytes(samples))
                player = QSoundEffect()
                player.setSource(QUrl.fromLocalFile(str(path)))
                player.setVolume(0.35)
                self._players[name] = player
        except Exception:
            try:
                import winsound
                self._fallback = winsound
                SOUND_DIR.mkdir(exist_ok=True)
                for name, samples in _make_sounds().items():
                    (SOUND_DIR / f"{name}.wav").write_bytes(
                        _wav_bytes(samples))
            except Exception:
                pass

    def play(self, name):
        if not self.enabled:
            return
        player = self._players.get(name)
        if player is not None:
            player.play()
        elif self._fallback is not None:
            try:
                path = SOUND_DIR / f"{name}.wav"
                self._fallback.PlaySound(str(path),
                                         self._fallback.SND_FILENAME
                                         | self._fallback.SND_ASYNC)
            except Exception:
                pass
