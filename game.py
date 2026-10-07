#!/usr/bin/env python3
"""A tiny, original pixel-art Mario-inspired normal-distribution playground."""

import argparse
import math
import os
from pathlib import Path
import struct
import sys
import tempfile

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import pygame
except ImportError:
    print("Install the free dependency first: python3 -m pip install -r requirements.txt")
    sys.exit(1)

from game_logic import Game, SampleLog, WIDTH, GROUND_Y, GAP_X, WORLD_BOTTOM, MAX_DRAWS
from music import BackgroundMusic, choose_music

BASE = Path(__file__).resolve().parent
HEIGHT = 272
SKY = (92, 148, 252)
WHITE = (255, 249, 233)
INK = (31, 25, 26)
BRICK = (200, 76, 12)
GOLD = (252, 188, 60)
GREEN = (0, 168, 0)
SCENES = ("random outcomes", "binary control variable", "multiple control variables", "Endogneity")

# A little bitmap alphabet keeps the artwork sharp at integer zoom levels.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
    ":": ["00000", "00110", "00110", "00000", "00110", "00110", "00000"],
    "/": ["00001", "00001", "00010", "00100", "01000", "10000", "10000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    ",": ["00000", "00000", "00000", "00000", "00110", "00110", "00100"],
    "=": ["00000", "00000", "11111", "00000", "11111", "00000", "00000"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
}

MARIO = [
    ".....RRRRR......",
    "....RRRRRRRRR...",
    "....BBBSSBS.....",
    "...BSBSSSBSSS...",
    "...BSBBSSSBSSS..",
    "...BBSSSSBBBB...",
    ".....SSSSSS.....",
    "....RBRRRB......",
    "...RRBRRRBRRR...",
    "..RRRBBBBBRRRR..",
    "..SSBYBBBYBSSS..",
    "..SSSBBBBBBSSS..",
    "...BBBBBBBBBB...",
    "...BBBB..BBBB...",
    "..BBBB....BBBB..",
    ".BBBBB....BBBBB.",
]


def text(surface, words, x, y, color=WHITE, scale=1, center=False, shadow=False):
    if center:
        x -= (len(words) * 6 - 1) * scale // 2
    if shadow:
        text(surface, words, x + scale, y + scale, INK, scale)
    for char in words.upper():
        for row, bits in enumerate(FONT.get(char, [])):
            for col, bit in enumerate(bits):
                if bit == "1":
                    pygame.draw.rect(surface, color, (x + col * scale, y + row * scale, scale, scale))
        x += 6 * scale


def make_mario():
    sprite = pygame.Surface((16, 16), pygame.SRCALPHA)
    colors = {"R": (181, 49, 32), "B": (106, 59, 17), "S": (255, 190, 126), "Y": GOLD}
    for y, row in enumerate(MARIO):
        for x, pixel in enumerate(row):
            if pixel in colors:
                sprite.set_at((x, y), colors[pixel])
    return sprite


def brick(surface, x, y):
    pygame.draw.rect(surface, INK, (x, y, 16, 16))
    pygame.draw.rect(surface, BRICK, (x + 1, y + 1, 14, 14))
    pygame.draw.line(surface, (255, 164, 84), (x + 1, y + 1), (x + 14, y + 1))
    pygame.draw.line(surface, INK, (x, y + 8), (x + 15, y + 8))
    pygame.draw.line(surface, INK, (x + 7, y + 1), (x + 7, y + 7))
    pygame.draw.line(surface, INK, (x + 3, y + 9), (x + 3, y + 15))
    pygame.draw.line(surface, INK, (x + 12, y + 9), (x + 12, y + 15))
    pygame.draw.line(surface, (255, 164, 84), (x + 1, y + 9), (x + 14, y + 9))


def cloud(surface, x, y, width=38):
    shade = (185, 222, 255)
    pygame.draw.rect(surface, shade, (x + 3, y + 10, width - 3, 9))
    for dx, dy, w, h in [(7, 1, 12, 13), (18, 0, 12, 14), (1, 7, 14, 10), (28, 7, width - 27, 10)]:
        pygame.draw.rect(surface, WHITE, (x + dx, y + dy, w, h))
    pygame.draw.rect(surface, WHITE, (x + 4, y + 10, width - 3, 6))
    pygame.draw.rect(surface, SKY, (x + 10, y + 10, 2, 2))
    pygame.draw.rect(surface, SKY, (x + 27, y + 10, 2, 2))


def hill(surface, x, width, height):
    points = [(x, GROUND_Y), (x + 6, GROUND_Y - 7),
              (x + width // 2 - 9, GROUND_Y - height + 5),
              (x + width // 2 - 4, GROUND_Y - height),
              (x + width // 2 + 4, GROUND_Y - height),
              (x + width // 2 + 9, GROUND_Y - height + 5),
              (x + width - 6, GROUND_Y - 7), (x + width, GROUND_Y)]
    pygame.draw.polygon(surface, INK, points)
    pygame.draw.polygon(surface, (0, 184, 0), [(px, py + 2) for px, py in points])
    for dx, dy in [(width // 2 - 12, height // 2), (width // 2 + 5, height // 2 + 7), (width // 2 - 1, height - 12)]:
        pygame.draw.rect(surface, (0, 104, 0), (x + dx, GROUND_Y - dy, 3, 6))


def bush(surface, x):
    for dx, dy in [(0, 8), (8, 3), (17, 0), (26, 4), (34, 9)]:
        pygame.draw.rect(surface, INK, (x + dx, GROUND_Y - 15 + dy, 12, 15 - dy))
        pygame.draw.rect(surface, (112, 216, 0), (x + dx + 1, GROUND_Y - 14 + dy, 10, 14 - dy))
    pygame.draw.rect(surface, (112, 216, 0), (x + 2, GROUND_Y - 6, 42, 6))


def pipe(surface, rect):
    x, y, w, h = map(int, (rect.x, rect.y, rect.w, rect.h))
    pygame.draw.rect(surface, INK, (x + 2, y + 8, w - 4, h - 8))
    pygame.draw.rect(surface, GREEN, (x + 3, y + 8, w - 6, h - 8))
    pygame.draw.rect(surface, (160, 232, 0), (x + 5, y + 8, 4, h - 8))
    pygame.draw.rect(surface, (0, 104, 0), (x + w - 9, y + 8, 5, h - 8))
    pygame.draw.rect(surface, INK, (x, y, w, 9))
    pygame.draw.rect(surface, GREEN, (x + 1, y + 1, w - 2, 6))
    pygame.draw.rect(surface, (160, 232, 0), (x + 3, y + 1, 5, 6))
    pygame.draw.rect(surface, (0, 104, 0), (x + w - 8, y + 1, 6, 6))


def question_box(surface, game):
    x, y = int(game.box.x), int(game.box.y)
    if game.bump:
        y -= round(3 * math.sin(math.pi * game.bump / 0.16))
    empty = len(game.samples) == MAX_DRAWS
    face = (148, 84, 40) if empty else GOLD
    border, symbol = INK, INK
    highlight = (221, 143, 70) if empty else (255, 224, 151)
    shade = (108, 54, 20)
    if (game.binary_control or game.endogeneity_control) and not empty:
        face = (0, 0, 0) if game.binary_value == 1 else (255, 255, 255)
        symbol = (255, 255, 255) if game.binary_value == 1 else (0, 0, 0)
        border = highlight = shade = (125, 125, 125)
    elif game.rgb_control and not empty:
        face = game.rgb_value
        r, g, b = face
        symbol = (0, 0, 0) if 299 * r + 587 * g + 114 * b >= 128000 else (255, 255, 255)
        border = highlight = shade = (125, 125, 125)
    pygame.draw.rect(surface, border, (x, y, 16, 16))
    pygame.draw.rect(surface, face, (x + 1, y + 1, 14, 14))
    pygame.draw.line(surface, highlight, (x + 1, y + 1), (x + 14, y + 1))
    pygame.draw.line(surface, shade, (x + 1, y + 14), (x + 14, y + 14))
    for dx, dy in [(2, 2), (13, 2), (2, 13), (13, 13)]:
        surface.set_at((x + dx, y + dy), border)
    if not empty:
        text(surface, "?", x + 6, y + 4, symbol)


def draw_scene(surface, game, sprite, popups, paused=False, error=None):
    surface.fill(SKY)
    cloud(surface, 40, 66)
    cloud(surface, 139, 86, 49)
    cloud(surface, 244, 54)
    cloud(surface, 336, 94)
    hill(surface, -9, 90, 41)
    hill(surface, 216, 48, 23)
    bush(surface, 124)
    # A short vine makes W/S useful without removing platform gravity.
    pygame.draw.rect(surface, INK, (game.vine_x - 1, game.vine_top, 3, GROUND_Y - game.vine_top))
    pygame.draw.line(surface, (128, 220, 0), (game.vine_x, game.vine_top), (game.vine_x, GROUND_Y - 1))
    for y in range(game.vine_top + 5, GROUND_Y - 5, 9):
        pygame.draw.polygon(surface, GREEN, [(game.vine_x, y + 5), (game.vine_x - 7, y), (game.vine_x - 7, y + 4)])
        pygame.draw.polygon(surface, GREEN, [(game.vine_x + 1, y + 7), (game.vine_x + 8, y + 2), (game.vine_x + 8, y + 6)])
    text(surface, "W/S", game.vine_x, game.vine_top - 14, WHITE, center=True, shadow=True)
    for solid in game.bricks:
        brick(surface, int(solid.x), int(solid.y))
    question_box(surface, game)
    pipe(surface, game.pipe)
    for y in range(GROUND_Y, WORLD_BOTTOM, 16):
        for x in range(0, GAP_X, 16):
            brick(surface, x, y)
    text(surface, "GAP", 357, GROUND_Y - 17, WHITE, center=True, shadow=True)
    pygame.draw.polygon(surface, WHITE, [(353, GROUND_Y - 6), (361, GROUND_Y - 6), (357, GROUND_Y - 2)])

    # Draw Mario only in the world, so falling never covers the controls.
    surface.set_clip(pygame.Rect(0, 32, WIDTH, WORLD_BOTTOM - 32))
    current = sprite
    if game.crouching:
        current = pygame.transform.scale(sprite, (16, 12))
    elif game.grounded and game.vx and int(game.elapsed * 12) % 2:
        current = sprite.copy()
        current.fill((0, 0, 0, 0), (0, 14, 16, 2))
        pygame.draw.rect(current, (106, 59, 17), (3, 14, 5, 2))
        pygame.draw.rect(current, (106, 59, 17), (10, 13, 4, 2))
    if game.facing < 0:
        current = pygame.transform.flip(current, True, False)
    surface.blit(current, (round(game.player.x) - 1, round(game.player.bottom) - current.get_height()))
    for value, age, popup_x in popups:
        y = 128 - int(min(age, 0.7) * 42)
        coin_width = 3 if int(age * 12) % 2 else 7
        pygame.draw.rect(surface, INK, (popup_x - coin_width // 2 - 1, y - 15, coin_width + 2, 12))
        pygame.draw.rect(surface, GOLD, (popup_x - coin_width // 2, y - 14, coin_width, 10))
        label = f"{value:+.4f}"
        pygame.draw.rect(surface, INK, (popup_x - len(label) * 3 - 3, y - 1, len(label) * 6 + 5, 10))
        text(surface, label, popup_x, y, GOLD, center=True)
    surface.set_clip(None)

    text(surface, "MARIO", 16, 10)
    text(surface, f"{len(game.samples) * 100:06d}", 16, 21)
    text(surface, "DRAWS", 112, 10)
    text(surface, f"{len(game.samples):02d}/10", 112, 21)
    text(surface, "WORLD", 220, 10)
    text(surface, "1-1", 226, 21)
    if not game.binary_control and not game.rgb_control and not game.endogeneity_control:
        text(surface, "NORMAL", 314, 10)
        text(surface, f"N({game.outcome_mean},1)", 314, 21)
    if game.samples:
        text(surface, f"LAST {game.samples[-1]:+.4f}  SAVED TO CSV", 16, 43, WHITE, shadow=True)
    if game.endogeneity_control:
        if len(game.samples) == MAX_DRAWS:
            x, z = game.endogeneity_samples[-1]
            label = f"LAST HIT X={x} Z={z}"
        else:
            color = "BLACK" if game.binary_value == 1 else "WHITE"
            location = "PIPE" if game.z_value == 1 else "VINE"
            label = f"X={game.binary_value} {color} (0.2S) Z={game.z_value} {location}"
        text(surface, label, 16, 55, WHITE, shadow=True)
    elif game.binary_control:
        if len(game.samples) == MAX_DRAWS:
            text(surface, f"LAST HIT X={game.binary_samples[-1]}", 16, 55, WHITE, shadow=True)
        else:
            color = "BLACK" if game.binary_value == 1 else "WHITE"
            text(surface, f"BINARY X={game.binary_value} {color} (0.2S)", 16, 55, WHITE, shadow=True)
    elif game.rgb_control:
        r, g, b = game.rgb_samples[-1] if len(game.samples) == MAX_DRAWS else game.rgb_value
        label = f"R={r} G={g} B={b}"
        label = "LAST HIT " + label if len(game.samples) == MAX_DRAWS else label + " (0.2S)"
        text(surface, label, 16, 55, WHITE, shadow=True)
    if len(game.samples) == MAX_DRAWS:
        text(surface, "BOX EMPTY! ALL 10 DRAWS SAVED.", 192, 64, GOLD, center=True, shadow=True)
    else:
        text(surface, "JUMP UNDER THE ? TO DRAW A NUMBER", 192, 113, WHITE, center=True, shadow=True)

    pygame.draw.rect(surface, (25, 29, 51), (0, WORLD_BOTTOM, WIDTH, HEIGHT - WORLD_BOTTOM))
    pygame.draw.line(surface, GOLD, (0, WORLD_BOTTOM), (WIDTH, WORLD_BOTTOM))
    text(surface, "A/D WALK  W/S VINE  S CROUCH  U JUMP", 192, 248, center=True)
    text(surface, "R RESTART  P PAUSE  M MUSIC  ESC QUIT", 192, 261, (165, 186, 225), center=True)

    if game.dead or paused or error:
        veil = pygame.Surface((WIDTH, WORLD_BOTTOM), pygame.SRCALPHA)
        veil.fill((12, 18, 42, 150))
        surface.blit(veil, (0, 0))
        pygame.draw.rect(surface, INK, (36, 84, 312, 85))
        pygame.draw.rect(surface, GOLD, (36, 84, 312, 85), 1)
        title = "SAVE ERROR" if error else "GAME OVER" if game.dead else "PAUSED"
        text(surface, title, 192, 96, GOLD, 2, center=True)
        text(surface, f"{len(game.samples)} / 10 DRAWS SAVED TO CSV", 192, 121, center=True)
        message = "CHECK TERMINAL. ESC TO QUIT." if error else "R TO RESTART   ESC TO QUIT" if game.dead else "P TO CONTINUE   ESC TO QUIT"
        text(surface, message, 192, 147, center=True)


def draw_start_menu(surface, sprite, selected):
    surface.fill(SKY)
    cloud(surface, 22, 47)
    cloud(surface, 315, 56)
    hill(surface, -9, 90, 41)
    hill(surface, 280, 76, 32)
    bush(surface, 249)
    for y in range(GROUND_Y, WORLD_BOTTOM, 16):
        for x in range(0, WIDTH, 16):
            brick(surface, x, y)
    surface.blit(sprite, (24, GROUND_Y - 16))
    pygame.draw.rect(surface, INK, (109, 20, 170, 33))
    pygame.draw.rect(surface, BRICK, (107, 18, 170, 33))
    pygame.draw.rect(surface, GOLD, (107, 18, 170, 33), 1)
    text(surface, "MARIO LAB", 192, 28, WHITE, 2, center=True, shadow=True)

    pygame.draw.rect(surface, INK, (34, 67, 316, 137))
    pygame.draw.rect(surface, GOLD, (34, 67, 316, 137), 1)
    text(surface, "CHOOSE A SCENE", 192, 78, WHITE, center=True)
    for index, label in enumerate(SCENES):
        y = 99 + index * 21
        if index == selected:
            pygame.draw.rect(surface, (68, 43, 32), (46, y - 4, 292, 17))
            pygame.draw.rect(surface, GOLD, (46, y - 4, 292, 17), 1)
            pygame.draw.polygon(surface, GOLD, [(54, y - 1), (54, y + 7), (60, y + 3)])
        text(surface, f"{index + 1}. {label}", 70, y, GOLD if index == selected else WHITE)
    text(surface, "4 SCENES. 10 DRAWS EACH.", 192, 190, (165, 186, 225), center=True)

    pygame.draw.rect(surface, (25, 29, 51), (0, WORLD_BOTTOM, WIDTH, HEIGHT - WORLD_BOTTOM))
    pygame.draw.line(surface, GOLD, (0, WORLD_BOTTOM), (WIDTH, WORLD_BOTTOM))
    text(surface, "W UP  S DOWN  ENTER SELECT", 192, 248, center=True)
    text(surface, "M MUSIC    ESC QUIT", 192, 261, (165, 186, 225), center=True)


def choose_start_scene(screen, canvas, sprite, music):
    """Return a scene index, or None when the player closes the menu."""
    selected = 0
    clock = pygame.time.Clock()
    pygame.key.set_repeat(300, 140)
    try:
        while True:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.WINDOWFOCUSLOST:
                    music.update(paused=True)
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    music.update(paused=False)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_w:
                        selected = (selected - 1) % len(SCENES)
                    elif event.key == pygame.K_s:
                        selected = (selected + 1) % len(SCENES)
                    elif event.key == pygame.K_m:
                        music.toggle_mute()
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        music.update(paused=False)
                        return selected
            draw_start_menu(canvas, sprite, selected)
            pygame.transform.scale(canvas, screen.get_size(), screen)
            pygame.display.flip()
    finally:
        # Repeated keydown events must not turn held U into repeated jumps.
        pygame.key.set_repeat()


def make_sounds(enabled):
    if not enabled or pygame.mixer.get_init() is None:
        return {}
    sounds = {}
    specs = {"jump": [(280, 0.06), (420, 0.07), (580, 0.07)],
             "sample": [(988, 0.07), (1318, 0.12)],
             "bump": [(110, 0.08)], "empty": [(110, 0.08)],
             "death": [(440, 0.10), (330, 0.10), (220, 0.16), (110, 0.24)]}
    for name, notes in specs.items():
        raw = bytearray()
        for frequency, duration in notes:
            count = int(duration * 22050)
            for i in range(count):
                envelope = min(1.0, i / 100) * (1 - i / count)
                amplitude = int(2000 * envelope) * (1 if math.sin(2 * math.pi * frequency * i / 22050) >= 0 else -1)
                raw.extend(struct.pack("<h", amplitude))
        sounds[name] = pygame.mixer.Sound(buffer=raw)
    return sounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=int, choices=(2, 3, 4), default=3, help="pixel zoom (default: 3)")
    parser.add_argument("--no-sound", action="store_true")
    parser.add_argument("--no-music", action="store_true", help="disable music, keep sound effects")
    parser.add_argument("--music", type=Path, help="loop a local WAV, OGG, or MP3 instead of the included original tune")
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("--screenshot", type=Path, help="render one PNG without opening a window or saving game data")
    parser.add_argument("--screenshot-scene", choices=("game", "binary", "rgb", "endogeneity", "menu"), default="game", help="which scene to render with --screenshot")
    args = parser.parse_args()
    if args.screenshot:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH * args.scale, HEIGHT * args.scale))
        pygame.display.set_caption("Mario's Normal World | A S D W + U")
        canvas = pygame.Surface((WIDTH, HEIGHT))
        sprite = make_mario()
        if args.screenshot:
            if args.screenshot_scene == "menu":
                draw_start_menu(canvas, sprite, 0)
            else:
                with tempfile.TemporaryDirectory() as folder:
                    scene_options = {"binary_control": args.screenshot_scene == "binary", "rgb_control": args.screenshot_scene == "rgb", "endogeneity_control": args.screenshot_scene == "endogeneity"}
                    log = SampleLog(Path(folder), **scene_options)
                    try:
                        draw_scene(canvas, Game(log, **scene_options), sprite, [])
                    finally:
                        log.close()
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(pygame.transform.scale(canvas, screen.get_size()), str(args.screenshot))
            print(f"Preview saved: {args.screenshot.resolve()}")
            return
        sounds = make_sounds(not args.no_sound)
        music = BackgroundMusic(choose_music(args.music), not args.no_sound and not args.no_music)
        selected = choose_start_scene(screen, canvas, sprite, music)
        if selected is None:
            return
        scene_options = {"binary_control": selected == 1, "rgb_control": selected == 2, "endogeneity_control": selected == 3}
        log = SampleLog(args.data_dir, **scene_options)
        try:
            game = Game(log, **scene_options)
            print(f"Scene: {SCENES[selected]}", flush=True)
            print(f"Saving draws to: {log.path.resolve()}", flush=True)
            print("A/D: walk. W/S: climb vine. S: crouch/descend. U: jump. M: mute music. R: restart. P: pause. Esc: quit.", flush=True)
            clock = pygame.time.Clock()
            running, paused, error = True, False, None
            popups = []
            accumulator = 0.0
            jump_pending = False
            step = 1 / 120
            while running:
                frame_dt = min(clock.tick(60) / 1000, 0.05)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.WINDOWFOCUSLOST:
                        paused = True
                        jump_pending = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_p and not game.dead and not error:
                            paused = not paused
                            jump_pending = False
                        elif event.key == pygame.K_m:
                            music.toggle_mute()
                        elif event.key == pygame.K_r and not error:
                            next_log = SampleLog(args.data_dir, **scene_options)
                            log.close()
                            log = next_log
                            game = Game(log, **scene_options)
                            music.restart()
                            paused, popups, accumulator, jump_pending = False, [], 0.0, False
                            print(f"New game. Saving draws to: {log.path.resolve()}", flush=True)
                        elif event.key == pygame.K_u and not paused and not error:
                            jump_pending = True
                keys = pygame.key.get_pressed()
                if not paused and not error:
                    accumulator += frame_dt
                    while accumulator >= step:
                        try:
                            game.update(step, int(keys[pygame.K_d]) - int(keys[pygame.K_a]),
                                        int(keys[pygame.K_s]) - int(keys[pygame.K_w]), jump_pending)
                        except OSError as exc:
                            error = str(exc)
                            print(f"Could not save CSV: {exc}. Gameplay stopped.", file=sys.stderr, flush=True)
                            break
                        jump_pending = False
                        accumulator -= step
                        for name, value in game.events:
                            if name == "sample":
                                popups.append((value, 0.0, game.last_hit_center))
                                control = f" X={game.binary_samples[-1]}" if game.binary_control else ""
                                if game.rgb_control:
                                    control = f" RGB={game.rgb_samples[-1]}"
                                elif game.endogeneity_control:
                                    x, z = game.endogeneity_samples[-1]
                                    control = f" X={x} Z={z}"
                                print(f"Hit {len(game.samples):02d}:{control} outcome={value!r}", flush=True)
                            if name in sounds:
                                sounds[name].play()
                        game.events.clear()
                    popups = [(value, age + frame_dt, popup_x) for value, age, popup_x in popups if age + frame_dt < 1.25]
                else:
                    accumulator = 0.0
                music.update(paused=paused or bool(error), dead=game.dead)
                draw_scene(canvas, game, sprite, popups, paused, error)
                pygame.transform.scale(canvas, screen.get_size(), screen)
                pygame.display.flip()
        finally:
            log.close()
    except KeyboardInterrupt:
        pass
    except (OSError, pygame.error) as exc:
        print(f"Unable to run the game: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
