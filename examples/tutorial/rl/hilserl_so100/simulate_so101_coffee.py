#!/usr/bin/env python3
"""Open an SO-101 MuJoCo scene with a paper cup, coffee, and a sugar cube.

The robot model is loaded from the official SO-ARM100 repository. The coffee is
represented as a rigid cylinder, not a fluid simulation.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import mujoco
import mujoco.viewer


DEFAULT_SCENE = Path.home() / "SO-ARM100/Simulation/SO101/scene.xml"


def build_model(scene_path: Path) -> mujoco.MjModel:
    """Load the SO-101 scene and add a small table-top coffee task."""
    spec = mujoco.MjSpec.from_file(str(scene_path.expanduser()))
    world = spec.worldbody

    # The table rests on the scene's existing ground plane.
    world.add_geom(
        name="coffee_table",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0.34, 0.0, 0.035],
        size=[0.20, 0.22, 0.035],
        rgba=[0.42, 0.30, 0.20, 1.0],
        friction=[1.0, 0.005, 0.0001],
    )

    # A lightweight paper cup approximated by eight wall panels and a bottom.
    cup = world.add_body(name="paper_cup", pos=[0.25, -0.04, 0.07])
    cup.add_freejoint(name="paper_cup_free")
    cup.add_geom(
        name="cup_bottom",
        type=mujoco.mjtGeom.mjGEOM_CYLINDER,
        pos=[0.0, 0.0, 0.0025],
        size=[0.033, 0.0025],
        density=450.0,
        rgba=[0.95, 0.94, 0.88, 1.0],
    )

    wall_count = 8
    outer_radius = 0.035
    wall_thickness = 0.002
    wall_half_height = 0.043
    segment_half_length = outer_radius * math.tan(math.pi / wall_count) * 1.02
    for index in range(wall_count):
        angle = 2.0 * math.pi * index / wall_count
        cup.add_geom(
            name=f"cup_wall_{index}",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[outer_radius * math.cos(angle), outer_radius * math.sin(angle), wall_half_height],
            euler=[0.0, 0.0, angle + math.pi / 2.0],
            size=[segment_half_length, wall_thickness, wall_half_height],
            density=450.0,
            rgba=[0.95, 0.94, 0.88, 1.0],
        )

    # A brown rigid cylinder makes the coffee visible; it does not slosh or spill.
    cup.add_geom(
        name="coffee_surface",
        type=mujoco.mjtGeom.mjGEOM_CYLINDER,
        pos=[0.0, 0.0, 0.045],
        size=[0.028, 0.022],
        density=950.0,
        rgba=[0.20, 0.075, 0.025, 1.0],
    )

    sugar = world.add_body(name="sugar_block", pos=[0.39, 0.11, 0.08])
    sugar.add_freejoint(name="sugar_block_free")
    sugar.add_geom(
        name="sugar_cube",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[0.009, 0.009, 0.009],
        density=700.0,
        rgba=[0.98, 0.94, 0.79, 1.0],
    )

    return spec.compile()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scene",
        type=Path,
        default=DEFAULT_SCENE,
        help=f"Path to the official SO-101 scene (default: {DEFAULT_SCENE})",
    )
    args = parser.parse_args()
    scene_path = args.scene.expanduser()
    if not scene_path.is_file():
        raise SystemExit(
            f"SO-101 scene not found: {scene_path}\n"
            "Clone TheRobotStudio/SO-ARM100 or pass its Simulation/SO101/scene.xml path with --scene."
        )

    model = build_model(scene_path)
    data = mujoco.MjData(model)
    print("SO-101 coffee scene ready. Use the MuJoCo Control panel to move the joints; close the viewer to exit.")
    mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
