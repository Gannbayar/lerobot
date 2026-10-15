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
    """Load the SO-101 scene and add cup, coffee, and sugar on its ground."""
    spec = mujoco.MjSpec.from_file(str(scene_path.expanduser()))
    world = spec.worldbody

    # Dimensions supplied by the user: 73 mm top, 50 mm bottom, 80 mm tall.
    cup_height = 0.080
    bottom_radius = 0.025
    top_radius = 0.0365
    wall_thickness = 0.0015

    # A lightweight paper cup resting on the scene's existing ground plane.
    cup = world.add_body(name="paper_cup", pos=[0.25, -0.04, 0.0])
    cup.add_freejoint(name="paper_cup_free")
    cup.add_geom(
        name="cup_bottom",
        type=mujoco.mjtGeom.mjGEOM_CYLINDER,
        pos=[0.0, 0.0, 0.0015],
        size=[bottom_radius - wall_thickness, 0.0015],
        density=450.0,
        rgba=[0.95, 0.94, 0.88, 1.0],
    )

    # MuJoCo has no tapered-cylinder primitive. Small stacked polygon bands
    # approximate the measured paper-cup taper while retaining collisions.
    wall_count = 16
    wall_sections = 12
    wall_start_z = 0.003
    section_height = (cup_height - wall_start_z) / wall_sections
    for index in range(wall_count):
        angle = 2.0 * math.pi * index / wall_count
        for section in range(wall_sections):
            z = wall_start_z + (section + 0.5) * section_height
            outer_radius = bottom_radius + (top_radius - bottom_radius) * (z / cup_height)
            segment_half_length = outer_radius * math.sin(math.pi / wall_count)
            apothem = outer_radius * math.cos(math.pi / wall_count)
            wall_center_radius = apothem - wall_thickness / 2.0
            cup.add_geom(
                name=f"cup_wall_{index}_{section}",
                type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=[wall_center_radius * math.cos(angle), wall_center_radius * math.sin(angle), z],
                euler=[0.0, 0.0, angle + math.pi / 2.0],
                size=[segment_half_length, wall_thickness, section_height / 2.0 + 0.0001],
                density=450.0,
                rgba=[0.95, 0.94, 0.88, 1.0],
            )

    # A brown rigid cylinder makes the coffee visible; it does not slosh or spill.
    cup.add_geom(
        name="coffee_surface",
        type=mujoco.mjtGeom.mjGEOM_CYLINDER,
        pos=[0.0, 0.0, 0.037],
        size=[0.027, 0.020],
        density=950.0,
        rgba=[0.20, 0.075, 0.025, 1.0],
    )

    sugar = world.add_body(name="sugar_block", pos=[0.39, 0.11, 0.009])
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
    print("SO-101 coffee scene ready (no table). Use the MuJoCo Control panel to move the joints; close the viewer to exit.")
    mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
