#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
シミュレータ本体ノード
- Subscribe: /cmd_vel (geometry_msgs/Twist)
- Publish: 
  - /camera/image_raw (sensor_msgs/Image) - 車載カメラ(FPV)
  - /camera/birdseye_image_raw (sensor_msgs/Image) - 全体鳥瞰図(Bird's Eye Color)
  - /odom (nav_msgs/Odometry)
- 30Hz 物理計算 & レンダリングループ
- L1（5m直線）中央へのスポーン
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from cv_bridge import CvBridge

import numpy as np
from hirakata_simulation import course_generator
from hirakata_simulation.robot_physics import RobotPhysics
from hirakata_simulation.camera_renderer import CameraRenderer

class SimulatorNode(Node):
    def __init__(self):
        super().__init__('simulator_node')

        # ROS 2 通信設定
        self.sub_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.pub_image = self.create_publisher(Image, '/camera/image_raw', 10)
        self.pub_birdseye = self.create_publisher(Image, '/camera/birdseye_image_raw', 10)
        self.pub_odom = self.create_publisher(Odometry, '/odom', 10)

        self.cv_bridge = CvBridge()

        # 物理モデル & 描画エンジンの初期化
        self.physics = RobotPhysics(track_width=0.55, mass=40.0, inertia_tau=0.1, slip_ratio=0.02)
        self.renderer = CameraRenderer(width=640, height=480, fov=90.0)

        # スポーン位置設定: L1（5m直線）中央、反時計回り方向
        spawn_x, spawn_y, spawn_yaw = course_generator.get_l1_spawn_pose()
        self.physics.set_pose(spawn_x, spawn_y, spawn_yaw)

        self.cmd_v = 0.0
        self.cmd_w = 0.0

        # 30 FPS タイマー (33.3ms)
        self.dt = 1.0 / 30.0
        self.timer = self.create_timer(self.dt, self.update_loop)

        self.get_logger().info("SimulatorNode initialized successfully. AGV spawned at L1 center.")

    def cmd_vel_callback(self, msg: Twist):
        self.cmd_v = msg.linear.x
        self.cmd_w = msg.angular.z

    def update_loop(self):
        # 1. 物理更新
        x, y, yaw, v_act, w_act = self.physics.update(self.cmd_v, self.cmd_w, self.dt)

        # 2. オドメトリ Publish
        now = self.get_clock().now().to_msg()
        odom_msg = Odometry()
        odom_msg.header.stamp = now
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'

        odom_msg.pose.pose.position.x = float(x)
        odom_msg.pose.pose.position.y = float(y)
        odom_msg.pose.pose.position.z = 0.0

        # Yaw -> Quaternion
        odom_msg.pose.pose.orientation.z = float(np.sin(yaw / 2.0))
        odom_msg.pose.pose.orientation.w = float(np.cos(yaw / 2.0))

        odom_msg.twist.twist.linear.x = float(v_act)
        odom_msg.twist.twist.angular.z = float(w_act)

        self.pub_odom.publish(odom_msg)

        # 3. 車載カメラ (FPV) レンダリング & Publish
        bgr_image = self.renderer.render_frame(x, y, yaw)
        img_msg = self.cv_bridge.cv2_to_imgmsg(bgr_image, encoding='bgr8')
        img_msg.header.stamp = now
        img_msg.header.frame_id = 'camera_frame'
        self.pub_image.publish(img_msg)

        # 4. 鳥瞰図カメラ (Bird's Eye) レンダリング & Publish
        bgr_birdseye = self.renderer.render_birdseye_frame(x, y, yaw)
        bird_msg = self.cv_bridge.cv2_to_imgmsg(bgr_birdseye, encoding='bgr8')
        bird_msg.header.stamp = now
        bird_msg.header.frame_id = 'birdseye_frame'
        self.pub_birdseye.publish(bird_msg)

def main(args=None):
    rclpy.init(args=args)
    node = SimulatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
