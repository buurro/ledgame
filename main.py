import _thread
from collections import namedtuple
from math import floor

import machine
import utime as time
from galactic import GalacticUnicorn
from picographics import DISPLAY_GALACTIC_UNICORN, PicoGraphics

SCROLL_TIME = 1000  # time in ms for a note to scroll across the screen
BRIGHTNESS = 0.5
HITOBJECTS_BUFFER_SIZE = 150  # number of hitobjects to buffer
BEATMAP_FILENAME = "happy_end_9k.osu"

KeySettings = namedtuple("KeySettings", ["color", "columns", "gu_key"])
HitObject = namedtuple("HitObject", ["key", "time"])

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
WHITE = graphics.create_pen(255, 255, 255)

keys_settings = {
    4: {
        0: KeySettings(PURPLE, columns=[0, 1], gu_key=GalacticUnicorn.SWITCH_A),
        1: KeySettings(BLUE, columns=[3, 4], gu_key=GalacticUnicorn.SWITCH_B),
        2: KeySettings(BLUE, columns=[6, 7], gu_key=GalacticUnicorn.SWITCH_C),
        3: KeySettings(PURPLE, columns=[9, 10], gu_key=GalacticUnicorn.SWITCH_D),
    },
    5: {
        0: KeySettings(PURPLE, columns=[0], gu_key=GalacticUnicorn.SWITCH_A),
        1: KeySettings(BLUE, columns=[2], gu_key=GalacticUnicorn.SWITCH_A),
        2: KeySettings(RED, columns=[5], gu_key=GalacticUnicorn.SWITCH_A),
        3: KeySettings(BLUE, columns=[8], gu_key=GalacticUnicorn.SWITCH_A),
        4: KeySettings(PURPLE, columns=[10], gu_key=GalacticUnicorn.SWITCH_A),
    },
    9: {
        0: KeySettings(PURPLE, columns=[0], gu_key=GalacticUnicorn.SWITCH_A),
        1: KeySettings(BLUE, columns=[1], gu_key=GalacticUnicorn.SWITCH_A),
        2: KeySettings(PURPLE, columns=[2], gu_key=GalacticUnicorn.SWITCH_A),
        3: KeySettings(BLUE, columns=[3], gu_key=GalacticUnicorn.SWITCH_A),
        4: KeySettings(RED, columns=[5], gu_key=GalacticUnicorn.SWITCH_A),
        5: KeySettings(BLUE, columns=[7], gu_key=GalacticUnicorn.SWITCH_A),
        6: KeySettings(PURPLE, columns=[8], gu_key=GalacticUnicorn.SWITCH_A),
        7: KeySettings(BLUE, columns=[9], gu_key=GalacticUnicorn.SWITCH_A),
        8: KeySettings(PURPLE, columns=[10], gu_key=GalacticUnicorn.SWITCH_A),
    },
}

machine.freq(200_000_000)
gu.set_brightness(BRIGHTNESS)


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
                key = floor(int(line[0]) / (512 / self.keys))
                hit_time = int(line[2])

                hitobject = HitObject(key, hit_time)

                yield hitobject


class Gameplay:
    beatmap: Beatmap
    start_time: int | None = None
    time = 0
    combo = 0
    hitobjects: list[HitObject] = []
    hitobjects_in_range: dict[int, list[HitObject]] = {}
    keypress_states: dict[int, bool] = {}

    def __init__(self, beatmap):
        self.beatmap = beatmap
        for key in range(self.beatmap.keys):
            self.hitobjects_in_range[key] = []
            self.keypress_states[key] = False

    def _get_key_info(self, key):
        return keys_settings[self.beatmap.keys][key]

    def _render(self):
        while True:
            if self.start_time is None:
                raise ValueError("Gameplay has not started yet")

            graphics.set_pen(BLACK)
            graphics.clear()

            graphics.set_pen(WHITE)
            graphics.text(str(self.combo), 30, 3, scale=0.5)

            current_time = time.ticks_ms() - self.start_time
            self.time = current_time

            for hitobject in self.hitobjects:
                if hitobject.time > current_time + SCROLL_TIME:
                    break
                remaining_time = hitobject.time - current_time
                if remaining_time < -200:
                    self.hitobjects.remove(hitobject)
                    self.hitobjects_in_range[hitobject.key].remove(hitobject)
                    self.combo = 0
                    continue
                if (
                    remaining_time < 200
                    and hitobject not in self.hitobjects_in_range[hitobject.key]
                ):
                    self.hitobjects_in_range[hitobject.key].append(hitobject)

                scroll = remaining_time * GalacticUnicorn.WIDTH / SCROLL_TIME

                key_info = self._get_key_info(hitobject.key)
                graphics.set_pen(key_info.color)
                for column in key_info.columns:
                    graphics.pixel(floor(scroll), column)

            for key in range(self.beatmap.keys):
                key_info = self._get_key_info(key)
                graphics.set_pen(key_info.color)
                for column in key_info.columns:
                    graphics.pixel(0, column)
                if gu.is_pressed(key_info.gu_key):
                    graphics.set_pen(RED)
                    for column in key_info.columns:
                        graphics.pixel(0, column)

                    if not self.keypress_states[key]:
                        self.keypress_states[key] = True
                        if self.hitobjects_in_range[key]:
                            hitobject = self.hitobjects_in_range[key].pop(0)
                            self.hitobjects.remove(hitobject)
                            self.combo += 1
                else:
                    self.keypress_states[key] = False

            gu.update(graphics)

    def start(self):
        self.start_time = time.ticks_ms()
        _thread.start_new_thread(self._render, ())
        for hitobject in self.beatmap.hitobjects:
            while len(self.hitobjects) >= HITOBJECTS_BUFFER_SIZE:
                time.sleep_ms(50)
            self.hitobjects.append(hitobject)


beatmap = Beatmap(BEATMAP_FILENAME)
gameplay = Gameplay(beatmap)

gameplay.start()
