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
BEATMAP_FILENAME = "happy_end_of_the_world.osu"

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
        1: {"columns": [3, 4], "color": GREEN},
        2: {"columns": [6, 7], "color": BLUE},
        3: {"columns": [9, 10], "color": CYAN},
    },
    5: {
        0: {"columns": [0], "color": PURPLE},
        1: {"columns": [2], "color": GREEN},
        2: {"columns": [5], "color": RED},
        3: {"columns": [7], "color": BLUE},
        4: {"columns": [9], "color": CYAN},
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
    time: int
    start_time: int | None
    visible_notes: list
    hitobjects_buffer: list

    def __init__(self, beatmap):
        self.beatmap = beatmap
        self.time = 0
        self.visible_notes = []
        self.hitobjects_buffer = []

    def _get_key_info(self, key):
        return keys_settings[self.beatmap.keys][key]

    def render(self):
        while True:
            if self.start_time is None:
                raise ValueError("Gameplay has not started yet")

            graphics.set_pen(BLACK)
            graphics.clear()

            current_time = time.ticks_ms() - self.start_time
            frame_time = current_time - self.time
            self.time = current_time

            for hitobject in self.hitobjects_buffer:
                if hitobject.time > current_time:
                    break
                self.visible_notes.append(
                    {"key": hitobject.key, "scroll": GalacticUnicorn.WIDTH}
                )
                self.hitobjects_buffer.remove(hitobject)

            for note in self.visible_notes:
                key_info = self._get_key_info(note["key"])
                graphics.set_pen(key_info["color"])
                note["scroll"] -= frame_time / SCROLL_TIME * GalacticUnicorn.WIDTH
                if note["scroll"] < 0:
                    self.visible_notes.remove(note)
                for column in key_info["columns"]:
                    graphics.pixel(floor(note["scroll"]), column)

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
