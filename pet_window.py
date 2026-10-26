"""Готовое окно питомца. Ученикам достаточно функций в конце этого файла.

Все ожидания обрабатывают события Pygame на основном потоке. Игровые правила
остаются в main.py; оболочка только показывает переданные ей значения.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


ROOT = Path(__file__).resolve().parent
INK = (42, 48, 66)
MUTED = (99, 108, 125)
PAPER = (248, 249, 252)
WHITE = (255, 255, 255)
LINE = (224, 228, 238)


def _wrap(text, font, width):
    """Переносим даже очень длинное слово; явные переводы строк сохраняются."""
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if font.size(candidate)[0] <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            for char in word:
                if line and font.size(line + char)[0] > width:
                    lines.append(line)
                    line = ""
                line += char
        lines.append(line)
    return lines or [""]


class PetWindow:
    """Внутреннее устройство окна, не часть задания для детей."""

    def __init__(self, name="Туманчик", species="Облачный лис", *,
                 image="images/pet.png", color="#6955c4", motion=True):
        pygame.display.init()
        pygame.font.init()
        info = pygame.display.Info()
        size = (min(900, max(560, info.current_w - 100)),
                min(820, max(600, info.current_h - 110)))
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption(f"{name} · Мой питомец")
        self.clock = pygame.time.Clock()
        self.name, self.species = str(name), str(species)
        self.accent = pygame.Color(color)
        self.motion = motion
        # SysFont иногда выбирает Segoe UI Light вместо обычного начертания.
        regular = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
        self.font_path = str(regular) if regular.is_file() else pygame.font.match_font("dejavusans,arial")
        self.fonts = {}
        self.hunger, self.energy, self.mood = 3, 7, 5
        self.day, self.total_days = 1, 10
        self.messages = []
        self.scroll = 0
        self.max_scroll = 0
        self.focus = 0
        self.pressed = None
        self.mouse = (-1, -1)
        self.mode = "play"
        self.effect = ""
        self.effect_until = 0
        self.ready_at = 0
        self.closed = False
        self.labels = ("Покормить", "Поиграть", "Спать")
        self.images = {}
        self.scaled_images = {}
        path = Path(image)
        if not path.is_absolute():
            path = ROOT / path
        self._load_image("normal", path)
        for state in ("happy", "hungry", "tired", "sleeping"):
            self._load_image(state, path.with_name(state + ".png"))
        self._layout()
        self.draw()

    def _load_image(self, state, path):
        if not path.is_file():
            return
        try:
            self.images[state] = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError) as error:
            # Испорченный рисунок не должен мешать запуску учебной программы.
            print(f"Не удалось открыть {path.name}: {error}. Использую встроенного питомца.")

    def font(self, size, bold=False):
        key = (max(12, round(size * self.scale)), bold)
        if key not in self.fonts:
            font = pygame.font.Font(self.font_path, key[0])
            font.set_bold(bold)
            self.fonts[key] = font
        return self.fonts[key]

    def _layout(self):
        w, h = self.screen.get_size()
        self.scale = max(.82, min(1.15, w / 900, h / 820))
        s = self.scale
        margin, gap = round(28 * s), round(14 * s)
        inner = w - margin * 2
        header_h, footer_h = round(76 * s), round(34 * s)
        button_h, stat_h, speech_h = round(76 * s), round(88 * s), round(108 * s)
        self.header = pygame.Rect(margin, margin, inner, header_h)
        self.actions = pygame.Rect(margin, h - margin - footer_h - button_h, inner, button_h)
        self.stats = pygame.Rect(margin, self.actions.y - gap - stat_h, inner, stat_h)
        self.speech = pygame.Rect(margin, self.stats.y - gap - speech_h, inner, speech_h)
        top = self.header.bottom + gap
        self.scene = pygame.Rect(margin, top, inner, max(80, self.speech.y - gap - top))
        self.buttons = []
        for i in range(3):
            left = margin + round(i * (inner + gap) / 3)
            right = margin + round((i + 1) * (inner + gap) / 3) - gap
            self.buttons.append(pygame.Rect(left, self.actions.y, right - left, button_h))
        self.done_button = pygame.Rect(0, self.actions.y, min(inner, round(330 * s)), button_h)
        self.done_button.centerx = w // 2

    def _text(self, text, rect, size=18, color=INK, bold=False, center=False):
        """Одна строка с многоточием вместо выхода за границы."""
        font = self.font(size, bold)
        text = str(text)
        if font.size(text)[0] > rect.w:
            while text and font.size(text + "…")[0] > rect.w:
                text = text[:-1]
            text += "…"
        surface = font.render(text, True, color)
        pos = surface.get_rect(center=rect.center) if center else surface.get_rect(midleft=rect.midleft)
        self.screen.blit(surface, pos)

    def _card(self, rect, fill=WHITE, border=None, radius=20):
        pygame.draw.rect(self.screen, fill, rect, border_radius=round(radius * self.scale))
        if border:
            pygame.draw.rect(self.screen, border, rect, 1, border_radius=round(radius * self.scale))

    def state(self):
        if self.effect == "3" and pygame.time.get_ticks() < self.effect_until:
            return "sleeping"
        if self.energy <= 2:
            return "tired"
        if self.hunger >= 8:
            return "hungry"
        if self.mood >= 7:
            return "happy"
        return "normal"

    def _pet(self, area, now):
        state = self.state()
        image = self.images.get(state, self.images.get("normal"))
        bob = math.sin(now / 650) * 3 * self.scale if self.motion else 0
        size = min(area.w * .66, area.h * .88, 280 * self.scale)
        center = (area.centerx, round(area.centery + bob + 7 * self.scale))
        shadow = pygame.Rect(0, 0, round(size * .82), max(6, round(size * .08)))
        shadow.center = (center[0], round(center[1] + size * .40))
        pygame.draw.ellipse(self.screen, (211, 216, 235), shadow)
        if image:
            target = max(1, round(size))
            key = (id(image), target)
            if key not in self.scaled_images:
                ratio = min(target / image.get_width(), target / image.get_height())
                dimensions = (max(1, round(image.get_width() * ratio)),
                              max(1, round(image.get_height() * ratio)))
                self.scaled_images[key] = pygame.transform.smoothscale(image, dimensions)
            pet = self.scaled_images[key]
            self.screen.blit(pet, pet.get_rect(center=center))
        else:
            self._fox(center, size, state, now)
        if now < self.effect_until:
            symbol = {"1": "М-м-м!", "2": "+ радость", "3": "Z z z"}.get(self.effect, "")
            badge = pygame.Rect(center[0] + round(size * .26),
                                center[1] - round(size * .38), round(105 * self.scale), round(34 * self.scale))
            badge.clamp_ip(area)
            self._card(badge, WHITE, radius=12)
            self._text(symbol, badge, 15, self.accent, center=True)

    def _fox(self, center, size, state, now):
        """Небольшая векторная иллюстрация: работает без внешних файлов."""
        cx, cy = center
        u = size / 220
        def point(x, y):
            return round(cx + x * u), round(cy + y * u)
        def ellipse(color, x, y, w, h):
            pygame.draw.ellipse(self.screen, color, pygame.Rect(*point(x, y), round(w * u), round(h * u)))
        fur, light, inner = (240, 181, 137), (255, 244, 225), (216, 143, 141)
        # Хвост, туловище, лапы и уши.
        ellipse(fur, 35, 10, 65, 68)
        ellipse(light, 69, 14, 30, 33)
        ellipse(fur, -51, -8, 102, 96)
        ellipse(light, -32, 25, 64, 58)
        ellipse(fur, -49, 70, 40, 20)
        ellipse(fur, 10, 70, 40, 20)
        pygame.draw.polygon(self.screen, fur, [point(-67, -20), point(-69, -94), point(-15, -57)])
        pygame.draw.polygon(self.screen, fur, [point(67, -20), point(69, -94), point(15, -57)])
        pygame.draw.polygon(self.screen, inner, [point(-57, -36), point(-59, -74), point(-32, -53)])
        pygame.draw.polygon(self.screen, inner, [point(57, -36), point(59, -74), point(32, -53)])
        ellipse(fur, -76, -67, 152, 116)
        ellipse(light, -68, -12, 84, 58)
        ellipse(light, -16, -12, 84, 58)
        sleeping = state in ("sleeping", "tired")
        blink = self.motion and now % 4300 < 140
        for x in (-32, 32):
            if sleeping or blink:
                pygame.draw.line(self.screen, INK, point(x - 7, -8), point(x + 7, -8), max(2, round(3 * u)))
            else:
                ellipse(INK, x - 5, -18, 10, 15)
                ellipse(WHITE, x - 2, -16, 3, 4)
        ellipse((237, 159, 148), -55, 2, 20, 10)
        ellipse((237, 159, 148), 35, 2, 20, 10)
        pygame.draw.polygon(self.screen, INK, [point(-7, 7), point(7, 7), point(0, 13)])
        if state == "happy":
            ellipse(INK, -8, 18, 16, 13)
        else:
            pygame.draw.lines(self.screen, INK, False, [point(-8, 20), point(0, 24), point(8, 20)], max(1, round(2 * u)))

    def _draw_messages(self):
        self._card(self.speech, WHITE, LINE)
        padding = round(18 * self.scale)
        box = self.speech.inflate(-2 * padding, -2 * padding)
        font = self.font(18)
        text = "\n".join(self.messages) or "Выбери, чем мы займёмся сегодня."
        lines = _wrap(text, font, box.w - round(26 * self.scale))
        line_h = font.get_linesize() + 2
        count = max(1, box.h // line_h)
        self.max_scroll = max(0, len(lines) - count)
        self.scroll = max(0, min(self.scroll, self.max_scroll))
        previous = self.screen.get_clip()
        self.screen.set_clip(box)
        for i, line in enumerate(lines[self.scroll:self.scroll + count]):
            self.screen.blit(font.render(line, True, INK), (box.x, box.y + i * line_h))
        self.screen.set_clip(previous)
        if self.max_scroll:
            track = pygame.Rect(box.right - 5, box.y, 3, box.h)
            pygame.draw.rect(self.screen, LINE, track, border_radius=2)
            thumb_h = max(12, round(box.h * count / len(lines)))
            thumb_y = track.y + round((track.h - thumb_h) * self.scroll / self.max_scroll)
            pygame.draw.rect(self.screen, self.accent, (track.x, thumb_y, 3, thumb_h), border_radius=2)

    def draw(self):
        if self.closed:
            return
        self._layout()
        s = self.scale
        now = pygame.time.get_ticks()
        self.screen.fill(PAPER)
        day_box = pygame.Rect(self.header.right - round(126*s), self.header.y + round(16*s), round(126*s), round(38*s))
        self._card(day_box, (237, 234, 249), radius=14)
        self._text(f"{self.day} / {self.total_days} дней", day_box, 16, self.accent, True, True)
        name_box = pygame.Rect(self.header.x, self.header.y + round(23*s), day_box.x-self.header.x-round(16*s), round(43*s))
        self._text(self.species.upper() if self.mode == "play" else "НАШЕ ПРИКЛЮЧЕНИЕ", name_box.move(0, -round(28*s)), 13, MUTED, True)
        self._text(self.name if self.mode == "play" else "Спасибо за заботу!", name_box, 32, bold=True)

        self._card(self.scene, (234, 238, 250), radius=25)
        previous = self.screen.get_clip()
        self.screen.set_clip(self.scene)
        for dx, dy, radius in ((.18, .27, 43), (.83, .68, 60), (.68, .15, 24)):
            pygame.draw.circle(self.screen, (242, 245, 255),
                               (round(self.scene.x+self.scene.w*dx), round(self.scene.y+self.scene.h*dy)), round(radius*s))
        # Небольшие звёзды создают окружение, не отвлекая от героя.
        for dx, dy in ((.25,.60),(.74,.34),(.84,.22)):
            x, y = round(self.scene.x+self.scene.w*dx), round(self.scene.y+self.scene.h*dy)
            pygame.draw.line(self.screen, (179,189,218), (x-4,y), (x+4,y), 2)
            pygame.draw.line(self.screen, (179,189,218), (x,y-4), (x,y+4), 2)
        self._pet(self.scene, now)
        self.screen.set_clip(previous)
        state_text = {"normal":"Давай дружить", "happy":"В отличном настроении", "hungry":"Пора перекусить", "tired":"Хочется отдохнуть", "sleeping":"Тихо, я сплю"}[self.state()]
        badge = pygame.Rect(self.scene.x+round(16*s), self.scene.y+round(12*s), min(round(230*s), self.scene.w-32), round(29*s))
        self._text(state_text, badge, 14, MUTED)
        self._draw_messages()

        values = (("Сытость", 10-self.hunger, (67,145,118)),
                  ("Энергия", self.energy, (179,120,46)),
                  ("Настроение", self.mood, (117,95,188)))
        for i, (label, value, color) in enumerate(values):
            rect = pygame.Rect(self.buttons[i].x, self.stats.y, self.buttons[i].w, self.stats.h)
            self._card(rect, WHITE, LINE, 16)
            pad = round(15*s)
            self._text(label, pygame.Rect(rect.x+pad,rect.y+round(10*s),rect.w-2*pad,round(24*s)), 16, MUTED)
            value_box = pygame.Rect(rect.x+pad,rect.y+round(35*s),rect.w-2*pad,round(23*s))
            self._text(f"{value} / 10", value_box, 19, color, True)
            track = pygame.Rect(rect.x+pad, rect.bottom-round(16*s), rect.w-pad*2, max(4,round(5*s)))
            pygame.draw.rect(self.screen, (235,238,244), track, border_radius=3)
            if value:
                pygame.draw.rect(self.screen, color, (track.x,track.y,round(track.w*value/10),track.h), border_radius=3)

        if self.mode == "play":
            for i, rect in enumerate(self.buttons):
                hover = rect.collidepoint(self.mouse)
                pressed = self.pressed == i
                fill = (231,226,247) if pressed else (242,239,252) if hover else WHITE
                target = rect.move(0, 2 if pressed else 0)
                self._card(target, fill, self.accent if self.focus == i else LINE, 18)
                if self.focus == i:
                    pygame.draw.rect(self.screen, self.accent, target, 2, border_radius=round(18*s))
                label_box = target.inflate(-16, 0)
                self._text(f"{i+1}  {self.labels[i]}", label_box, 17, bold=True, center=True)
        else:
            self._card(self.done_button, self.accent, radius=18)
            # Контрастный текст сохраняется и при пользовательском цвете.
            brightness = .2126*self.accent.r + .7152*self.accent.g + .0722*self.accent.b
            self._text("Завершить", self.done_button, 20, INK if brightness > 170 else WHITE, True, True)

        footer = pygame.Rect(self.actions.x, self.actions.bottom+round(8*s), self.actions.w, round(27*s))
        hint = "1–3: действие   •   Tab / ← →: выбор   •   Enter: подтвердить   •   M: движение"
        if self.max_scroll:
            hint = "Колёсико / ↑ ↓: читать реплики   •   M: движение   •   Esc: выход"
        if self.mode == "finish" and not self.max_scroll:
            hint = "Спасибо за игру!   •   Enter или Esc: закрыть окно"
        self._text(hint, footer, 12, MUTED, center=True)
        pygame.display.flip()

    def handle(self, event):
        """Вернуть команду только после завершённого нажатия."""
        if event.type == pygame.QUIT:
            self.close()
            raise SystemExit(0)
        if event.type == pygame.VIDEORESIZE:
            size = (max(560, event.w), max(600, event.h))
            self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            self.scaled_images.clear()
            self._layout()
        if event.type == pygame.WINDOWFOCUSLOST:
            self.pressed = None
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll-event.y))
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                raise SystemExit(0)
            if event.key == pygame.K_m:
                self.motion = not self.motion
            if event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll = min(self.max_scroll, self.scroll+1)
            if event.key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll = max(0, self.scroll-1)
            if self.mode == "play":
                if event.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT):
                    backwards = event.key == pygame.K_LEFT or (event.key == pygame.K_TAB and getattr(event, "mod", 0) & pygame.KMOD_SHIFT)
                    self.focus = (self.focus + (-1 if backwards else 1)) % 3
        result = None
        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                result = str(self.focus+1) if self.mode == "play" else "done"
            elif self.mode == "play":
                result = {pygame.K_1:"1",pygame.K_2:"2",pygame.K_3:"3",
                          pygame.K_KP1:"1",pygame.K_KP2:"2",pygame.K_KP3:"3"}.get(event.key)
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and event.button == 1:
            self.mouse = event.pos
            targets = self.buttons if self.mode == "play" else [self.done_button]
            hit = next((i for i, rect in enumerate(targets) if rect.collidepoint(event.pos)), None)
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.pressed = hit
                if hit is not None and self.mode == "play":
                    self.focus = hit
            else:
                if hit is not None and hit == self.pressed:
                    result = str(hit+1) if self.mode == "play" else "done"
                self.pressed = None
        if result and pygame.time.get_ticks() >= self.ready_at:
            return result
        return None

    def wait(self):
        while not self.closed:
            selected = None
            # Обрабатываем весь пакет, в том числе закрытие после клика.
            for event in pygame.event.get():
                result = self.handle(event)
                if result and selected is None:
                    selected = result
            if selected:
                self.pressed = None
                self.ready_at = pygame.time.get_ticks() + 180
                if self.mode == "play":
                    self.effect = selected
                    self.effect_until = pygame.time.get_ticks() + 1700
                    self.messages.clear()
                    self.scroll = 0
                return selected
            self.draw()
            self.clock.tick(60)

    def close(self):
        self.closed = True
        pygame.quit()


_window = None


def _get_window():
    global _window
    if _window is None or _window.closed:
        _window = PetWindow()
    return _window


def start(name="Туманчик", species="Облачный лис", *, image="images/pet.png",
          color="#6955c4", motion=True):
    """Открыть окно. Пути к рисункам считаются от папки pet_window.py."""
    global _window
    if _window is not None and not _window.closed:
        _window.close()
    _window = PetWindow(name, species, image=image, color=color, motion=motion)


def show(hunger, energy, mood, day=1, total_days=10):
    """Показать значения. Сытость на экране равна 10 - hunger."""
    window = _get_window()
    window.hunger, window.energy, window.mood = [max(0, min(10, int(v))) for v in (hunger, energy, mood)]
    window.total_days = max(1, int(total_days))
    window.day = max(1, min(window.total_days, int(day)))
    window.draw()


def say(*parts):
    """Добавить реплику, как print(). Реплики читаются во время choose/finish."""
    window = _get_window()
    window.messages.append(" ".join(str(part) for part in parts))
    window.scroll = 0
    window.draw()


def choose(feed="Покормить", play="Поиграть", sleep="Спать"):
    """Ждать кнопку, обслуживая окно; вернуть строку '1', '2' или '3'."""
    window = _get_window()
    window.labels = (str(feed), str(play), str(sleep))
    window.mode = "play"
    return window.wait()


def finish(title="Спасибо за заботу!", message="До новой встречи!"):
    """Показать итог и оставить окно открытым до кнопки «Завершить»."""
    window = _get_window()
    window.mode = "finish"
    window.messages = [str(title), str(message)]
    window.scroll = 0
    window.wait()
    window.close()
