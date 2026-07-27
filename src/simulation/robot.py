import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from simulation import config

class DifferentialDriveRobot(Node):
    def __init__(self, start_x, start_y, start_theta=0.0):
        super().__init__('sim_robot_node')
        self.x = float(start_x)
        self.y = float(start_y)
        self.theta = float(start_theta)
        self.odom_distance = 0.0

        # ROS 2 コマンド速度
        self.cmd_v = 0.0
        self.cmd_w = 0.0

        # Subscriptions
        self.cmd_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self._cb_cmd_vel,
            10
        )

    def _cb_cmd_vel(self, msg: Twist):
        """ROS 2 /cmd_vel 受信"""
        self.cmd_v = msg.linear.x
        self.cmd_w = msg.angular.z

    def update_physics(self, dt):
        """速度・角速度コマンドに基づいて自律オドメトリ物理移動"""
        self.theta += self.cmd_w * dt
        dx = self.cmd_v * np.cos(self.theta) * dt
        dy = self.cmd_v * np.sin(self.theta) * dt
        self.x += dx
        self.y += dy
        self.odom_distance += float(np.hypot(dx, dy))

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
