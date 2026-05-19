"""Local input reading and conversion to PlayerCommand."""

import pygame as pg
from typing import Dict

from core.commands import PlayerCommand
from core import config as C


class InputMapper:
    """Converts keyboard input and events into PlayerCommand for multiple players."""

    def __init__(self) -> None:
        if not pg.joystick.get_init():
            pg.joystick.init()
        self._joysticks = [pg.joystick.Joystick(x) for x in range(pg.joystick.get_count())]
        for j in self._joysticks:
            j.init()

        # Temporary state for "one-shot" events
        self._shoot_pressed = {C.LOCAL_PLAYER_ID: False, C.P2_ID: False}
        self._hyper_pressed = {C.LOCAL_PLAYER_ID: False, C.P2_ID: False}
        self._power_pressed = {C.LOCAL_PLAYER_ID: False, C.P2_ID: False}

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.JOYBUTTONDOWN:
            # Simple mapping for generic/xbox controller
            pid = C.LOCAL_PLAYER_ID if event.joy == 0 else C.P2_ID
            if pid not in [C.LOCAL_PLAYER_ID, C.P2_ID]: return
            
            if event.button == 1: # B
                self._shoot_pressed[pid] = True
            elif event.button == 2: # X
                self._hyper_pressed[pid] = True
            elif event.button == 4: # LB
                self._power_pressed[pid] = True

        if event.type != pg.KEYDOWN:
            return

        # Player 1 Keyboard (Arrows + Space/Shift/Alt)
        if event.key == pg.K_SPACE:
            self._shoot_pressed[C.LOCAL_PLAYER_ID] = True
        elif event.key == pg.K_RSHIFT:
            self._hyper_pressed[C.LOCAL_PLAYER_ID] = True
        elif event.key == pg.K_RALT:
            self._power_pressed[C.LOCAL_PLAYER_ID] = True

        # Player 2 Keyboard (WASD + V/B/N)
        elif event.key == pg.K_v:
            self._shoot_pressed[C.P2_ID] = True
        elif event.key == pg.K_b:
            self._hyper_pressed[C.P2_ID] = True
        elif event.key == pg.K_n:
            self._power_pressed[C.P2_ID] = True

    def build_commands(self, keys: pg.key.ScancodeWrapper) -> Dict[int, PlayerCommand]:
        cmds = {}
        
        # Build P1 Keyboard
        p1_cmd = PlayerCommand(
            rotate_left=keys[pg.K_LEFT],
            rotate_right=keys[pg.K_RIGHT],
            thrust=keys[pg.K_UP],
            shoot=self._shoot_pressed[C.LOCAL_PLAYER_ID],
            hyperspace=self._hyper_pressed[C.LOCAL_PLAYER_ID],
            shield=keys[pg.K_RCTRL],
            activate_power=self._power_pressed[C.LOCAL_PLAYER_ID],
        )
        cmds[C.LOCAL_PLAYER_ID] = p1_cmd

        # Build P2 Keyboard
        p2_cmd = PlayerCommand(
            rotate_left=keys[pg.K_a],
            rotate_right=keys[pg.K_d],
            thrust=keys[pg.K_w],
            shoot=self._shoot_pressed[C.P2_ID],
            hyperspace=self._hyper_pressed[C.P2_ID],
            shield=keys[pg.K_LSHIFT],
            activate_power=self._power_pressed[C.P2_ID],
        )
        cmds[C.P2_ID] = p2_cmd

        # Override with Joystick if available
        for i, j in enumerate(self._joysticks[:2]):
            pid = C.LOCAL_PLAYER_ID if i == 0 else C.P2_ID
            
            # Xbox Controller Mapping (Windows/XInput)
            # Axis 0: Left Stick X (Rotation)
            # Axis 4: Left Trigger (Thrust/Run)
            # Axis 5: Right Trigger (Shoot)
            # Button 3: Y Button (Shield)
            
            axis_x = j.get_axis(0)
            # Triggers often range from -1.0 to 1.0 or 0.0 to 1.0. 
            # Threshold 0.1 handles both.
            thrust_joy = j.get_axis(4) > 0.1
            shoot_joy = j.get_axis(5) > 0.1 or self._shoot_pressed[pid]
            shield_joy = j.get_button(3)
            
            cmds[pid] = PlayerCommand(
                rotate_left=axis_x < -0.5,
                rotate_right=axis_x > 0.5,
                thrust=thrust_joy,
                shoot=shoot_joy,
                hyperspace=self._hyper_pressed[pid],
                shield=shield_joy,
                activate_power=self._power_pressed[pid]
            )

        # Reset one-shots
        for pid in [C.LOCAL_PLAYER_ID, C.P2_ID]:
            self._shoot_pressed[pid] = False
            self._hyper_pressed[pid] = False
            self._power_pressed[pid] = False

        return cmds
