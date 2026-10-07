"""An original chiptune loop and optional playback of a local music file.

The included composition is original; it is not the Super Mario Bros. theme.
Run `python3 music.py` to regenerate the included WAV using only Python.
"""

from array import array
import math
from pathlib import Path
import random
import sys
import wave

MUSIC_DIR = Path(__file__).resolve().parent / "assets" / "music"
DEFAULT_MUSIC = MUSIC_DIR / "original_chiptune.wav"
RATE = 22050
BPM = 140


def write_original_music(path=DEFAULT_MUSIC):
    """Synthesize a sixteen-bar loop: two pulse voices, bass, and percussion."""
    beat_seconds = 60 / BPM
    bars = [
        [(67, .5), (71, .5), (74, 1), (72, .5), (71, .5), (69, 1)],
        [(64, 1), (67, .5), (69, .5), (71, 1), (67, 1)],
        [(65, .5), (69, .5), (72, 1), (74, .5), (72, .5), (69, 1)],
        [(71, .5), (69, .5), (67, .5), (66, .5), (62, 1), (0, 1)],
        [(67, .5), (74, .5), (76, 1), (74, .5), (71, .5), (69, 1)],
        [(72, 1), (71, .5), (69, .5), (67, 1), (64, 1)],
        [(65, .5), (67, .5), (69, .5), (72, .5), (71, 1), (69, 1)],
        [(74, .5), (71, .5), (69, .5), (66, .5), (67, 1), (0, 1)],
        [(79, 1), (76, .5), (74, .5), (71, .5), (74, .5), (76, 1)],
        [(72, .5), (76, .5), (79, 1), (76, 1), (72, 1)],
        [(77, 1), (74, .5), (72, .5), (69, .5), (72, .5), (74, 1)],
        [(78, .5), (74, .5), (71, 1), (69, .5), (66, .5), (62, 1)],
        [(76, .5), (74, .5), (71, 1), (67, .5), (69, .5), (71, 1)],
        [(72, .5), (71, .5), (69, 1), (64, .5), (67, .5), (69, 1)],
        [(65, .5), (69, .5), (72, 1), (69, .5), (66, .5), (74, 1)],
        [(71, .5), (69, .5), (67, 1), (62, 1), (0, 1)],
    ]
    roots = [43, 48, 41, 38, 43, 48, 41, 38] * 2
    mix = [0.0] * round(64 * beat_seconds * RATE)

    def note(midi, beat, duration, gain, voice="pulse"):
        if midi == 0:
            return
        frequency = 440 * 2 ** ((midi - 69) / 12)
        start = round(beat * beat_seconds * RATE)
        count = round(duration * beat_seconds * RATE * .88)
        for i in range(min(count, len(mix) - start)):
            phase = (i * frequency / RATE) % 1
            value = 1.0 if phase < .25 else -1 / 3
            if voice == "triangle":
                value = 1 - 4 * abs(phase - .5)
            envelope = min(1.0, i / 80, (count - i) / 180)
            mix[start + i] += value * envelope * gain

    for bar, melody in enumerate(bars):
        beat = bar * 4
        for midi, duration in melody:
            note(midi, beat, duration, .34)
            beat += duration
        root = roots[bar]
        for offset in range(4):
            note(root if offset % 2 == 0 else root + 7, bar * 4 + offset, .85, .28, "triangle")
            # A quiet offbeat pulse accompaniment keeps the lead clear.
            note(root + (12, 16, 19, 16)[offset], bar * 4 + offset + .5, .35, .10)

    noise = random.Random(1985)
    for beat in range(64):
        start = round(beat * beat_seconds * RATE)
        count = round(.09 * RATE)
        for i in range(min(count, len(mix) - start)):
            envelope = (1 - i / count) ** 3
            if beat % 2 == 0:
                frequency = 105 - 65 * i / count
                value = math.sin(2 * math.pi * frequency * i / RATE) * .20
            else:
                value = noise.uniform(-1, 1) * .12
            mix[start + i] += value * envelope

    gain = .8 * 32767 / max(1.0, max(abs(value) for value in mix))
    pcm = array("h", (round(value * gain) for value in mix))
    if sys.byteorder != "little":
        pcm.byteswap()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with wave.open(str(temporary), "wb") as output:
        output.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())
    temporary.replace(path)
    return path


def choose_music(explicit_path=None):
    if explicit_path is not None:
        return Path(explicit_path).expanduser()
    for suffix in ("ogg", "mp3", "wav"):
        custom = MUSIC_DIR / ("overworld." + suffix)
        if custom.is_file():
            return custom
    return DEFAULT_MUSIC


class BackgroundMusic:
    """Keep streaming music separate from jump/coin/death sound effects."""

    def __init__(self, path, enabled=True):
        import pygame
        self.pygame = pygame
        self.active = False
        self.muted = False
        self.paused = False
        self.stopped = False
        if not enabled or pygame.mixer.get_init() is None:
            return
        try:
            path = Path(path)
            if path == DEFAULT_MUSIC and not path.is_file():
                write_original_music(path)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(.30)
            pygame.mixer.music.play(loops=-1)
            self.active = True
            print(f"Background music: {path.resolve()}", flush=True)
        except (OSError, pygame.error) as exc:
            print(f"Could not play background music: {exc}. The game will continue.", file=sys.stderr, flush=True)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.active:
            self.pygame.mixer.music.set_volume(0.0 if self.muted else .30)

    def update(self, paused=False, dead=False):
        if not self.active or self.stopped:
            return
        if dead:
            self.pygame.mixer.music.stop()
            self.stopped = True
        elif paused != self.paused:
            if paused:
                self.pygame.mixer.music.pause()
            else:
                self.pygame.mixer.music.unpause()
            self.paused = paused

    def restart(self):
        if self.active:
            self.pygame.mixer.music.play(loops=-1)
            self.paused, self.stopped = False, False


if __name__ == "__main__":
    print(f"Original chiptune saved: {write_original_music()}")
