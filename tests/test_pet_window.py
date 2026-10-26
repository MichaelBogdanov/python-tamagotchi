"""Проверки оболочки без рабочего стола: SDL рисует в память."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import contextlib
import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import pygame
import pet_window as ui


class WindowTests(unittest.TestCase):
    def setUp(self):
        ui.start(motion=False)
        self.window = ui._window
        pygame.event.clear()

    def tearDown(self):
        self.window.close()

    def key(self, key, kind=pygame.KEYUP, **kwargs):
        return self.window.handle(pygame.event.Event(kind, key=key, **kwargs))

    def test_wait_returns_button_string_and_clears_old_messages(self):
        ui.say("Первая реплика")
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_2))
        self.assertEqual(ui.choose(), "2")
        self.assertEqual(self.window.messages, [])
        self.assertEqual(self.window.effect, "2")

    def test_keydown_does_not_repeat_actions(self):
        for _ in range(5):
            self.assertIsNone(self.key(pygame.K_1, pygame.KEYDOWN))
        self.assertEqual(self.key(pygame.K_1), "1")

    def test_navigation_and_confirmation(self):
        self.key(pygame.K_TAB, pygame.KEYDOWN, mod=0)
        self.assertEqual(self.key(pygame.K_RETURN), "2")
        self.key(pygame.K_TAB, pygame.KEYDOWN, mod=pygame.KMOD_SHIFT)
        self.key(pygame.K_LEFT, pygame.KEYDOWN)
        self.assertEqual(self.key(pygame.K_SPACE), "3")

    def test_mouse_requires_press_and_release_on_same_button(self):
        a, b = (rect.center for rect in self.window.buttons[:2])
        up = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)
        down = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
        self.assertIsNone(self.window.handle(up(a)))
        self.window.handle(down(a))
        self.assertIsNone(self.window.handle(up(b)))
        self.window.handle(down(b))
        self.assertEqual(self.window.handle(up(b)), "2")

    def test_free_space_does_not_choose(self):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.assertIsNone(self.window.handle(pygame.event.Event(kind, pos=self.window.scene.center, button=1)))

    def test_show_clamps_without_changing_game_variables(self):
        hunger, energy, mood = -7, 12, 5
        ui.show(hunger, energy, mood, 11, 10)
        self.assertEqual((hunger, energy, mood), (-7, 12, 5))
        self.assertEqual((self.window.hunger, self.window.energy, self.window.mood, self.window.day), (0, 10, 5, 10))

    def test_reactions_have_explicit_priority(self):
        ui.show(9, 1, 9)
        self.assertEqual(self.window.state(), "tired")
        ui.show(9, 5, 9)
        self.assertEqual(self.window.state(), "hungry")
        ui.show(1, 5, 9)
        self.assertEqual(self.window.state(), "happy")
        self.window.effect, self.window.effect_until = "3", pygame.time.get_ticks()+1000
        self.assertEqual(self.window.state(), "sleeping")

    def test_long_text_is_wrapped_and_scrollable(self):
        ui.say("Оченьдлинноеимябезпробелов" * 40)
        font = self.window.font(18)
        lines = ui._wrap(self.window.messages[0], font, 180)
        self.assertTrue(all(font.size(line)[0] <= 180 for line in lines))
        self.assertGreater(self.window.max_scroll, 0)
        self.key(pygame.K_DOWN, pygame.KEYDOWN)
        self.assertEqual(self.window.scroll, 1)

    def test_resize_keeps_panels_and_hitboxes_on_screen(self):
        for size in ((560, 600), (900, 820), (1280, 720)):
            self.window.handle(pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1]))
            self.window.draw()
            screen = self.window.screen.get_rect()
            for rect in (self.window.header,self.window.scene,self.window.speech,self.window.stats,*self.window.buttons):
                self.assertTrue(screen.contains(rect), (size, rect))
            self.assertLess(self.window.scene.bottom, self.window.speech.top)
            self.assertLess(self.window.speech.bottom, self.window.stats.top)
            self.assertLess(self.window.stats.bottom, self.window.actions.top)

    def test_missing_and_broken_image_use_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.png"
            path.write_text("not an image", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.window._load_image("normal", path)
            self.window.draw()
            self.assertNotIn("normal", self.window.images)

    def test_png_resolves_relative_to_module_from_another_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "images").mkdir()
            image = pygame.Surface((320, 160), pygame.SRCALPHA)
            image.fill((150, 40, 90, 200))
            pygame.image.save(image, root / "images" / "pet.png")
            elsewhere = root / "another_working_directory"
            elsewhere.mkdir()
            previous_cwd = Path.cwd()
            try:
                os.chdir(elsewhere)
                with patch.object(ui, "ROOT", root):
                    ui.start()
            finally:
                os.chdir(previous_cwd)
            self.window = ui._window
            self.assertEqual(self.window.images["normal"].get_size(), (320, 160))
            self.assertTrue(self.window.scaled_images)
            scaled = next(iter(self.window.scaled_images.values()))
            self.assertAlmostEqual(scaled.get_width()/scaled.get_height(), 2, delta=.02)

    def test_finish_waits_for_confirmation_and_closes(self):
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
        ui.finish("Моё звание", "Моя концовка")
        self.assertEqual(self.window.messages, ["Моё звание", "Моя концовка"])
        self.assertTrue(self.window.closed)

    def test_quit_processed_even_after_action_in_same_batch(self):
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_1))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        with self.assertRaises(SystemExit) as error:
            ui.choose()
        self.assertEqual(error.exception.code, 0)
        self.assertTrue(self.window.closed)

    def test_motion_toggle(self):
        self.key(pygame.K_m, pygame.KEYDOWN)
        self.assertTrue(self.window.motion)
        self.key(pygame.K_m, pygame.KEYDOWN)
        self.assertFalse(self.window.motion)


class GameTests(unittest.TestCase):
    def test_full_game_all_endings_and_last_day_update(self):
        cases = [
            (["1"]*10, (0,7,0), "Хранитель"),
            (["2"]*10, (10,0,10), "Легенда"),
            (["3"]*10, (10,10,0), "Хранитель"),
            (["2"]+["1"]*9, (0,5,0), "Исследователь"),
        ]
        for choices, expected, ending in cases:
            with self.subTest(ending=ending, first=choices[0]):
                with patch.object(ui,"start"), patch.object(ui,"say"), patch.object(ui,"choose",side_effect=choices) as choose, patch.object(ui,"show") as show, patch.object(ui,"finish") as finish:
                    runpy.run_path(str(ui.ROOT / "main.py"), run_name="__main__")
                self.assertEqual(choose.call_count, 10)
                self.assertEqual([call.args[3] for call in show.call_args_list], list(range(1,11))+[10])
                self.assertEqual(show.call_args.args, (*expected,10,10))
                self.assertIn(ending, finish.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
