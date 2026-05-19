"""Client-side rendering (pygame)."""

import math
import pygame as pg

from core import config as C
from core.entities import Asteroid, BlackHole, Bullet, Ship, UFO, PowerUp
from core.scene import SceneState


class Renderer:
    """Draws scenes and entities without coupling game rules to Game."""

    def __init__(
        self,
        screen: pg.Surface,
        config: object = C,
        fonts: dict[str, pg.font.Font] | None = None,
    ) -> None:
        self.screen = screen
        self.config = config
        safe_fonts = fonts or {}
        self.font = safe_fonts["font"]
        self.big = safe_fonts["big"]

        self._draw_dispatch: dict[type, callable] = {
            Bullet: self._draw_bullet,
            Asteroid: self._draw_asteroid,
            Ship: self._draw_ship,
            UFO: self._draw_ufo,
            PowerUp: self._draw_powerup,
            BlackHole: self._draw_black_hole,
        }

    def clear(self) -> None:
        self.screen.fill(self.config.BG_COLOR)

    def draw_world(self, world: object) -> None:
        sprites = getattr(world, "all_sprites", [])
        for sprite in sprites:
            drawer = self._draw_dispatch.get(type(sprite))
            if drawer is not None:
                drawer(sprite)

    def draw_hud(self, world: object, state: SceneState) -> None:
        if state != SceneState.PLAY:
            return

        # Player 1 HUD
        p1_score = world.scores.get(self.config.LOCAL_PLAYER_ID, 0)
        p1_lives = world.lives.get(self.config.LOCAL_PLAYER_ID, 0)
        p1_text = f"P1: {p1_score:06d} LIVES: {p1_lives}"
        self._draw_text(self.font, p1_text, 10, 10, self.config.P1_COLOR)

        # Player 2 HUD
        p2_score = world.scores.get(self.config.P2_ID, 0)
        p2_lives = world.lives.get(self.config.P2_ID, 0)
        p2_text = f"P2: {p2_score:06d} LIVES: {p2_lives}"
        self._draw_text(self.font, p2_text, self.config.WIDTH - 300, 10, self.config.P2_COLOR)

        # Wave
        self._draw_text(self.font, f"WAVE {world.wave}", self.config.WIDTH // 2 - 40, 10)

        if world.freeze_timer > 0.0:
            self._draw_text(self.font, f"FROZEN {world.freeze_timer:.1f}s", self.config.WIDTH // 2 - 60, 40, (100, 200, 255))

        for pid, ship in world.ships.items():
            self._draw_ship_bars(ship, pid)

    def _draw_ship_bars(self, ship, pid) -> None:
        is_p1 = pid == self.config.LOCAL_PLAYER_ID
        bar_x = 10 if is_p1 else self.config.WIDTH - 130
        bar_y = 36
        bar_width = 120
        bar_height = 8

        ratio = ship.shield_energy / self.config.SHIELD_MAX_ENERGY
        fill = int(bar_width * ratio)
        pg.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height))
        if fill > 0:
            color = self.config.P1_COLOR if is_p1 else self.config.P2_COLOR
            if ship.shield_active: color = self.config.WHITE
            pg.draw.rect(self.screen, color, (bar_x, bar_y, fill, bar_height))
        pg.draw.rect(self.screen, self.config.WHITE, (bar_x, bar_y, bar_width, bar_height), width=1)

    def draw_pause(self, world: object) -> None:
        overlay = pg.Surface((self.config.WIDTH, self.config.HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        self._draw_text(self.big, "PAUSED", self.config.WIDTH // 2 - 100, 150)
        y = 250
        self._draw_text(self.font, "MECHANICS (Press 1-3 to Toggle):", self.config.WIDTH // 2 - 180, y)
        y += 50
        
        m_names = ["1. Swap de Risco", "2. Tiro da Confusão", "3. Bomba Gravitacional"]
        m_keys = ["swap", "confusion", "gravity_bomb"]
        
        for name, key in zip(m_names, m_keys):
            enabled = world.mechanics_enabled[key]
            status = "[ON]" if enabled else "[OFF]"
            color = (0, 255, 0) if enabled else (255, 0, 0)
            self._draw_text(self.font, f"{name}: {status}", self.config.WIDTH // 2 - 150, y, color)
            y += 40

        self._draw_text(self.font, "Press ESC to Resume", self.config.WIDTH // 2 - 100, y + 40)

    def draw_menu(self) -> None:
        self._draw_text(self.big, "ASTEROIDS MULTIPLAYER", self.config.WIDTH // 2 - 280, 200, self.config.P1_COLOR)
        self._draw_text(self.font, "XBOX CONTROLLERS: LT to Thrust | RT to Shoot", self.config.WIDTH // 2 - 220, 350)
        self._draw_text(self.font, "Press any button to START", self.config.WIDTH // 2 - 130, 400, self.config.P2_COLOR)

    def draw_game_over(self) -> None:
        self._draw_text(self.big, "GAME OVER", self.config.WIDTH // 2 - 170, 260, (255, 50, 50))
        self._draw_text(self.font, "Press any button to Restart", self.config.WIDTH // 2 - 140, 340)

    def _draw_text(self, font: pg.font.Font, text: str, x: int, y: int, color = None) -> None:
        if color is None: color = self.config.WHITE
        label = font.render(text, True, color)
        self.screen.blit(label, (x, y))

    def _draw_bullet(self, bullet: Bullet) -> None:
        center = (int(bullet.pos.x), int(bullet.pos.y))
        color = self.config.CONFUSION_COLOR if getattr(bullet, "is_confusion", False) else self.config.BULLET_COLOR
        pg.draw.circle(self.screen, color, center, bullet.r)

    def _draw_asteroid(self, asteroid: Asteroid) -> None:
        points = [(int(asteroid.pos.x + p.x), int(asteroid.pos.y + p.y)) for p in asteroid.poly]
        pg.draw.polygon(self.screen, self.config.ASTEROID_COLOR, points, width=2)

    def _draw_ship(self, ship: Ship) -> None:
        p1, p2, p3 = ship.ship_points()
        points = [(int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), (int(p3.x), int(p3.y))]
        color = self.config.P1_COLOR if ship.player_id == self.config.LOCAL_PLAYER_ID else self.config.P2_COLOR
        if getattr(ship, "confused_timer", 0) > 0 and int(pg.time.get_ticks() / 100) % 2 == 0:
            color = self.config.CONFUSION_COLOR
        pg.draw.polygon(self.screen, color, points, width=2)

        if ship.shield_active:
            pg.draw.circle(self.screen, color, (int(ship.pos.x), int(ship.pos.y)), ship.r + 10, width=1)
        if ship.invuln > 0.0 and int(ship.invuln * 10) % 2 == 0:
            pg.draw.circle(self.screen, self.config.WHITE, (int(ship.pos.x), int(ship.pos.y)), ship.r + 6, width=1)
        if getattr(ship, "swap_warmup", 0) > 0:
            target_pos = getattr(ship, "swap_target_pos", None)
            if target_pos:
                pg.draw.line(self.screen, self.config.WHITE, (int(ship.pos.x), int(ship.pos.y)), (int(target_pos.x), int(target_pos.y)), 1)
                pg.draw.circle(self.screen, self.config.WHITE, (int(ship.pos.x), int(ship.pos.y)), ship.r + 15, width=1)

    def _draw_black_hole(self, bh: BlackHole) -> None:
        center = (int(bh.pos.x), int(bh.pos.y))
        is_mini = getattr(bh, "is_mini", False)
        base_color = self.config.GRAVITY_BOMB_COLOR if is_mini else (60, 60, 80)
        pg.draw.circle(self.screen, base_color, center, int(bh.influence_r), width=1)
        t = getattr(bh, "age", 0)
        for i in range(3):
            phase = (t * 0.6 + i * 0.33) % 1.0
            ring_r = int(bh.r + 6 + phase * (bh.influence_r - bh.r - 6) * 0.4)
            brightness = int(180 * (1.0 - phase))
            color = (min(255, brightness + 100), brightness, 255) if is_mini else (brightness, brightness, min(255, brightness + 30))
            pg.draw.circle(self.screen, color, center, ring_r, width=1)
        pg.draw.circle(self.screen, self.config.BLACK, center, bh.r)
        pg.draw.circle(self.screen, self.config.WHITE if not is_mini else self.config.GRAVITY_BOMB_COLOR, center, bh.r, width=2)

    def _draw_ufo(self, ufo: UFO) -> None:
        width, height = ufo.r * 2, ufo.r
        body = pg.Rect(0, 0, width, height)
        body.center = (int(ufo.pos.x), int(ufo.pos.y))
        pg.draw.ellipse(self.screen, self.config.WHITE, body, width=1)
        cup = pg.Rect(0, 0, int(width * 0.5), int(height * 0.7))
        cup.center = (int(ufo.pos.x), int(ufo.pos.y - height * 0.3))
        pg.draw.ellipse(self.screen, self.config.WHITE, cup, width=1)

    def _draw_powerup(self, powerup: PowerUp) -> None:
        center = (int(powerup.pos.x), int(powerup.pos.y))
        r = powerup.r
        points = [(center[0], center[1] - r), (center[0] + r, center[1]), (center[0], center[1] + r), (center[0] - r, center[1])]
        color = (100, 200, 255) if powerup.type == "freeze" else self.config.WHITE
        pg.draw.polygon(self.screen, color, points, width=2)
        pg.draw.circle(self.screen, color, center, r // 2, width=1)
