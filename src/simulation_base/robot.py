import numpy as np
from simulation import config

class DifferentialDriveRobot:
    def __init__(self, start_x, start_y, start_theta=0.0):
        self.x = float(start_x)
        self.y = float(start_y)
        self.theta = float(start_theta)
        self.speed = float(config.ROBOT_SPEED)
        self.odom_distance = 0.0

    def update_along_course(self, course_points, step_index):
        """
        コース座標列全体 + 現在のステップインデックスから状態量を更新する。
        """
        if step_index < len(course_points) - 1:
            next_pt = course_points[step_index + 1]
            dx = next_pt[0] - self.x
            dy = next_pt[1] - self.y
            self.x = float(next_pt[0])
            self.y = float(next_pt[1])
            self.theta = float(np.arctan2(dy, dx))
            self.odom_distance += float(np.sqrt(dx**2 + dy**2))
        elif step_index == len(course_points) - 1:
            # 最終ステップの場合は現在位置維持
            pass

    def inject_slip(self, slip_distance):
        """
        将来拡張用: odom_distance に slip_distance を加算（スリップ誤差シミュレート）
        """
        self.odom_distance += float(slip_distance)

    def get_state(self):
        return {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "odom": self.odom_distance
        }

    @property
    def position(self):
        return (self.x, self.y)
