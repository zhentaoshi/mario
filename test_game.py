"""Run with python3 -m unittest -v test_game (no Pygame needed)."""

import csv
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import Mock

from game_logic import Game, SampleLog, GROUND_Y, GAP_X, MAX_DRAWS, PLAYER_H, ENDOGENEITY_BOX_X

STEP = 1 / 120


class GameTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.log = SampleLog(Path(self.folder.name))
        self.game = Game(self.log, random.Random(12345))

    def tearDown(self):
        self.log.close()
        self.folder.cleanup()

    def rows(self):
        with self.log.path.open(newline="") as saved:
            return list(csv.DictReader(saved))

    def jump_and_land(self):
        self.game.update(STEP, jump=True)
        for _ in range(200):
            self.game.update(STEP)
            if self.game.grounded:
                return
        self.fail("Mario did not land")

    def test_ten_real_head_collisions_and_no_eleventh_draw(self):
        self.game.player.x = 185
        for count in range(1, MAX_DRAWS + 1):
            self.jump_and_land()
            self.assertEqual(len(self.game.samples), count)
            self.assertEqual(len(self.rows()), count)
        before = self.log.path.read_bytes()
        self.jump_and_land()
        self.assertEqual(len(self.game.samples), MAX_DRAWS)
        self.assertEqual(self.log.path.read_bytes(), before)

    def test_values_are_seeded_standard_normal_draws_with_full_precision(self):
        expected_rng = random.Random(12345)
        for _ in range(MAX_DRAWS):
            self.game.hit_box()
        saved = self.rows()
        self.assertEqual([float(row["value"]) for row in saved],
                         [expected_rng.gauss(0.0, 1.0) for _ in range(MAX_DRAWS)])
        self.assertEqual([int(row["hit"]) for row in saved], list(range(1, 11)))
        self.assertTrue(all(row["timestamp_utc"].endswith("+00:00") for row in saved))

    def test_unaligned_jump_and_side_collision_do_not_dispense(self):
        self.jump_and_land()
        self.game.player.x = 150
        self.game.player.y = 147
        self.game.vy = 0
        self.game.grounded = False
        for _ in range(10):
            self.game.update(STEP, horizontal=1)
        self.assertEqual(self.game.samples, [])
        self.assertLessEqual(self.game.player.right, 168)

    def test_landing_on_box_does_not_dispense(self):
        self.game.player.x = 185
        self.game.player.y = 110
        self.game.grounded = False
        for _ in range(60):
            self.game.update(STEP)
        self.assertTrue(self.game.grounded)
        self.assertEqual(self.game.player.bottom, self.game.box.y)
        self.assertEqual(self.game.samples, [])

    def test_ground_and_pipe_are_solid_and_pipe_is_jumpable(self):
        for _ in range(330):
            self.game.update(STEP, horizontal=1)
        self.assertAlmostEqual(self.game.player.right, self.game.pipe.x)
        self.assertEqual(self.game.player.bottom, GROUND_Y)
        self.game.update(STEP, jump=True)
        for _ in range(100):
            self.game.update(STEP, horizontal=1)
        self.assertGreater(self.game.player.x, self.game.pipe.right)
        self.assertFalse(self.game.dead)

    def test_fall_into_right_gap_ends_game_and_freezes_movement(self):
        self.game.player.x = GAP_X - 3
        for _ in range(200):
            self.game.update(STEP, horizontal=1)
        self.assertTrue(self.game.dead)
        before = (self.game.player.x, self.game.player.y)
        self.game.update(1.0, horizontal=-1, vertical=-1, jump=True)
        self.assertEqual(before, (self.game.player.x, self.game.player.y))

    def test_vine_up_down_and_jump_off(self):
        self.game.player.x = self.game.vine_x - self.game.player.w / 2
        for _ in range(40):
            self.game.update(STEP, vertical=-1)
        self.assertTrue(self.game.climbing)
        climbed_y = self.game.player.y
        self.assertLess(climbed_y, GROUND_Y - PLAYER_H)
        for _ in range(10):
            self.game.update(STEP, vertical=1)
        self.assertGreater(self.game.player.y, climbed_y)
        self.game.update(STEP, jump=True)
        self.assertFalse(self.game.climbing)
        self.assertLess(self.game.vy, 0)

    def test_crouch_preserves_feet_and_standing_restores_height(self):
        self.game.update(STEP, vertical=1)
        self.assertTrue(self.game.crouching)
        self.assertEqual(self.game.player.bottom, GROUND_Y)
        self.game.update(STEP)
        self.assertFalse(self.game.crouching)
        self.assertEqual(self.game.player.h, PLAYER_H)
        self.assertEqual(self.game.player.bottom, GROUND_Y)

    def test_new_game_keeps_previous_csv(self):
        self.game.hit_box()
        original = self.log.path.read_bytes()
        second = SampleLog(Path(self.folder.name))
        try:
            self.assertNotEqual(second.path, self.log.path)
            self.assertEqual(len(Game(second).samples), 0)
            self.assertEqual(self.log.path.read_bytes(), original)
        finally:
            second.close()

    def test_save_failure_does_not_count_hit(self):
        class BrokenLog:
            def append(self, hit, value):
                raise OSError("disk full")
        game = Game(BrokenLog())
        with self.assertRaises(OSError):
            game.hit_box()
        self.assertEqual(game.samples, [])


class BinaryGameTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.log = SampleLog(Path(self.folder.name), binary_control=True)
        self.game = Game(self.log, rng=random.Random(12345), binary_control=True,
                         binary_rng=random.Random(7))

    def tearDown(self):
        self.log.close()
        self.folder.cleanup()

    def rows(self):
        with self.log.path.open(newline="") as saved:
            return list(csv.DictReader(saved))

    def test_initial_draw_and_exact_point_two_second_intervals(self):
        binary_rng = Mock()
        binary_rng.randint.side_effect = [0, 1, 0, 1]
        game = Game(self.log, binary_control=True, binary_rng=binary_rng)
        self.assertEqual(game.binary_value, 0)
        self.assertEqual(binary_rng.randint.call_count, 1)
        for _ in range(23):
            game.update(STEP)
        self.assertEqual(game.binary_value, 0)
        self.assertEqual(binary_rng.randint.call_count, 1)
        game.update(STEP)
        self.assertEqual(game.binary_value, 1)
        game.update(.1)
        self.assertEqual(game.binary_value, 1)
        game.update(.1)
        self.assertEqual(game.binary_value, 0)
        game.update(.2)
        self.assertEqual(game.binary_value, 1)
        self.assertEqual(binary_rng.randint.call_count, 4)
        self.assertTrue(all(call.args == (0, 1) for call in binary_rng.randint.call_args_list))
        self.assertEqual(self.rows(), [], "Color redraws must not create hit rows")

    def test_ten_real_hits_save_paired_values_and_empty_box_stops_draws(self):
        self.game.player.x = 185
        for count in range(1, 11):
            self.game.update(STEP, jump=True)
            for _ in range(200):
                self.game.update(STEP)
                if any(name == "sample" for name, value in self.game.events):
                    self.assertEqual(self.game.binary_samples[-1], self.game.binary_value)
                self.game.events.clear()
                if self.game.grounded:
                    break
            self.assertEqual(len(self.rows()), count)
        saved = self.rows()
        self.assertEqual(list(saved[0]), ["hit", "binary_variable", "outcome", "timestamp_utc"])
        self.assertEqual([int(row["binary_variable"]) for row in saved], self.game.binary_samples)
        expected_rng = random.Random(12345)
        self.assertEqual([float(row["outcome"]) for row in saved],
                         [expected_rng.gauss(float(row["binary_variable"]), 1.0) for row in saved])
        self.assertEqual([int(row["hit"]) for row in saved], list(range(1, 11)))
        frozen_binary = self.game.binary_value
        before = self.log.path.read_bytes()
        self.game.hit_box()
        self.game.update(1.0)
        self.assertEqual(len(self.game.samples), 10)
        self.assertEqual(self.game.binary_value, frozen_binary)
        self.assertEqual(self.log.path.read_bytes(), before)

    def test_record_uses_hit_time_value_not_later_color(self):
        self.game.binary_value = 1
        self.game.hit_box()
        self.game.binary_value = 0
        self.game.hit_box()
        self.assertEqual([int(row["binary_variable"]) for row in self.rows()], [1, 0])
        self.assertEqual(self.game.binary_samples, [1, 0])
        expected_rng = random.Random(12345)
        self.assertEqual([float(row["outcome"]) for row in self.rows()],
                         [expected_rng.gauss(1.0, 1.0), expected_rng.gauss(0.0, 1.0)])

    def test_death_stops_binary_timer(self):
        self.game.dead = True
        value, timer = self.game.binary_value, self.game.control_elapsed
        self.game.update(1.0)
        self.assertEqual((self.game.binary_value, self.game.control_elapsed), (value, timer))


class RgbGameTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.log = SampleLog(Path(self.folder.name), rgb_control=True)
        self.game = Game(self.log, rng=random.Random(12345), rgb_control=True,
                         rgb_rng=random.Random(7))

    def tearDown(self):
        self.log.close()
        self.folder.cleanup()

    def rows(self):
        with self.log.path.open(newline="") as saved:
            return list(csv.DictReader(saved))

    def test_three_uniform_draws_on_entry_and_every_point_two_seconds(self):
        rgb_rng = Mock()
        rgb_rng.randint.side_effect = [0, 255, 127, 200, 3, 57, 55, 88, 20]
        game = Game(self.log, rgb_control=True, rgb_rng=rgb_rng)
        self.assertEqual(game.rgb_value, (0, 255, 127))
        self.assertEqual(rgb_rng.randint.call_count, 3)
        for _ in range(23):
            game.update(STEP)
        self.assertEqual(rgb_rng.randint.call_count, 3)
        game.update(STEP)
        self.assertEqual(game.rgb_value, (200, 3, 57))
        game.update(.2)
        self.assertEqual(game.rgb_value, (55, 88, 20))
        self.assertEqual(rgb_rng.randint.call_count, 9)
        self.assertTrue(all(call.args == (0, 255) for call in rgb_rng.randint.call_args_list))
        self.assertEqual(self.rows(), [], "Color redraws must not add hit rows")

    def test_ten_real_hits_save_rgb_plus_normal_noise_and_stop_when_empty(self):
        self.game.player.x = 185
        for count in range(1, 11):
            self.game.update(STEP, jump=True)
            for _ in range(200):
                self.game.update(STEP)
                if any(name == "sample" for name, value in self.game.events):
                    self.assertEqual(self.game.rgb_samples[-1], self.game.rgb_value)
                self.game.events.clear()
                if self.game.grounded:
                    break
            self.assertEqual(len(self.rows()), count)
        rows = self.rows()
        self.assertEqual(list(rows[0]), ["hit", "R", "G", "B", "outcome", "timestamp_utc"])
        self.assertEqual([tuple(int(row[key]) for key in ("R", "G", "B")) for row in rows], self.game.rgb_samples)
        expected_rng = random.Random(12345)
        self.assertEqual([float(row["outcome"]) for row in rows],
                         [sum(channels) + expected_rng.gauss(0.0, 1.0) for channels in self.game.rgb_samples])
        self.assertEqual([int(row["hit"]) for row in rows], list(range(1, 11)))
        self.assertTrue(all(0 <= channel <= 255 for channels in self.game.rgb_samples for channel in channels))
        before = self.log.path.read_bytes()
        channels = self.game.rgb_value
        color_rng_state = self.game.rgb_rng.getstate()
        noise_rng_state = self.game.rng.getstate()
        self.game.hit_box()
        self.game.update(1.0)
        self.assertEqual(self.log.path.read_bytes(), before)
        self.assertEqual(self.game.rgb_value, channels)
        self.assertEqual(self.game.rgb_rng.getstate(), color_rng_state)
        self.assertEqual(self.game.rng.getstate(), noise_rng_state)

    def test_hit_time_channels_and_unclipped_outcomes(self):
        expected_rng = random.Random(12345)
        self.game.rgb_value = (0, 0, 0)
        first = self.game.hit_box()
        self.game.rgb_value = (255, 255, 255)
        second = self.game.hit_box()
        self.game.rgb_value = (10, 20, 30)
        rows = self.rows()
        self.assertEqual(self.game.rgb_samples, [(0, 0, 0), (255, 255, 255)])
        self.assertEqual(first, expected_rng.gauss(0.0, 1.0))
        self.assertEqual(second, 765 + expected_rng.gauss(0.0, 1.0))
        self.assertLess(first, 0)
        self.assertGreater(second, 765)
        self.assertEqual([tuple(int(row[key]) for key in ("R", "G", "B")) for row in rows], self.game.rgb_samples)
        self.assertEqual([float(row["outcome"]) for row in rows], [first, second])

    def test_failed_save_and_death_do_not_add_samples_or_redraw_colors(self):
        broken = Mock()
        broken.append.side_effect = OSError("disk full")
        game = Game(broken, rgb_control=True)
        with self.assertRaises(OSError):
            game.hit_box()
        self.assertEqual(game.samples, [])
        self.assertEqual(game.rgb_samples, [])
        game.dead = True
        before = game.rgb_value, game.control_elapsed
        game.update(1.0)
        self.assertEqual((game.rgb_value, game.control_elapsed), before)


class EndogeneityGameTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.log = SampleLog(Path(self.folder.name), endogeneity_control=True)
        self.game = Game(self.log, rng=random.Random(12345), endogeneity_control=True,
                         endogeneity_rng=random.Random(123))

    def tearDown(self):
        self.log.close()
        self.folder.cleanup()

    def rows(self):
        with self.log.path.open(newline="") as saved:
            return list(csv.DictReader(saved))

    def test_conditional_probabilities_and_two_box_locations(self):
        for z, uniform, expected_x in [(1, .699999, 1), (1, .7, 0),
                                        (0, .299999, 1), (0, .3, 0)]:
            with self.subTest(z=z, uniform=uniform):
                controls = Mock()
                controls.randint.return_value = z
                controls.random.return_value = uniform
                game = Game(self.log, endogeneity_control=True, endogeneity_rng=controls)
                self.assertEqual((game.binary_value, game.z_value), (expected_x, z))
                self.assertEqual(game.box.x, ENDOGENEITY_BOX_X[z])
                self.assertEqual(len([solid for solid in game.solids if solid is game.box]), 1)
                controls.randint.assert_called_once_with(0, 1)
                controls.random.assert_called_once_with()

    def test_four_conditional_outcomes_and_csv_snapshots(self):
        expected_rng = random.Random(12345)
        cases = [(1, 1, 2), (0, 1, 1), (1, 0, 1), (0, 0, -1)]
        expected_y = []
        for x, z, mean in cases:
            self.game.binary_value, self.game.z_value = x, z
            self.assertEqual(self.game.outcome_mean, mean)
            expected = expected_rng.gauss(float(mean), 1.0)
            expected_y.append(expected)
            self.assertEqual(self.game.hit_box(), expected)
        self.game.binary_value, self.game.z_value = 1, 1
        rows = self.rows()
        self.assertEqual(list(rows[0]), ["hit", "x", "z", "y", "timestamp_utc"])
        self.assertEqual([(int(row["x"]), int(row["z"])) for row in rows], [(x, z) for x, z, mean in cases])
        self.assertEqual([float(row["y"]) for row in rows], expected_y)

    def test_x_timer_and_z_redraw_only_after_hits(self):
        controls = Mock()
        controls.randint.side_effect = [0, 1, 0]
        controls.random.side_effect = [.5, .5, .2]
        game = Game(self.log, endogeneity_control=True, endogeneity_rng=controls)
        self.assertEqual((game.binary_value, game.z_value), (0, 0))
        for _ in range(23):
            game.update(STEP)
        self.assertEqual(controls.randint.call_count, 1)
        self.assertEqual(controls.random.call_count, 1)
        timer = game.control_elapsed
        game.hit_box()
        self.assertEqual((game.binary_value, game.z_value), (0, 1))
        self.assertEqual(game.endogeneity_samples, [(0, 0)])
        self.assertEqual(game.control_elapsed, timer)
        self.assertEqual(controls.random.call_count, 1, "A hit must not add an X redraw")
        game.update(STEP)
        self.assertEqual((game.binary_value, game.z_value), (1, 1))
        self.assertEqual(game.box.x, ENDOGENEITY_BOX_X[1])
        game.update(.2)
        self.assertEqual((game.binary_value, game.z_value), (1, 1))
        self.assertEqual(controls.randint.call_count, 2, "Timed draws must not change Z")
        self.assertEqual(controls.random.call_count, 3)
        self.assertEqual(len(self.rows()), 1, "Timed color redraws must not create rows")

    def test_ten_real_hits_then_empty_box_freezes_location_and_csv(self):
        for count in range(1, 11):
            old_z = self.game.z_value
            old_center = int(self.game.box.x + self.game.box.w / 2)
            self.game.player.x = self.game.box.x + 1
            self.game.update(STEP, jump=True)
            for _ in range(200):
                self.game.update(STEP)
                if any(name == "sample" for name, value in self.game.events):
                    self.assertEqual(self.game.endogeneity_samples[-1], (self.game.binary_value, old_z))
                    self.assertEqual(self.game.last_hit_center, old_center)
                self.game.events.clear()
                if self.game.grounded:
                    break
            self.assertEqual(len(self.game.samples), count)
        self.assertEqual(len(self.game.samples), 10)
        rows = self.rows()
        self.assertEqual(len(rows), 10)
        expected_rng = random.Random(12345)
        means = {(0, 0): -1, (1, 0): 1, (0, 1): 1, (1, 1): 2}
        self.assertEqual([float(row["y"]) for row in rows],
                         [expected_rng.gauss(float(means[(int(row["x"]), int(row["z"]))]), 1.0) for row in rows])
        before = self.log.path.read_bytes()
        state = self.game.box.x, self.game.binary_value, self.game.z_value
        controls_state = self.game.endogeneity_rng.getstate()
        self.game.hit_box()
        for _ in range(120):
            self.game.update(STEP)
        self.assertEqual(self.log.path.read_bytes(), before)
        self.assertEqual((self.game.box.x, self.game.binary_value, self.game.z_value), state)
        self.assertEqual(self.game.endogeneity_rng.getstate(), controls_state)

    def test_moving_box_resolves_overlap_without_counting_a_hit(self):
        controls = Mock()
        controls.randint.side_effect = [1, 0]
        controls.random.return_value = .5
        game = Game(self.log, endogeneity_control=True, endogeneity_rng=controls)
        game.player.x, game.player.y = ENDOGENEITY_BOX_X[0], 150
        game.vy = -80
        game.grounded = False
        game.draw_endogeneity_z()
        self.assertFalse(game.player.overlaps_x(game.box) and game.player.overlaps_y(game.box))
        self.assertEqual(game.samples, [])
        self.assertEqual(game.events, [])
        self.assertEqual(self.rows(), [])


if __name__ == "__main__":
    unittest.main()
