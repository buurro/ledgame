from collections import namedtuple
from math import floor

import machine
import utime as time
from galactic import GalacticUnicorn
from picographics import DISPLAY_GALACTIC_UNICORN, PicoGraphics

# overclock to 200Mhz
machine.freq(200000000)

# create a PicoGraphics framebuffer to draw into
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

# create our GalacticUnicorn object
gu = GalacticUnicorn()
gu.set_brightness(1)

# pen colours to draw with
BLACK = graphics.create_pen(0, 0, 0)
PURPLE = graphics.create_pen(255, 0, 255)
GREEN = graphics.create_pen(0, 255, 0)
BLUE = graphics.create_pen(0, 0, 255)
CYAN = graphics.create_pen(0, 255, 255)
RED = graphics.create_pen(255, 0, 0)

notes = []

HitObject = namedtuple("HitObject", ["key", "time"])

SPACING = 55
SPEED = 123


def get_hitobjects():
    with open("blue_rose.osu", "r") as f:
        hitobjects_section = False
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
            hit_time = int(line[2])

            hitobject = HitObject(key, hit_time)

            yield hitobject


keys_settings = {
    0: {"columns": [0, 1], "color": PURPLE},
    1: {"columns": [3, 4], "color": GREEN},
    2: {"columns": [6, 7], "color": BLUE},
    3: {"columns": [9, 10], "color": CYAN},
}


def tick():
    global notes
    graphics.set_pen(BLACK)
    graphics.clear()

    for note in notes:
        graphics.set_pen(keys_settings[note["key"]]["color"])
        note["scroll"] -= SPEED / 1000
        if note["scroll"] < 0:
            notes.remove(note)
        for column in keys_settings[note["key"]]["columns"]:
            graphics.pixel(floor(note["scroll"]), column)

    gu.update(graphics)


hitobjects = get_hitobjects()
curr_time = 0

# start = time.ticks_ms()

while True:
    next_hitobject = next(hitobjects)

    while abs(curr_time - next_hitobject.time) > 100 / SPACING:
        tick()
        curr_time += 100 / SPACING
        # time.sleep(0.001)

    hitobject = next_hitobject

    notes.append({"scroll": GalacticUnicorn.WIDTH, "key": hitobject.key})
