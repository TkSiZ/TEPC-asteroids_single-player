"""Game systems (World, waves, score)."""

import math
from random import uniform, choice
from typing import Dict

import pygame as pg

from core import config as C
from core.collisions import CollisionManager
from core.commands import PlayerCommand
from core.entities import Asteroid, BlackHole, Ship, UFO, PowerUp, EnumPowerUps
from core.utils import Vec, rand_edge_pos

PlayerId = int


class World:
    """World state and game rules."""

    def __init__(self) -> None:
        self.ships: Dict[PlayerId, Ship] = {}
        self.bullets = pg.sprite.Group()
        self.asteroids = pg.sprite.Group()
        self.ufos = pg.sprite.Group()
        self.powerups = pg.sprite.Group()
        self.black_holes = pg.sprite.Group()
        self.all_sprites = pg.sprite.Group()

        self.scores: Dict[PlayerId, int] = {}
        self.lives: Dict[PlayerId, int] = {}
        self.wave = 0
        self.wave_cool = float(C.WAVE_DELAY)
        self.ufo_timer = float(C.UFO_SPAWN_EVERY)
        self.freeze_timer = 0.0
        self.black_hole_timer = uniform(
            C.BLACK_HOLE_SPAWN_EVERY_MIN, C.BLACK_HOLE_SPAWN_EVERY_MAX
        )

        self.events: list[str] = []
        self._collision_mgr = CollisionManager()

        self.game_over = False
        
        # Mechanics Toggles
        self.mechanics_enabled = {
            "swap": True,
            "confusion": True,
            "gravity_bomb": True
        }

        self.spawn_player(C.LOCAL_PLAYER_ID)
        self.spawn_player(C.P2_ID)

    def begin_frame(self) -> None:
        self.events.clear()

    def reset(self) -> None:
        """Reset the world (used on Game Over)."""
        self.__init__()

    def spawn_player(self, player_id: PlayerId) -> None:
        # Offset P1 and P2 slightly
        offset = -40 if player_id == C.LOCAL_PLAYER_ID else 40
        pos = Vec(C.WIDTH / 2 + offset, C.HEIGHT / 2)
        ship = Ship(player_id, pos)
        ship.invuln = float(C.SAFE_SPAWN_TIME)

        self.ships[player_id] = ship
        self.scores[player_id] = 0
        self.lives[player_id] = C.START_LIVES
        self.all_sprites.add(ship)

    def get_ship(self, player_id: PlayerId) -> Ship | None:
        return self.ships.get(player_id)

    def start_wave(self) -> None:
        self.wave += 1
        count = C.WAVE_BASE_COUNT + self.wave
        ship_positions = [s.pos for s in self.ships.values()]

        for _ in range(count):
            pos = rand_edge_pos()
            while any((pos - sp).length() < C.AST_MIN_SPAWN_DIST for sp in ship_positions):
                pos = rand_edge_pos()

            ang = uniform(0, math.tau)
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
            vel = Vec(math.cos(ang), math.sin(ang)) * speed
            self.spawn_asteroid(pos, vel, "L")

    def spawn_asteroid(self, pos: Vec, vel: Vec, size: str) -> None:
        ast = Asteroid(pos, vel, size)
        self.asteroids.add(ast)
        self.all_sprites.add(ast)

    def spawn_powerup(self, pos: Vec, type: str) -> None:
        pu = PowerUp(pos, type)
        self.powerups.add(pu)
        self.all_sprites.add(pu)

    def spawn_ufo(self) -> None:
        small = uniform(0, 1) < 0.5
        pos = rand_edge_pos()
        target = self._get_nearest_ship_pos(pos)
        ufo = UFO(pos, small, target_pos=target)
        self.ufos.add(ufo)
        self.all_sprites.add(ufo)

    def spawn_random_powerup(self, pos: Vec):
        powerup = choice([pw.name for pw in EnumPowerUps])
        self.spawn_power_up(pos, powerup)

    def spawn_power_up(self, pos: Vec, power_up: str):
        pw_up = PowerUp(pos, power_up)
        self.powerups.add(pw_up)
        self.all_sprites.add(pw_up)

    def spawn_black_hole(self) -> None:
        ship_positions = [s.pos for s in self.ships.values()]
        margin = C.BLACK_HOLE_RADIUS * 2
        pos = Vec(uniform(margin, C.WIDTH - margin), uniform(margin, C.HEIGHT - margin))
        for _ in range(10):
            if all((pos - sp).length() >= C.BLACK_HOLE_MIN_SPAWN_DIST for sp in ship_positions):
                break
            pos = Vec(uniform(margin, C.WIDTH - margin), uniform(margin, C.HEIGHT - margin))

        lifetime = uniform(C.BLACK_HOLE_LIFETIME_MIN, C.BLACK_HOLE_LIFETIME_MAX)
        bh = BlackHole(pos, lifetime)
        self.black_holes.add(bh)
        self.all_sprites.add(bh)
        self.events.append("black_hole_spawn")

    def update(self, dt: float, commands_by_player_id: Dict[PlayerId, PlayerCommand]) -> None:
        self.begin_frame()
        if self.game_over: return

        self._apply_commands(dt, commands_by_player_id)
        self._update_mechanics(dt)
        
        for ship in self.ships.values():
            ship.update(dt)
        self.bullets.update(dt)
        self.powerups.update(dt)
        self.black_holes.update(dt)

        if self.freeze_timer > 0.0:
            self.freeze_timer -= dt
        else:
            self.asteroids.update(dt)
            self._update_ufos(dt)
            
        self._apply_black_hole_pull(dt)
        self._update_timers(dt)
        self._handle_collisions()
        self._maybe_start_next_wave(dt)

    def _apply_commands(self, dt: float, commands_by_player_id: Dict[PlayerId, PlayerCommand]) -> None:
        for player_id, cmd in commands_by_player_id.items():
            ship = self.get_ship(player_id)
            if ship is None: continue

            if cmd.hyperspace:
                ship.hyperspace()
                self.scores[player_id] = max(0, self.scores[player_id] - C.HYPERSPACE_COST)
                
            if cmd.activate_power:
                self._handle_mechanic_activation(ship)

            bullet = ship.apply_command(cmd, dt, self.bullets)
            if bullet:
                if isinstance(bullet, list):
                    for b in bullet:
                        self.bullets.add(b)
                        self.all_sprites.add(b)
                else:
                    self.bullets.add(bullet)
                    self.all_sprites.add(bullet)
                self.events.append("player_shoot")

    def _handle_mechanic_activation(self, ship: Ship):
        pid = ship.player_id
        other_pid = C.P2_ID if pid == C.LOCAL_PLAYER_ID else C.LOCAL_PLAYER_ID
        other_ship = self.get_ship(other_pid)
        
        if self.mechanics_enabled["swap"] and other_ship and ship.swap_warmup <= 0:
            ship.swap_warmup = C.SWAP_WARMUP
            ship.swap_target_pos = other_ship.pos
            self.events.append("powerup_collect")
            
        if self.mechanics_enabled["gravity_bomb"]:
            if not any(getattr(bh, "owner_id", None) == pid for bh in self.black_holes):
                bh = BlackHole(Vec(ship.pos), C.MINI_BH_LIFETIME, is_mini=True, owner_id=pid)
                self.black_holes.add(bh)
                self.all_sprites.add(bh)
                self.events.append("black_hole_spawn")

    def _update_mechanics(self, dt: float):
        for pid, ship in self.ships.items():
            if ship.swap_warmup > 0:
                other_pid = C.P2_ID if pid == C.LOCAL_PLAYER_ID else C.LOCAL_PLAYER_ID
                other_ship = self.get_ship(other_pid)
                if other_ship: ship.swap_target_pos = other_ship.pos
                
                if ship.swap_warmup - dt <= 0:
                    if other_ship:
                        ship.pos, other_ship.pos = Vec(other_ship.pos), Vec(ship.pos)
                        ship.swap_warmup = 0
                        self.events.append("ship_explosion")

    def _apply_black_hole_pull(self, dt: float) -> None:
        for pid, ship in self.ships.items():
            total_accel = Vec(0, 0)
            for bh in self.black_holes:
                total_accel += bh.pull_acceleration(ship.pos, target_id=pid)
            if total_accel.length_squared() > 0:
                ship.vel += total_accel * dt

    def _update_ufos(self, dt: float) -> None:
        for ufo in list(self.ufos):
            ufo.target_pos = self._get_nearest_ship_pos(ufo.pos)
            ufo.update(dt)
            if not ufo.alive(): continue
            bullet = ufo.try_fire()
            if bullet:
                self.bullets.add(bullet)
                self.all_sprites.add(bullet)
                self.events.append("ufo_shoot")

    def _get_nearest_ship_pos(self, from_pos: Vec) -> Vec | None:
        nearest = None
        min_dist = float("inf")
        for ship in self.ships.values():
            d = (ship.pos - from_pos).length()
            if d < min_dist:
                min_dist = d
                nearest = ship
        return nearest.pos if nearest else None

    def _update_timers(self, dt: float) -> None:
        self.ufo_timer -= dt
        if self.ufo_timer <= 0.0:
            self.spawn_ufo()
            self.ufo_timer = float(C.UFO_SPAWN_EVERY)

        self.black_hole_timer -= dt
        if self.black_hole_timer <= 0.0:
            self.spawn_black_hole()
            self.black_hole_timer = uniform(C.BLACK_HOLE_SPAWN_EVERY_MIN, C.BLACK_HOLE_SPAWN_EVERY_MAX)

    def _maybe_start_next_wave(self, dt: float) -> None:
        if self.asteroids: return
        self.wave_cool -= dt
        if self.wave_cool <= 0.0:
            self.start_wave()
            self.wave_cool = float(C.WAVE_DELAY)

    def _handle_collisions(self) -> None:
        result = self._collision_mgr.resolve(self.ships, self.bullets, self.asteroids, self.ufos, self.powerups, self.black_holes)
        self.events.extend(result.events)
        for pid, delta in result.score_deltas.items():
            if pid in self.scores: self.scores[pid] += delta
        for ufo in result.ufo_deaths: self.spawn_random_powerup(ufo.pos)
        for powerup, ship in result.powerups_to_apply: self._apply_powerup(powerup, ship)
        for pos, vel, size in result.asteroids_to_spawn: self.spawn_asteroid(pos, vel, size)
        for pos, type in result.powerups_to_spawn: self.spawn_powerup(pos, type)
        for pid in result.ship_deaths:
            ship = self.get_ship(pid)
            if ship: self._ship_die(ship)
        for pid in result.instant_deaths:
            ship = self.get_ship(pid)
            if ship: self._ship_die_instant(ship)

    def _ship_die(self, ship: Ship) -> None:
        pid = ship.player_id
        self.lives[pid] -= 1
        ship.pos.xy = (C.WIDTH / 2, C.HEIGHT / 2)
        ship.vel.xy = (0, 0)
        ship.angle = -90.0
        ship.invuln = float(C.SAFE_SPAWN_TIME)
        self.events.append("ship_explosion")
        if any(v <= 0 for v in self.lives.values()): self.game_over = True

    def _apply_powerup(self, powerup: PowerUp, ship: Ship):
        if powerup.type == "ONE_UP": self.lives[ship.player_id] += 1
        elif powerup.type == "freeze":
            self.freeze_timer = float(C.FREEZE_POWERUP_DURATION)
            self.events.append("powerup_collect")

    def _ship_die_instant(self, ship: Ship) -> None:
        self.lives[ship.player_id] = 0
        ship.vel.xy = (0, 0)
        if any(v <= 0 for v in self.lives.values()): self.game_over = True
