"""Check the complete Pygame loop with simulated input and no visible window."""

import csv
from collections import defaultdict
import os
import random
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import game as app
from game_logic import Game
from music import BackgroundMusic, DEFAULT_MUSIC, choose_music


class HeadlessTests(unittest.TestCase):
    def test_start_menu_navigation_and_scene_routing(self):
        choices = [
            # Down then up returns to random outcomes.
            ([pygame.K_s, pygame.K_w, pygame.K_RETURN], True),
            ([pygame.K_s, pygame.K_RETURN], True),
            ([pygame.K_s, pygame.K_s, pygame.K_RETURN], True),
            # W wraps from the first item to the fourth.
            ([pygame.K_w, pygame.K_RETURN], True),
            ([pygame.K_s, pygame.K_s, pygame.K_s, pygame.K_RETURN], True),
            ([pygame.K_ESCAPE], False),
        ]
        for sequence, starts_game in choices:
            with self.subTest(keys=sequence), tempfile.TemporaryDirectory() as folder:
                first = [True]

                def events():
                    if first[0]:
                        first[0] = False
                        return [pygame.event.Event(pygame.KEYDOWN, key=key) for key in sequence]
                    return [pygame.event.Event(pygame.QUIT)]

                args = ["game.py", "--scale", "2", "--no-sound", "--data-dir", folder]
                with patch.object(sys, "argv", args), \
                     patch.object(app, "Game", wraps=Game) as create_game, \
                     patch.object(pygame.event, "get", side_effect=events):
                    app.main()
                self.assertEqual(create_game.call_count, int(starts_game))
                self.assertEqual(len(list(Path(folder).glob("*.csv"))), int(starts_game))
                if starts_game:
                    self.assertEqual(create_game.call_args.kwargs["binary_control"], sequence == [pygame.K_s, pygame.K_RETURN])
                    self.assertEqual(create_game.call_args.kwargs["rgb_control"], sequence == [pygame.K_s, pygame.K_s, pygame.K_RETURN])
                    self.assertEqual(create_game.call_args.kwargs["endogeneity_control"], sequence in ([pygame.K_w, pygame.K_RETURN], [pygame.K_s, pygame.K_s, pygame.K_s, pygame.K_RETURN]))

    def test_rgb_block_colors_and_empty_appearance(self):
        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as folder:
                log = app.SampleLog(Path(folder), rgb_control=True)
                try:
                    state = Game(log, rgb_control=True)
                    surface = pygame.Surface((app.WIDTH, app.HEIGHT))
                    for channels, glyph in [((0, 0, 0), (255, 255, 255)),
                                             ((255, 255, 255), (0, 0, 0)),
                                             ((0, 255, 0), (0, 0, 0)),
                                             ((23, 132, 210), (255, 255, 255))]:
                        state.rgb_value = channels
                        app.question_box(surface, state)
                        self.assertEqual(surface.get_at((187, 149))[:3], channels)
                        self.assertEqual(surface.get_at((191, 148))[:3], glyph)
                    for _ in range(10):
                        state.hit_box()
                    state.bump = 0
                    app.question_box(surface, state)
                    self.assertEqual(surface.get_at((187, 149))[:3], (148, 84, 40))
                    app.draw_scene(surface, state, app.make_mario(), [])
                finally:
                    log.close()
        finally:
            pygame.quit()

    def test_binary_block_colors_and_empty_appearance(self):
        pygame.init()
        try:
            with tempfile.TemporaryDirectory() as folder:
                log = app.SampleLog(Path(folder), binary_control=True)
                try:
                    state = Game(log, binary_control=True)
                    surface = pygame.Surface((app.WIDTH, app.HEIGHT))
                    for binary, face, glyph in [(0, (255, 255, 255), (0, 0, 0)),
                                                (1, (0, 0, 0), (255, 255, 255))]:
                        state.binary_value = binary
                        app.question_box(surface, state)
                        self.assertEqual(surface.get_at((187, 149))[:3], face)
                        self.assertEqual(surface.get_at((191, 148))[:3], glyph)
                    for _ in range(10):
                        state.hit_box()
                    state.bump = 0
                    app.question_box(surface, state)
                    self.assertEqual(surface.get_at((187, 149))[:3], (148, 84, 40))
                    app.draw_scene(surface, state, app.make_mario(), [])
                finally:
                    log.close()
        finally:
            pygame.quit()

    def test_music_file_and_pause_mute_death_restart(self):
        with wave.open(str(DEFAULT_MUSIC), "rb") as recording:
            self.assertEqual(recording.getnchannels(), 1)
            self.assertEqual(recording.getsampwidth(), 2)
            self.assertEqual(recording.getframerate(), 22050)
            self.assertGreater(recording.getnframes() / recording.getframerate(), 25)
            self.assertTrue(any(recording.readframes(22050)))
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        try:
            music = BackgroundMusic(DEFAULT_MUSIC)
            self.assertTrue(music.active)
            self.assertTrue(pygame.mixer.music.get_busy())
            music.toggle_mute()
            self.assertEqual(pygame.mixer.music.get_volume(), 0)
            music.update(paused=True)
            self.assertTrue(music.paused)
            self.assertFalse(pygame.mixer.music.get_busy())
            music.update(paused=False)
            self.assertTrue(pygame.mixer.music.get_busy())
            music.update(dead=True)
            self.assertTrue(music.stopped)
            self.assertFalse(pygame.mixer.music.get_busy())
            music.restart()
            self.assertTrue(pygame.mixer.music.get_busy())
            self.assertEqual(pygame.mixer.music.get_volume(), 0)
            music.toggle_mute()
            self.assertGreater(pygame.mixer.music.get_volume(), 0)
        finally:
            pygame.quit()

    def test_custom_music_selection_and_disabled_playback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("music.MUSIC_DIR", root):
                self.assertEqual(choose_music(), DEFAULT_MUSIC)
                (root / "overworld.wav").touch()
                self.assertEqual(choose_music(), root / "overworld.wav")
                (root / "overworld.mp3").touch()
                self.assertEqual(choose_music(), root / "overworld.mp3")
                (root / "overworld.ogg").touch()
                self.assertEqual(choose_music(), root / "overworld.ogg")
                self.assertEqual(choose_music(root / "other.wav"), root / "other.wav")
            with patch.object(pygame.mixer.music, "load") as load:
                music = BackgroundMusic(root / "missing.wav", enabled=False)
                music.toggle_mute()
                music.update(paused=True)
                music.restart()
                self.assertFalse(music.active)
                load.assert_not_called()

    def test_walk_ten_jumps_empty_box_pipe_gap_restart_and_quit(self):
        self.playthrough(binary_control=False)

    def test_binary_scene_ten_hits_death_and_restart(self):
        self.playthrough(binary_control=True)

    def test_rgb_scene_ten_hits_death_and_restart(self):
        self.playthrough(rgb_control=True)

    def test_endogeneity_scene_ten_hits_death_and_restart(self):
        self.playthrough(endogeneity_control=True)

    def playthrough(self, binary_control=False, rgb_control=False, endogeneity_control=False):
        games = []
        frames = [0]
        extra_jump = [False]

        def create_game(log, **kwargs):
            if endogeneity_control:
                kwargs["endogeneity_rng"] = random.Random(123)
            result = Game(log, **kwargs)
            games.append(result)
            return result

        class FastClock:
            def tick(self, fps):
                frames[0] += 1
                return 17

        def events():
            if not games:
                keys = [pygame.K_s] * (3 if endogeneity_control else 2 if rgb_control else 1 if binary_control else 0) + [pygame.K_RETURN]
                return [pygame.event.Event(pygame.KEYDOWN, key=key) for key in keys]
            state = games[-1]
            if frames[0] > 2500 or len(games) > 1:
                return [pygame.event.Event(pygame.QUIT)]
            if state.dead:
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)]
            if state.grounded:
                target = state.box.x + 1 if endogeneity_control else 185
                under_box = abs(state.player.x - target) < 1
                if under_box and (len(state.samples) < 10 or not extra_jump[0]):
                    if len(state.samples) == 10:
                        extra_jump[0] = True
                    return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u)]
                if 265 <= state.player.x < 280:
                    return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u)]
            return []

        def held_keys():
            state = games[-1]
            keys = defaultdict(int)
            if len(state.samples) < 10:
                target = state.box.x + 1 if endogeneity_control else 185
                if state.player.x < target - .8:
                    keys[pygame.K_d] = 1
                elif state.player.x > target + .8:
                    keys[pygame.K_a] = 1
            elif extra_jump[0] and state.grounded:
                keys[pygame.K_d] = 1
            elif extra_jump[0] and state.player.x > 240:
                keys[pygame.K_d] = 1
            return keys

        with tempfile.TemporaryDirectory() as folder:
            args = ["game.py", "--scale", "2", "--data-dir", folder]
            with patch.object(sys, "argv", args), \
                 patch.object(app, "Game", side_effect=create_game), \
                 patch.object(pygame.time, "Clock", FastClock), \
                 patch.object(pygame.event, "get", side_effect=events), \
                 patch.object(pygame.key, "get_pressed", side_effect=held_keys):
                app.main()
            self.assertLess(frames[0], 2500, "Game loop failed to finish the scripted playthrough")
            self.assertEqual(len(games), 2, "Restart did not create a new game")
            self.assertTrue(games[0].dead)
            self.assertTrue(extra_jump[0])
            self.assertEqual(len(games[0].samples), 10)
            self.assertEqual(len(games[1].samples), 0)
            self.assertTrue(all(state.binary_control == binary_control for state in games))
            self.assertTrue(all(state.rgb_control == rgb_control for state in games))
            self.assertTrue(all(state.endogeneity_control == endogeneity_control for state in games))
            files = sorted(Path(folder).glob("*.csv"))
            self.assertEqual(len(files), 2)
            lengths = []
            for path in files:
                with path.open(newline="") as saved:
                    rows = list(csv.DictReader(saved))
                    lengths.append(len(rows))
                    if binary_control and rows:
                        self.assertEqual([int(row["binary_variable"]) for row in rows], games[0].binary_samples)
                        self.assertEqual([float(row["outcome"]) for row in rows], games[0].samples)
                    elif rgb_control and rows:
                        self.assertEqual([tuple(int(row[key]) for key in ("R", "G", "B")) for row in rows], games[0].rgb_samples)
                        self.assertEqual([float(row["outcome"]) for row in rows], games[0].samples)
                    elif endogeneity_control and rows:
                        self.assertEqual([(int(row["x"]), int(row["z"])) for row in rows], games[0].endogeneity_samples)
                        self.assertEqual([float(row["y"]) for row in rows], games[0].samples)
            self.assertEqual(sorted(lengths), [0, 10])

    def test_pixel_art_and_overlay_rendering(self):
        pygame.init()
        try:
            self.assertTrue(all(len(row) == 16 for row in app.MARIO))
            sprite = app.make_mario()
            with tempfile.TemporaryDirectory() as folder:
                log = app.SampleLog(Path(folder))
                try:
                    state = Game(log)
                    surface = pygame.Surface((app.WIDTH, app.HEIGHT))
                    app.draw_scene(surface, state, sprite, [])
                    normal_pixel = surface.get_at((36, 84))
                    app.draw_scene(surface, state, sprite, [], paused=True)
                    self.assertNotEqual(surface.get_at((36, 84)), normal_pixel)
                    for _ in range(10):
                        state.hit_box()
                    app.draw_scene(surface, state, sprite, [(state.samples[-1], 0.3, 192)])
                    state.dead = True
                    app.draw_scene(surface, state, sprite, [])
                    app.draw_scene(surface, state, sprite, [], error="disk full")
                finally:
                    log.close()
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
