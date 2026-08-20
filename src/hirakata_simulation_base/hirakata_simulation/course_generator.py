#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
段差ゼロメッシュコース生成モジュール
コース仕様:
- 床面: RGB(177, 170, 164), 幅 31m x 奥行 19m
- 白線: RGB(255, 255, 255), 幅 5cm (0.05m)
- 形状: 外幅15m x 外奥行き10m (直線 5m x 2, 10m x 2, R2.5m 角丸長方形)
- 原点 (0, 0) を中心とし、完全左右対称・上下対称に配置
"""

import numpy as np

COURSE_WIDTH_X = 15.0
COURSE_LENGTH_Y = 10.0
CORNER_RADIUS = 2.5
LINE_WIDTH = 0.05

FLOOR_COLOR = (177 / 255.0, 170 / 255.0, 164 / 255.0)
LINE_COLOR = (1.0, 1.0, 1.0)
SKY_COLOR = (30 / 255.0, 30 / 255.0, 40 / 255.0)

SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 5.0},
    {"id": "C4", "type": "arc",      "radius": 2.5, "angle_deg": 90, "direction": "right"},
    {"id": "L4", "type": "straight", "length": 10.0},
    {"id": "C3", "type": "arc",      "radius": 2.5, "angle_deg": 90, "direction": "right"},
    {"id": "L3", "type": "straight", "length": 5.0},
    {"id": "C2", "type": "arc",      "radius": 2.5, "angle_deg": 90, "direction": "right"},
    {"id": "L2", "type": "straight", "length": 10.0},
    {"id": "C1", "type": "arc",      "radius": 2.5, "angle_deg": 90, "direction": "right"},
]

def generate_course_centerline_points(step_size=0.02):
    """
    コースの中心線座標 (N, 2) および法線 (N, 2) を高精度に生成する。
    L1南端 (X=-7.5m, Y=-2.5m) を起点とし、L1北向き (+Y) に進行。
    原点 (0, 0) を真中心とする完全対称コース [X: -7.5~+7.5, Y: -5.0~+5.0]
    """
    cx_offset = (COURSE_WIDTH_X / 2.0) - CORNER_RADIUS  # 5.0
    cy_offset = (COURSE_LENGTH_Y / 2.0) - CORNER_RADIUS # 2.5

    x = - (cx_offset + CORNER_RADIUS) # -7.5
    y = - cy_offset                    # -2.5
    theta = np.pi / 2.0                # +Y (北向き)

    points = []
    normals = []

    for seg in SEGMENTS:
        seg_type = seg["type"]

        if seg_type == "straight":
            length = seg["length"]
            num_steps = max(1, int(np.round(length / step_size)))
            actual_step = length / num_steps
            
            # 進行方向の単位ベクトルと左法線ベクトル
            dir_x, dir_y = np.cos(theta), np.sin(theta)
            nx, ny = -dir_y, dir_x  # 左法線 (+90 deg)

            for i in range(num_steps):
                px = x + i * actual_step * dir_x
                py = y + i * actual_step * dir_y
                points.append([px, py])
                normals.append([nx, ny])

            x += length * dir_x
            y += length * dir_y

        elif seg_type == "arc":
            radius = seg["radius"]
            angle_deg = seg["angle_deg"]
            angle_rad = np.radians(angle_deg)
            direction = seg.get("direction", "right")

            arc_length = radius * angle_rad
            num_steps = max(1, int(np.round(arc_length / step_size)))
            d_alpha = angle_rad / num_steps

            if direction == "right":
                # 右旋回: 旋回中心は進行方向の右側 (-90度方向)
                cx = x + radius * np.cos(theta - np.pi / 2.0)
                cy = y + radius * np.sin(theta - np.pi / 2.0)
                start_angle = np.arctan2(y - cy, x - cx)

                for i in range(num_steps):
                    cur_a = start_angle - i * d_alpha
                    px = cx + radius * np.cos(cur_a)
                    py = cy + radius * np.sin(cur_a)
                    points.append([px, py])
                    # 右折の場合、左法線は中心に向かうベクトル
                    normals.append([-np.cos(cur_a), -np.sin(cur_a)])

                theta -= angle_rad
                x = cx + radius * np.cos(start_angle - angle_rad)
                y = cy + radius * np.sin(start_angle - angle_rad)

    return np.array(points), np.array(normals)


def get_l1_spawn_pose():
    """
    5m直線（L1）の中央座標およびYaw角を返す。
    L1中央位置: X = -7.5m, Y = 0.0m, Yaw = -90度 (-π/2 rad, 南向き -Y方向)
    """
    cx_offset = (COURSE_WIDTH_X / 2.0) - CORNER_RADIUS  # 5.0
    spawn_x = - (cx_offset + CORNER_RADIUS)            # -7.5
    spawn_y = 0.0
    spawn_yaw = -np.pi / 2.0                           # 南向き (-Y方向)
    return spawn_x, spawn_y, spawn_yaw
