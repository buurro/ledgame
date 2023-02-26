import _thread
from collections import namedtuple
from math import floor

import machine
import utime as time
from galactic import GalacticUnicorn
from picographics import DISPLAY_GALACTIC_UNICORN, PicoGraphics

SCROLL_TIME = 750  # time in ms for a note to scroll across the screen
BRIGHTNESS = 0.5
HIT_OBJECTS_BUFFER_SIZE = 200  # number of hitobjects to buffer
BEATMAP_FILENAME = "blue_rose.osu"

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)
# create our GalacticUnicorn object
gu = GalacticUnicorn()

BLACK = graphics.create_pen(0, 0, 0)
PURPLE = graphics.create_pen(255, 0, 255)
GREEN = graphics.create_pen(0, 255, 0)
BLUE = graphics.create_pen(0, 0, 255)
CYAN = graphics.create_pen(0, 255, 255)
RED = graphics.create_pen(255, 0, 0)

keys_settings = {
    4: {
        0: {"columns": [0, 1], "color": PURPLE},
        1: {"columns": [3, 4], "color": BLUE},
        2: {"columns": [6, 7], "color": BLUE},
        3: {"columns": [9, 10], "color": PURPLE},
    },
    5: {
        0: {"columns": [0], "color": PURPLE},
        1: {"columns": [2], "color": BLUE},
        2: {"columns": [5], "color": RED},
        3: {"columns": [7], "color": BLUE},
        4: {"columns": [9], "color": PURPLE},
    },
}

machine.freq(200000000)
gu.set_brightness(BRIGHTNESS)


HitObject = namedtuple("HitObject", ["key", "time"])


class Beatmap:
    filename: str
    keys: int

    def __init__(self, filename):
        self.filename = filename
        self._parse_keys_number()
        self.hitobjects = self._get_hitobjects()

    def _parse_keys_number(self):
        with open(self.filename, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    raise ValueError("No keys found in beatmap")

                if line.startswith("CircleSize:"):
                    self.keys = int(line.split(":")[1])
                    break

    def _get_hitobjects(self):
        hitobjects_section = False
        with open(self.filename, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break

                if not hitobjects_section:
                    if line.startswith("[HitObjects]"):
                        hitobjects_section = True
                    continue

                line = line.strip().split(",")
                key = (int(line[0]) - 64) // 128
                key = floor(int(line[0]) / (512 / self.keys))
                hit_time = int(line[2])

                hitobject = HitObject(key, hit_time)

                yield hitobject


class Gameplay:
    beatmap: Beatmap
    time = 0
    start_time: int | None
    visible_hitobjects: list[HitObject] = []
    hitobjects_buffer: list[HitObject] = []

    def __init__(self, beatmap):
        self.beatmap = beatmap

    def _get_key_info(self, key):
        return keys_settings[self.beatmap.keys][key]

    def render(self):
        while True:
            if self.start_time is None:
                raise ValueError("Gameplay has not started yet")

            graphics.set_pen(BLACK)
            graphics.clear()

            current_time = time.ticks_ms() - self.start_time
            self.time = current_time

            for hitobject in self.hitobjects_buffer:
                if hitobject.time > current_time + SCROLL_TIME:
                    break

                self.visible_hitobjects.append(hitobject)
                self.hitobjects_buffer.remove(hitobject)

            for hitobject in self.visible_hitobjects:
                key_info = self._get_key_info(hitobject.key)
                graphics.set_pen(key_info["color"])
                scroll = (
                    (hitobject.time - current_time)
                    * GalacticUnicorn.WIDTH
                    / SCROLL_TIME
                )
                if scroll < 0:
                    self.visible_hitobjects.remove(hitobject)
                for column in key_info["columns"]:
                    graphics.pixel(floor(scroll), column)

            gu.update(graphics)

    def start(self):
        self.start_time = time.ticks_ms()
        _thread.start_new_thread(self.render, ())
        for hitobject in self.beatmap.hitobjects:
            while len(self.hitobjects_buffer) >= HIT_OBJECTS_BUFFER_SIZE:
                time.sleep_ms(50)
            self.hitobjects_buffer.append(hitobject)


beatmap = Beatmap(BEATMAP_FILENAME)
gameplay = Gameplay(beatmap)

gameplay.start()
