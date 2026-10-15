#!/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from ..utils import TeleopEvents


class InputController:
    """Base class for input controllers that generate motion deltas."""

    def __init__(self, x_step_size=1.0, y_step_size=1.0, z_step_size=1.0):
        """
        Initialize the controller.

        Args:
            x_step_size: Base movement step size in meters
            y_step_size: Base movement step size in meters
            z_step_size: Base movement step size in meters
        """
        self.x_step_size = x_step_size
        self.y_step_size = y_step_size
        self.z_step_size = z_step_size
        self.running = True
        self.episode_end_status = None  # None, "success", or "failure"
        self.intervention_flag = False
        self.open_gripper_command = False
        self.close_gripper_command = False

    def start(self):
        """Start the controller and initialize resources."""
        pass

    def stop(self):
        """Stop the controller and release resources."""
        pass

    def get_deltas(self):
        """Get the current movement deltas (dx, dy, dz) in meters."""
        return 0.0, 0.0, 0.0

    def update(self):
        """Update controller state - call this once per frame."""
        pass

    def __enter__(self):
        """Support for use in 'with' statements."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are released when exiting 'with' block."""
        self.stop()

    def get_episode_end_status(self):
        """
        Get the current episode end status.

        Returns:
            None if episode should continue, "success" or "failure" otherwise
        """
        status = self.episode_end_status
        self.episode_end_status = None  # Reset after reading
        return status

    def should_intervene(self):
        """Return True if intervention flag was set."""
        return self.intervention_flag

    def gripper_command(self):
        """Return the current gripper command."""
        if self.open_gripper_command == self.close_gripper_command:
            return "stay"
        elif self.open_gripper_command:
            return "open"
        elif self.close_gripper_command:
            return "close"


class KeyboardController(InputController):
    """Generate motion deltas from keyboard input."""

    def __init__(self, x_step_size=1.0, y_step_size=1.0, z_step_size=1.0):
        super().__init__(x_step_size, y_step_size, z_step_size)
        self.key_states = {
            "forward_x": False,
            "backward_x": False,
            "forward_y": False,
            "backward_y": False,
            "forward_z": False,
            "backward_z": False,
            "quit": False,
            "success": False,
            "failure": False,
        }
        self.listener = None

    def start(self):
        """Start the keyboard listener."""
        from pynput import keyboard

        def on_press(key):
            try:
                if key == keyboard.Key.up:
                    self.key_states["forward_x"] = True
                elif key == keyboard.Key.down:
                    self.key_states["backward_x"] = True
                elif key == keyboard.Key.left:
                    self.key_states["forward_y"] = True
                elif key == keyboard.Key.right:
                    self.key_states["backward_y"] = True
                elif key == keyboard.Key.shift:
                    self.key_states["backward_z"] = True
                elif key == keyboard.Key.shift_r:
                    self.key_states["forward_z"] = True
                elif key == keyboard.Key.esc:
                    self.key_states["quit"] = True
                    self.running = False
                    return False
                elif key == keyboard.Key.enter:
                    self.key_states["success"] = True
                    self.episode_end_status = TeleopEvents.SUCCESS
                elif key == keyboard.Key.backspace:
                    self.key_states["failure"] = True
                    self.episode_end_status = TeleopEvents.FAILURE
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key == keyboard.Key.up:
                    self.key_states["forward_x"] = False
                elif key == keyboard.Key.down:
                    self.key_states["backward_x"] = False
                elif key == keyboard.Key.left:
                    self.key_states["forward_y"] = False
                elif key == keyboard.Key.right:
                    self.key_states["backward_y"] = False
                elif key == keyboard.Key.shift:
                    self.key_states["backward_z"] = False
                elif key == keyboard.Key.shift_r:
                    self.key_states["forward_z"] = False
                elif key == keyboard.Key.enter:
                    self.key_states["success"] = False
                elif key == keyboard.Key.backspace:
                    self.key_states["failure"] = False
            except AttributeError:
                pass

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

        print("Keyboard controls:")
        print("  Arrow keys: Move in X-Y plane")
        print("  Shift and Shift_R: Move in Z axis")
        print("  Enter: End episode with SUCCESS")
        print("  Backspace: End episode with FAILURE")
        print("  ESC: Exit")

    def stop(self):
        """Stop the keyboard listener."""
        if self.listener and self.listener.is_alive():
            self.listener.stop()

    def get_deltas(self):
        """Get the current movement deltas from keyboard state."""
        delta_x = delta_y = delta_z = 0.0

        if self.key_states["forward_x"]:
            delta_x += self.x_step_size
        if self.key_states["backward_x"]:
            delta_x -= self.x_step_size
        if self.key_states["forward_y"]:
            delta_y += self.y_step_size
        if self.key_states["backward_y"]:
            delta_y -= self.y_step_size
        if self.key_states["forward_z"]:
            delta_z += self.z_step_size
        if self.key_states["backward_z"]:
            delta_z -= self.z_step_size

        return delta_x, delta_y, delta_z


class GamepadController(InputController):
    """Read PlayStation-style gamepad inputs through SDL's standard controller mapping."""

    def __init__(self, x_step_size=1.0, y_step_size=1.0, z_step_size=1.0, deadzone=0.1):
        super().__init__(x_step_size, y_step_size, z_step_size)
        self.deadzone = deadzone
        self.pygame = None
        self.controller_api = None
        self.controller = None
        self.previous_buttons = {}

    def start(self):
        """Initialize SDL's mapped controller API and connect a supported gamepad."""
        import pygame
        from pygame._sdl2 import controller

        self.pygame = pygame
        self.controller_api = controller
        pygame.init()
        controller.init()

        joystick_count = controller.get_count()
        controller_indices = [index for index in range(joystick_count) if controller.is_controller(index)]
        if not controller_indices:
            logging.error("No SDL game controller detected. Connect a DualShock 4 and try again.")
            self.running = False
            return

        preferred_names = ("dualshock", "ps4", "playstation", "wireless controller")
        selected_index = next(
            (
                index
                for index in controller_indices
                if any(name in (controller.name_forindex(index) or "").lower() for name in preferred_names)
            ),
            controller_indices[0],
        )
        self.controller = controller.Controller(selected_index)
        logging.info("Initialized gamepad: %s", controller.name_forindex(selected_index))

        self.previous_buttons = {
            "success": False,
            "failure": False,
            "rerecord": False,
        }

        print("DualShock 4 controls:")
        print("  Left stick: Move in X-Y plane")
        print("  Right stick vertical: Move in Z axis")
        print("  Triangle: End episode with SUCCESS")
        print("  Cross: End episode with FAILURE")
        print("  Square: Rerecord episode")
        print("  R1: Take over from the policy")
        print("  L2 / R2: Close / open gripper")

    def stop(self):
        """Close the controller and release pygame resources."""
        if self.controller is not None:
            self.controller.quit()
            self.controller = None
        if self.controller_api is not None and self.controller_api.get_init():
            self.controller_api.quit()
        if self.pygame is not None:
            self.pygame.quit()

    @staticmethod
    def _normalize_stick_axis(value):
        """Normalize an SDL signed 16-bit stick axis to [-1, 1]."""
        value = int(value)
        return value / 32768.0 if value < 0 else value / 32767.0

    @staticmethod
    def _normalize_trigger(value):
        """Normalize an SDL trigger axis to [0, 1]."""
        return max(0.0, min(1.0, int(value) / 32767.0))

    def update(self):
        """Poll mapped DualShock buttons and analog triggers."""
        if self.controller is None or not self.running:
            return

        api = self.controller_api
        self.pygame.event.pump()
        try:
            button_states = {
                "success": bool(self.controller.get_button(api.CONTROLLER_BUTTON_Y)),
                "failure": bool(self.controller.get_button(api.CONTROLLER_BUTTON_A)),
                "rerecord": bool(self.controller.get_button(api.CONTROLLER_BUTTON_X)),
            }

            if button_states["success"] and not self.previous_buttons["success"]:
                self.episode_end_status = TeleopEvents.SUCCESS
            elif button_states["failure"] and not self.previous_buttons["failure"]:
                self.episode_end_status = TeleopEvents.FAILURE
            elif button_states["rerecord"] and not self.previous_buttons["rerecord"]:
                self.episode_end_status = TeleopEvents.RERECORD_EPISODE
            self.previous_buttons = button_states

            self.intervention_flag = bool(self.controller.get_button(api.CONTROLLER_BUTTON_RIGHTSHOULDER))
            self.close_gripper_command = (
                self._normalize_trigger(self.controller.get_axis(api.CONTROLLER_AXIS_TRIGGERLEFT)) > 0.5
            )
            self.open_gripper_command = (
                self._normalize_trigger(self.controller.get_axis(api.CONTROLLER_AXIS_TRIGGERRIGHT)) > 0.5
            )
        except self.pygame.error:
            logging.error("Error reading gamepad. Is it still connected?")
            self.running = False
            self.intervention_flag = False
            self.close_gripper_command = False
            self.open_gripper_command = False

    def get_deltas(self):
        """Return XYZ movement deltas from the DualShock sticks."""
        if self.controller is None or not self.running:
            return 0.0, 0.0, 0.0

        api = self.controller_api
        left_x = self._normalize_stick_axis(self.controller.get_axis(api.CONTROLLER_AXIS_LEFTX))
        left_y = self._normalize_stick_axis(self.controller.get_axis(api.CONTROLLER_AXIS_LEFTY))
        right_y = self._normalize_stick_axis(self.controller.get_axis(api.CONTROLLER_AXIS_RIGHTY))

        left_x = 0.0 if abs(left_x) < self.deadzone else left_x
        left_y = 0.0 if abs(left_y) < self.deadzone else left_y
        right_y = 0.0 if abs(right_y) < self.deadzone else right_y

        delta_x = -left_y * self.x_step_size
        delta_y = -left_x * self.y_step_size
        delta_z = -right_y * self.z_step_size
        return delta_x, delta_y, delta_z
