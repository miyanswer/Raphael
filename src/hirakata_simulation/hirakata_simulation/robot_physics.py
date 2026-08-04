#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中型AGV（トレッド幅 50〜60cm）の差動二輪運動学および標準グリップ（スリップ・慣性）計算モジュール
"""

import numpy as np

class RobotPhysics:
    def __init__(self, track_width=0.55, mass=40.0, inertia_tau=0.1, slip_ratio=0.02):
        """
        :param track_width: トレッド幅 [m] (50〜60cm、デフォルト 0.55m)
        :param mass: 車体重体 [kg]
        :param inertia_tau: 速度レスポンスの一次遅れ時定数 [s]
        :param slip_ratio: 微小スリップ係数（標準グリップ相当）
        """
        self.track_width = track_width
        self.mass = mass
        self.tau = inertia_tau
        self.slip_ratio = slip_ratio

        # 状態変数 [x, y, yaw, v_act, w_act]
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.v_act = 0.0
        self.w_act = 0.0

    def set_pose(self, x, y, yaw):
        self.x = x
        self.y = y
        self.yaw = yaw
        self.v_act = 0.0
        self.w_act = 0.0

    def update(self, v_target, w_target, dt):
        """
        /cmd_vel の目標値 (v_target, w_target) に基づき一次遅れ＋スリップを適用して状態更新
        """
        # 一次遅れレスポンス（慣性）
        alpha = dt / (self.tau + dt)
        self.v_act += alpha * (v_target - self.v_act)
        self.w_act += alpha * (w_target - self.w_act)

        # 標準グリップによる微小なスリップ（実効速度のわずかな減衰）
        v_eff = self.v_act * (1.0 - self.slip_ratio)
        w_eff = self.w_act * (1.0 - self.slip_ratio)

        # 差動二輪モデル運動学
        self.yaw += w_eff * dt
        # Yaw角正規化 [-pi, pi]
        self.yaw = (self.yaw + np.pi) % (2.0 * np.pi) - np.pi

        self.x += v_eff * np.cos(self.yaw) * dt
        self.y += v_eff * np.sin(self.yaw) * dt

        return self.x, self.y, self.yaw, self.v_act, self.w_act
