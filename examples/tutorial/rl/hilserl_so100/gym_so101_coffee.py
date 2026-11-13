"""Gymnasium environment for the SO-101 coffee-cup HIL-SERL example."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces


def _scene_builder():
    path = Path(__file__).with_name("simulate_so101_coffee.py")
    spec = importlib.util.spec_from_file_location("so101_coffee_scene", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SO101CoffeeEnv(gym.Env):
    """Cartesian delta control, two RGB cameras, and sugar-in-cup success reward."""

    metadata = {"render_modes": ["rgb_array", "human"], "render_fps": 10}

    def __init__(self, image_obs=True, render_mode="rgb_array", width=128, height=128, **_kwargs):
        super().__init__()
        builder = _scene_builder()
        scene = builder.DEFAULT_SCENE
        if not scene.is_file():
            raise FileNotFoundError(f"SO-101 scene is missing: {scene}; clone TheRobotStudio/SO-ARM100")
        self.model = builder.build_model(scene)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = 0.002
        self.dt = 0.1
        self.substeps = 50
        self.render_mode = render_mode
        self.image_obs = image_obs
        self.width, self.height = width, height
        self.renderer = None
        self.joint_names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
        self.joint_ids = np.array([self.model.joint(n).id for n in self.joint_names])
        self.qpos_ids = np.array([self.model.jnt_qposadr[i] for i in self.joint_ids])
        self.dof_ids = np.array([self.model.jnt_dofadr[i] for i in self.joint_ids[:5]])
        self.actuator_ids = np.array([self.model.actuator(n).id for n in self.joint_names])
        self.ee_body = self.model.body("gripper").id
        self.sugar_joint = self.model.joint("sugar_block_free").id
        self.sugar_qpos = self.model.jnt_qposadr[self.sugar_joint]
        self.cup_body = self.model.body("paper_cup").id
        self.camera_ids = [self.model.camera(n).id for n in ("front_camera", "wrist_camera")]
        self.action_space = spaces.Box(-1.0, 1.0, shape=(7,), dtype=np.float32)
        obs_spaces = {"agent_pos": spaces.Box(-np.inf, np.inf, shape=(18,), dtype=np.float32)}
        if image_obs:
            obs_spaces["pixels"] = spaces.Dict({
                name: spaces.Box(0, 255, (height, width, 3), dtype=np.uint8)
                for name in ("front", "wrist")
            })
        self.observation_space = spaces.Dict(obs_spaces)
        self._max_steps = 300
        self._steps = 0

    def _observation(self):
        q = self.data.qpos[self.qpos_ids].astype(np.float32)
        v = self.data.qvel[self.dof_ids].astype(np.float32)
        ee = self.data.xpos[self.ee_body].astype(np.float32)
        sugar = self.data.qpos[self.sugar_qpos:self.sugar_qpos + 3].astype(np.float32)
        state = np.concatenate((q, np.pad(v, (0, 1)), ee, sugar)).astype(np.float32)
        result = {"agent_pos": state}
        if self.image_obs:
            if self.renderer is None:
                self.renderer = mujoco.Renderer(self.model, height=self.height, width=self.width)
            images = {}
            for name, cam_id in zip(("front", "wrist"), self.camera_ids, strict=True):
                self.renderer.update_scene(self.data, camera=cam_id)
                images[name] = self.renderer.render().copy()
            result["pixels"] = images
        return result

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.qpos_ids] = [0.0, -0.25, 0.65, -0.4, 0.0, 0.35]
        self.data.ctrl[self.actuator_ids] = self.data.qpos[self.qpos_ids]
        self.data.qpos[self.sugar_qpos:self.sugar_qpos + 3] = [0.14, 0.13, 0.009]
        mujoco.mj_forward(self.model, self.data)
        self._steps = 0
        return self._observation(), {}

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        target = self.data.xpos[self.ee_body].copy() + action[:3]
        target = np.clip(target, [-0.02, -0.32, 0.035], [0.38, 0.32, 0.40])
        jacp = np.zeros((3, self.model.nv)); jacr = np.zeros((3, self.model.nv))
        mujoco.mj_jac(self.model, self.data, jacp, jacr, self.data.xpos[self.ee_body], self.ee_body)
        delta = target - self.data.xpos[self.ee_body]
        dq = jacp[:, self.dof_ids].T @ np.linalg.solve(jacp[:, self.dof_ids] @ jacp[:, self.dof_ids].T + 1e-4*np.eye(3), delta)
        target_q = self.data.qpos[self.qpos_ids[:5]] + np.clip(dq, -0.08, 0.08)
        self.data.ctrl[self.actuator_ids[:5]] = target_q
        grip_range = self.model.actuator_ctrlrange[self.actuator_ids[5]]
        self.data.ctrl[self.actuator_ids[5]] = np.clip(
            self.data.ctrl[self.actuator_ids[5]] + action[6] * 0.04, *grip_range
        )
        for _ in range(self.substeps):
            mujoco.mj_step(self.model, self.data)
        self._steps += 1
        sugar = self.data.qpos[self.sugar_qpos:self.sugar_qpos + 3]
        cup = self.data.xpos[self.cup_body]
        sugar_height = sugar[2] - cup[2]
        success = np.linalg.norm(sugar[:2] - cup[:2]) < 0.027 and 0.025 < sugar_height < 0.085
        obs = self._observation()
        return obs, float(success), bool(success), self._steps >= self._max_steps, {"success": bool(success)}

    def get_gripper_pose(self):
        lo, hi = self.model.actuator_ctrlrange[self.actuator_ids[5]]
        pos = self.data.ctrl[self.actuator_ids[5]]
        return np.array([(pos - lo) / (hi - lo) * 255.0], dtype=np.float32)

    def render(self):
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=self.height, width=self.width)
        self.renderer.update_scene(self.data, camera=self.camera_ids[0])
        return [self.renderer.render().copy()]

    def close(self):
        if self.renderer is not None:
            self.renderer.close()


def make_so101_coffee(**kwargs):
    from gym_hil.wrappers.factory import wrap_env

    env = SO101CoffeeEnv(**{k: v for k, v in kwargs.items() if k in {"image_obs", "render_mode"}})
    return wrap_env(env, ee_step_size={"x": 0.01, "y": 0.01, "z": 0.01},
                    use_viewer=kwargs.get("render_mode") == "human", use_inputs_control=True,
                    use_gripper=True, gripper_penalty=kwargs.get("gripper_penalty", -0.02),
                    reset_delay_seconds=0.0)
