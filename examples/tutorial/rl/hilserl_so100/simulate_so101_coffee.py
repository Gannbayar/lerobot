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
    """Load the SO-101 scene and add the photographed work area and cameras."""
    spec = mujoco.MjSpec.from_file(str(scene_path.expanduser()))
    world = spec.worldbody

    # The photographed mat is 550 mm wide by 400 mm deep. The shown 25 mm
    # checker spacing is an approximation based on the photos.
    # It is visual only; the official scene's floor remains the contact surface.
    mat_columns = 22
    mat_rows = 16
    mat_square = 0.025
    # The mat's near edge sits flush with the rear edge of the robot base plate.
    # Relative to the previous layout, the robot is 50 mm farther forward.
    mat_center_x = 0.175
    mat_center_y = 0.0
    for column in range(mat_columns):
        for row in range(mat_rows):
            is_blue = (column + row) % 2 == 0
            world.add_geom(
                name=f"checker_mat_{column}_{row}",
                type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=[
                    mat_center_x + (row - (mat_rows - 1) / 2) * mat_square,
                    mat_center_y + (column - (mat_columns - 1) / 2) * mat_square,
                    0.00015,
                ],
                size=[mat_square / 2, mat_square / 2, 0.00015],
                contype=0,
                conaffinity=0,
                rgba=[0.02, 0.37, 0.78, 1.0] if is_blue else [0.012, 0.016, 0.023, 1.0],
            )

    # The layout diagram gives camera offsets from the robot base in top view:
    # horizontal is the robot's lateral axis and down-page points along +X.
    camera_focus = world.add_body(name="camera_focus", pos=[mat_center_x, mat_center_y, 0.035])

    def add_layout_camera(
        name: str, lateral_mm: float, forward_mm: float, height_mm: float, fovy: float
    ) -> None:
        camera = world.add_camera(
            name=name,
            pos=[forward_mm / 1000.0, lateral_mm / 1000.0, height_mm / 1000.0],
            fovy=fovy,
        )
        camera.mode = mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY
        camera.targetbody = "camera_focus"

    # Aim each fixed camera at the work area. MuJoCo computes its downward tilt
    # from this target and the measured camera position.
    add_layout_camera(
        "robot_camera", lateral_mm=65, forward_mm=55, height_mm=610, fovy=58
    )
    add_layout_camera(
        "side_camera", lateral_mm=-385, forward_mm=220, height_mm=440, fovy=60
    )
    add_layout_camera(
        "front_camera", lateral_mm=400, forward_mm=140, height_mm=125, fovy=75
    )

    # A wrist-mounted viewpoint follows the moving gripper and keeps the work
    # area in view, like a close-up camera mounted near the robot's hand.
    gripper = spec.body("gripper")
    gripper.add_camera(
        name="wrist_camera",
        pos=[0.0, 0.035, 0.035],
        mode=mujoco.mjtCamLight.mjCAMLIGHT_TARGETBODY,
        targetbody="camera_focus",
        fovy=70.0,
    )

    # Dimensions supplied by the user: 73 mm top, 50 mm bottom, 80 mm tall.
    cup_height = 0.080
    bottom_radius = 0.025
    top_radius = 0.0365
    wall_thickness = 0.0015

    # A lightweight paper cup resting on the scene's existing ground plane.
    cup = world.add_body(name="paper_cup", pos=[0.24, -0.13, 0.0])
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

    sugar = world.add_body(name="sugar_block", pos=[0.14, 0.13, 0.009])
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
    print(
        "SO-101 coffee scene ready. Use Control to move the joints and the Camera menu "
        "to choose wrist_camera, robot_camera, side_camera, or front_camera; "
        "close the viewer to exit."
    )
    mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
