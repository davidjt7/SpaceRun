from kivy.config import Config

Config.set("graphics", "width", "900")
Config.set("graphics", "height", "400")

from kivy import platform
from kivy.app import App
from kivy.uix.relativelayout import RelativeLayout
from kivy.core.window import Window
from kivy.properties import NumericProperty, Clock, ObjectProperty, StringProperty
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Line, Quad, Triangle
from kivy.lang.builder import Builder
from kivy.core.audio import SoundLoader

import random

Builder.load_file("src/menu/menu.kv")

class MainWidget(RelativeLayout):
    from src.transforms import transform, transform_2D, transform_perspective
    from src.input import (
        on_keyboard_down,
        on_touch_down,
        on_keyboard_up,
        on_touch_up,
        keyboard_closed,
    )

    perspective_point_x = NumericProperty(0)
    perspective_point_y = NumericProperty(0)

    menu_widget = ObjectProperty()
    menu_title = StringProperty("S P A C E R U N")
    menu_button_title = StringProperty("START")
    score = StringProperty()

    NUM_VERTICAL_LINES = 18
    VERTICAL_LINE_SPACING = 0.25
    vertical_lines = []

    NUM_HORIZONTAL_LINES = 15
    HORIZONTAL_LINE_SPACING = 0.1
    horizontal_lines = []

    FRAMES = 60.0
    SPEED = 0.6
    SPEED_X = 2

    speed_y = 0
    speed_modifier = 0

    current_offset_y = 0
    current_offset_x = 0

    current_speed_x = 0

    NUM_TILES = 12
    tiles = []
    tiles_coordinates = []

    current_y_loop = 0

    RIGHT_BEND = 1
    LEFT_BEND = 2

    INITIAL_STRAIGHT_PATH_LENGTH = 15

    SHIP_WIDTH = 0.1
    SHIP_HEIGHT = 0.035
    SHIP_BASE_Y = 0.04

    ship = None
    ship_coordinates = [(0, 0), (0, 0), (0, 0)]

    state_game_over = False
    state_game_started = False

    sound_begin = None
    sound_gameover_impact = None
    sound_gameover_voice = None
    sound_play_state_music = None
    sound_menu_theme = None

    def __init__(self, **kwargs):
        super(MainWidget, self).__init__(**kwargs)
        self.icon = "images/icon.png"
        self.init_audio()
        self.sound_menu_theme.play()

        self.init_vertical_lines()
        self.init_horizontal_lines()
        self.init_tiles()
        self.init_ship()

        self.reset_game()

        if self.is_desktop():
            self._keyboard = Window.request_keyboard(self.keyboard_closed, self)
            self._keyboard.bind(on_key_down=self.on_keyboard_down)
            self._keyboard.bind(on_key_up=self.on_keyboard_up)

        Clock.schedule_interval(self.update, 1.0 / self.FRAMES)

    def init_audio(self):
        self.sound_begin = SoundLoader.load("audio/begin.wav")
        self.sound_gameover_impact = SoundLoader.load("audio/gameover_impact.wav")
        self.sound_gameover_voice = SoundLoader.load("audio/gameover_voice.wav")
        self.sound_play_state_music = SoundLoader.load("audio/play_state_music.wav")
        self.sound_menu_theme = SoundLoader.load("audio/menu_theme.wav")

        self.sound_play_state_music.volume = 0.6
        self.sound_menu_theme.volume = 0.2
        self.sound_begin.volume = 0.25
        self.sound_gameover_impact.volume = 0.25
        self.sound_gameover_voice.volume = 0.25

        self.sound_menu_theme.loop = True
        self.sound_play_state_music.loop = True

    def reset_game(self):
        self.current_offset_y = 0
        self.current_offset_x = 0
        self.current_speed_x = 0
        self.current_y_loop = 0
        self.speed_modifier = 0

        self.tiles_coordinates = []
        self.prefill_tiles_coordinates()

        self.state_game_over = False

    def increment_speed_modifier(self, dt):
        self.speed_modifier += 0.0002

    def is_desktop(self):
        if platform in ("linux", "win", "macosx"):
            return True
        return False

    def init_ship(self):
        with self.canvas:
            Color(1, 1, 1)
            self.ship = Triangle()

    def update_ship(self):
        center_x = self.width / 2
        base_y = self.SHIP_BASE_Y * self.height
        ship_half_width = self.SHIP_WIDTH * self.width / 2
        ship_height = self.SHIP_HEIGHT * self.height

        self.ship_coordinates[0] = (center_x - ship_half_width, base_y)
        self.ship_coordinates[1] = (center_x, base_y + ship_height)
        self.ship_coordinates[2] = (center_x + ship_half_width, base_y)

        x1, y1 = self.transform(*self.ship_coordinates[0])
        x2, y2 = self.transform(*self.ship_coordinates[1])
        x3, y3 = self.transform(*self.ship_coordinates[2])

        self.ship.points = [x1, y1, x2, y2, x3, y3]

    def check_ship_collision(self):
        for i in range(0, len(self.tiles_coordinates)):
            ti_x, ti_y = self.tiles_coordinates[i]
            if ti_y > self.current_y_loop + 1:
                return False
            if self.check_ship_collision_with_tile(ti_x, ti_y):
                return True
        return False

    def check_ship_collision_with_tile(self, ti_x, ti_y):
        xmin, ymin = self.get_tile_coordinates(ti_x, ti_y)
        xmax, ymax = self.get_tile_coordinates(ti_x + 1, ti_y + 1)
        for i in range(0, 3):
            px, py = self.ship_coordinates[i]
            if xmin <= px <= xmax and ymin <= py <= ymax:
                return True
        return False

    def get_line_x_from_index(self, index):
        center_line_x = self.perspective_point_x
        spacing = self.VERTICAL_LINE_SPACING * self.width
        offset = index - 0.5
        line_x = center_line_x + offset * spacing + self.current_offset_x
        return line_x

    def get_line_y_from_index(self, index):
        spacing_y = self.HORIZONTAL_LINE_SPACING * self.height
        line_y = index * spacing_y - self.current_offset_y
        return line_y

    def get_tile_coordinates(self, ti_x, ti_y):
        ti_y = ti_y - self.current_y_loop
        x = self.get_line_x_from_index(ti_x)
        y = self.get_line_y_from_index(ti_y)
        return x, y

    def prefill_tiles_coordinates(self):
        for i in range(0, self.INITIAL_STRAIGHT_PATH_LENGTH):
            self.tiles_coordinates.append((0, i))

    def generate_tiles_coordinates(self):
        start_index = -int(self.NUM_VERTICAL_LINES / 2) + 1
        end_index = start_index + self.NUM_VERTICAL_LINES - 1

        last_y = 0
        last_x = 0

        for i in range(len(self.tiles_coordinates) - 1, -1, -1):
            if self.tiles_coordinates[i][1] < self.current_y_loop:
                del self.tiles_coordinates[i]

        if len(self.tiles_coordinates) > 0:
            last_coordinates = self.tiles_coordinates[-1]
            last_y = last_coordinates[1] + 1
            last_x = last_coordinates[0]

        # Path Generation
        for i in range(len(self.tiles_coordinates), self.NUM_TILES):
            self.tiles_coordinates.append((last_x, last_y))

            r = random.randint(0, 2)
            if last_x <= start_index:
                r = self.RIGHT_BEND
            if last_x >= end_index - 1:
                r = self.LEFT_BEND

            # Right Bend
            if r == self.RIGHT_BEND:
                last_x += 1
                self.tiles_coordinates.append((last_x, last_y))
                last_y += 1
                self.tiles_coordinates.append((last_x, last_y))
            # Left Bend
            if r == self.LEFT_BEND:
                last_x -= 1
                self.tiles_coordinates.append((last_x, last_y))
                last_y += 1
                self.tiles_coordinates.append((last_x, last_y))

            last_y += 1

    def init_tiles(self):
        with self.canvas:
            Color(0.1, 0.1, 0.1)
            for i in range(0, self.NUM_TILES):
                self.tiles.append(Quad())

    def init_vertical_lines(self):
        with self.canvas:
            Color(0, 0, 0)
            for i in range(0, self.NUM_VERTICAL_LINES):
                self.vertical_lines.append(Line(width=1.25))

    def update_tiles(self):
        for i in range(0, self.NUM_TILES):
            tile = self.tiles[i]
            tile_coordinates = self.tiles_coordinates[i]
            xmin, ymin = self.get_tile_coordinates(
                tile_coordinates[0], tile_coordinates[1]
            )
            xmax, ymax = self.get_tile_coordinates(
                tile_coordinates[0] + 1, tile_coordinates[1] + 1
            )

            x1, y1 = self.transform(xmin, ymin)
            x2, y2 = self.transform(xmin, ymax)
            x3, y3 = self.transform(xmax, ymax)
            x4, y4 = self.transform(xmax, ymin)

            tile.points = [x1, y1, x2, y2, x3, y3, x4, y4]

    def update_vertical_lines(self):
        start_index = -int(self.NUM_VERTICAL_LINES / 2) + 1
        for i in range(start_index, start_index + self.NUM_VERTICAL_LINES):
            line_x = self.get_line_x_from_index(i)

            x1, y1 = self.transform(line_x, 0)
            x2, y2 = self.transform(line_x, self.height)
            self.vertical_lines[i].points = [x1, y1, x2, y2]

    def init_horizontal_lines(self):
        with self.canvas:
            Color(0, 0, 0)
            for i in range(0, self.NUM_HORIZONTAL_LINES):
                self.horizontal_lines.append(Line(width=1.25))

    def update_horizontal_lines(self):
        start_index = -int(self.NUM_VERTICAL_LINES / 2) + 1
        end_index = start_index + self.NUM_VERTICAL_LINES - 1

        xmin = self.get_line_x_from_index(start_index)
        xmax = self.get_line_x_from_index(end_index)

        for i in range(0, self.NUM_HORIZONTAL_LINES):
            line_y = self.get_line_y_from_index(i)
            x1, y1 = self.transform(xmin, line_y)
            x2, y2 = self.transform(xmax, line_y)
            self.horizontal_lines[i].points = [x1, y1, x2, y2]

    def update(self, dt):
        time_factor = dt * 60
        self.update_vertical_lines()
        self.update_horizontal_lines()
        self.update_tiles()
        self.update_ship()

        if not self.state_game_over and self.state_game_started:
            self.speed_y = self.SPEED * self.height / 100 + self.speed_modifier
            self.current_offset_y += self.speed_y * time_factor

            spacing_y = self.HORIZONTAL_LINE_SPACING * self.height
            while self.current_offset_y >= spacing_y:
                self.current_offset_y -= spacing_y
                self.current_y_loop += 1
                self.score = "SCORE: " + str(self.current_y_loop)
                self.generate_tiles_coordinates()

            speed_x = self.current_speed_x * self.width / 100
            self.current_offset_x += speed_x * time_factor
            Clock.schedule_once(self.increment_speed_modifier, 1)

        if not self.check_ship_collision() and not self.state_game_over:
            self.state_game_over = True
            self.menu_title = "GAME OVER"
            self.menu_button_title = "RESTART"
            self.menu_widget.opacity = 1
            self.sound_play_state_music.stop()
            self.sound_menu_theme.play()
            self.sound_gameover_impact.play()
            Clock.schedule_once(self.play_game_over_voice_sound, 2)

    def play_game_over_voice_sound(self, dt):
        if self.state_game_over:
            self.sound_gameover_voice.play()

    def on_menu_button_pressed(self):
        self.sound_menu_theme.stop()
        self.sound_begin.play()
        self.sound_play_state_music.play()
        self.reset_game()
        self.state_game_started = True
        self.menu_widget.opacity = 0


class SpaceRunApp(App):
    pass


SpaceRunApp().run()
