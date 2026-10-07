"""Physics and CSV storage for the little World 1-1 experiment."""

import csv
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

WIDTH = 384
GROUND_Y = 208
GAP_X = 336
WORLD_BOTTOM = 240
MAX_DRAWS = 10
CONTROL_INTERVAL = 0.2
ENDOGENEITY_BOX_X = (152, 216)
ENDOGENEITY_MEANS = {(0, 0): -1, (1, 0): 1, (0, 1): 1, (1, 1): 2}
PLAYER_W = 13
PLAYER_H = 16
SPEED = 96.0
GRAVITY = 760.0
JUMP_SPEED = 278.0


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    def overlaps_x(self, other):
        return self.x < other.right and self.right > other.x

    def overlaps_y(self, other):
        return self.y < other.bottom and self.bottom > other.y


class SampleLog:
    """One file per attempt; flush each successful hit to disk."""

    def __init__(self, directory: Path, binary_control=False, rgb_control=False, endogeneity_control=False):
        if sum((binary_control, rgb_control, endogeneity_control)) > 1:
            raise ValueError("Choose one control variable scene")
        self.binary_control = binary_control
        self.rgb_control = rgb_control
        self.endogeneity_control = endogeneity_control
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        prefix = "endogeneity_draws_" if endogeneity_control else "rgb_draws_" if rgb_control else "binary_draws_" if binary_control else "draws_"
        name = prefix + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ.csv")
        self.path = directory / name
        self.file = self.path.open("x", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        if endogeneity_control:
            columns = ["hit", "x", "z", "y", "timestamp_utc"]
        elif rgb_control:
            columns = ["hit", "R", "G", "B", "outcome", "timestamp_utc"]
        elif binary_control:
            columns = ["hit", "binary_variable", "outcome", "timestamp_utc"]
        else:
            columns = ["hit", "value", "timestamp_utc"]
        self.writer.writerow(columns)
        self.file.flush()

    def append(self, hit: int, value: float, binary_value=None, rgb_value=None, z_value=None):
        timestamp = datetime.now(timezone.utc).isoformat()
        if self.endogeneity_control:
            if binary_value not in (0, 1) or z_value not in (0, 1):
                raise ValueError("An endogeneity scene hit must include binary x and z")
            self.writer.writerow([hit, binary_value, z_value, repr(value), timestamp])
        elif self.rgb_control:
            if (not isinstance(rgb_value, (tuple, list)) or len(rgb_value) != 3
                    or any(type(channel) is not int or not 0 <= channel <= 255 for channel in rgb_value)):
                raise ValueError("An RGB scene hit needs three integer channels from 0 through 255")
            self.writer.writerow([hit, *rgb_value, repr(value), timestamp])
        elif self.binary_control:
            if binary_value not in (0, 1):
                raise ValueError("A binary scene hit must include a 0 or 1 control value")
            self.writer.writerow([hit, binary_value, repr(value), timestamp])
        else:
            if binary_value is not None or rgb_value is not None or z_value is not None:
                raise ValueError("A control variable hit needs its scene's CSV")
            self.writer.writerow([hit, repr(value), timestamp])
        self.file.flush()
        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


class Game:
    def __init__(self, log: SampleLog, rng=None, binary_control=False, binary_rng=None,
                 rgb_control=False, rgb_rng=None, endogeneity_control=False, endogeneity_rng=None):
        if sum((binary_control, rgb_control, endogeneity_control)) > 1:
            raise ValueError("Choose one control variable scene")
        self.log = log
        self.rng = rng if rng is not None else random.Random()
        self.binary_control = binary_control
        self.rgb_control = rgb_control
        self.endogeneity_control = endogeneity_control
        # Separate generators keep Gaussian noise independent of color draws.
        self.binary_rng = binary_rng if binary_rng is not None else random.Random()
        self.rgb_rng = rgb_rng if rgb_rng is not None else random.Random()
        self.endogeneity_rng = endogeneity_rng if endogeneity_rng is not None else random.Random()
        self.z_value = None
        self.binary_value = self.binary_rng.randint(0, 1) if binary_control else None
        self.rgb_value = self.draw_rgb() if rgb_control else None
        self.control_elapsed = 0.0
        self.binary_samples: List[int] = []
        self.rgb_samples: List[Tuple[int, int, int]] = []
        self.endogeneity_samples: List[Tuple[int, int]] = []
        self.player = Rect(32.0, GROUND_Y - PLAYER_H, PLAYER_W, PLAYER_H)
        self.box = Rect(184, 144, 16, 16)
        self.last_hit_center = 192
        self.bricks = [] if endogeneity_control else [Rect(168, 144, 16, 16), Rect(200, 144, 16, 16)]
        self.pipe = Rect(280, 176, 32, 32)
        self.solids = self.bricks + [self.box, self.pipe]
        self.vine_x = 104
        self.vine_top = 151
        self.vy = 0.0
        self.vx = 0.0
        self.facing = 1
        self.grounded = True
        self.climbing = False
        self.crouching = False
        self.dead = False
        self.samples: List[float] = []
        self.elapsed = 0.0
        self.bump = 0.0
        self.events = []
        if endogeneity_control:
            self.draw_endogeneity_z()
            self.draw_endogeneity_x()

    def draw_rgb(self):
        return tuple(self.rgb_rng.randint(0, 255) for _ in range(3))

    def draw_endogeneity_x(self):
        probability = 0.7 if self.z_value == 1 else 0.3
        self.binary_value = int(self.endogeneity_rng.random() < probability)

    def draw_endogeneity_z(self):
        self.z_value = self.endogeneity_rng.randint(0, 1)
        old_x = self.box.x
        self.box.x = ENDOGENEITY_BOX_X[self.z_value]
        # A box appearing inside Mario must not create a hit or trap him.
        p = self.player
        if old_x != self.box.x and p.overlaps_x(self.box) and p.overlaps_y(self.box):
            if p.y + p.h / 2 < self.box.y + self.box.h / 2:
                p.y = self.box.y - p.h
                self.grounded = True
            else:
                p.y = self.box.bottom
                self.grounded = False
            self.vy = 0.0

    @property
    def outcome_mean(self):
        if self.endogeneity_control:
            return ENDOGENEITY_MEANS[(self.binary_value, self.z_value)]
        if self.rgb_control:
            return sum(self.rgb_value)
        return self.binary_value if self.binary_control else 0

    def hit_box(self) -> Optional[float]:
        self.bump = 0.16
        if len(self.samples) >= MAX_DRAWS:
            self.events.append(("empty", None))
            return None
        control_value = self.binary_value if self.binary_control or self.endogeneity_control else None
        z_value = self.z_value if self.endogeneity_control else None
        rgb_value = self.rgb_value if self.rgb_control else None
        if self.rgb_control:
            value = sum(rgb_value) + self.rng.gauss(0.0, 1.0)
        else:
            value = self.rng.gauss(float(self.outcome_mean), 1.0)
        # Only count a hit after its row has been successfully saved.
        if self.endogeneity_control:
            self.log.append(len(self.samples) + 1, value, binary_value=control_value, z_value=z_value)
            self.endogeneity_samples.append((control_value, z_value))
        elif self.rgb_control:
            self.log.append(len(self.samples) + 1, value, rgb_value=rgb_value)
            self.rgb_samples.append(rgb_value)
        elif self.binary_control:
            self.log.append(len(self.samples) + 1, value, binary_value=control_value)
            self.binary_samples.append(control_value)
        else:
            self.log.append(len(self.samples) + 1, value)
        self.samples.append(value)
        self.last_hit_center = int(self.box.x + self.box.w / 2)
        self.events.append(("sample", value))
        if self.endogeneity_control and len(self.samples) < MAX_DRAWS:
            self.draw_endogeneity_z()
        return value

    def update(self, dt, horizontal=0, vertical=0, jump=False):
        if self.dead:
            return
        self.elapsed += dt
        self.bump = max(0.0, self.bump - dt)
        if (self.binary_control or self.rgb_control or self.endogeneity_control) and len(self.samples) < MAX_DRAWS:
            self.control_elapsed += dt
            while self.control_elapsed + 1e-12 >= CONTROL_INTERVAL:
                self.control_elapsed = max(0.0, self.control_elapsed - CONTROL_INTERVAL)
                if self.endogeneity_control:
                    self.draw_endogeneity_x()
                elif self.rgb_control:
                    self.rgb_value = self.draw_rgb()
                else:
                    self.binary_value = self.binary_rng.randint(0, 1)
        p = self.player
        # S crouches on the ground; release it to stand when there is headroom.
        crouch = vertical > 0 and self.grounded and not self.climbing
        height = 12 if crouch else PLAYER_H
        standing = Rect(p.x, p.bottom - height, p.w, height)
        blocked = any(standing.overlaps_x(s) and standing.overlaps_y(s) for s in self.solids)
        if height < p.h or not blocked:
            p.y, p.h = standing.y, height
        self.crouching = p.h < PLAYER_H

        near_vine = abs(p.x + p.w / 2 - self.vine_x) <= 11
        at_vine_height = p.bottom >= self.vine_top and p.y < GROUND_Y
        if vertical and near_vine and at_vine_height and not jump:
            self.climbing = True
        if not near_vine:
            self.climbing = False
        if jump and (self.grounded or self.climbing):
            self.vy = -JUMP_SPEED
            self.grounded = False
            self.climbing = False
            self.events.append(("jump", None))

        self.vx = horizontal * SPEED * (0.5 if self.crouching else 1.0)
        if horizontal:
            self.facing = 1 if horizontal > 0 else -1
        old_x = p.x
        p.x = max(0.0, min(WIDTH - p.w, p.x + self.vx * dt))
        for solid in self.solids:
            if not p.overlaps_y(solid):
                continue
            if self.vx > 0 and old_x + p.w <= solid.x and p.right > solid.x:
                p.x = solid.x - p.w
            elif self.vx < 0 and old_x >= solid.right and p.x < solid.right:
                p.x = solid.right

        if self.climbing:
            self.vy = 0.0
            p.y = max(self.vine_top - p.h, min(GROUND_Y - p.h, p.y + vertical * 68 * dt))
            self.grounded = p.bottom >= GROUND_Y
            if self.grounded and vertical > 0:
                self.climbing = False
            return

        old_y = p.y
        self.vy += GRAVITY * dt
        # S also lets the player descend more quickly in the air.
        if vertical > 0 and self.vy > 0:
            self.vy += GRAVITY * dt
        p.y += self.vy * dt
        self.grounded = False
        for solid in self.solids:
            if not p.overlaps_x(solid):
                continue
            if self.vy < 0 and old_y >= solid.bottom and p.y <= solid.bottom:
                p.y = solid.bottom
                self.vy = 0.0
                if solid is self.box:
                    self.hit_box()
                else:
                    self.events.append(("bump", None))
            elif self.vy >= 0 and old_y + p.h <= solid.y and p.bottom >= solid.y:
                p.y = solid.y - p.h
                self.vy = 0.0
                self.grounded = True

        if p.x < GAP_X and self.vy >= 0 and old_y + p.h <= GROUND_Y and p.bottom >= GROUND_Y:
            p.y = GROUND_Y - p.h
            self.vy = 0.0
            self.grounded = True
        if p.y > WORLD_BOTTOM + PLAYER_H:
            self.dead = True
            self.events.append(("death", None))
