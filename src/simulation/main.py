import os
import sys
import numpy as np
import rclpy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from simulation.course import CourseGenerator
from simulation.robot import DifferentialDriveRobot
from simulation.node_manager import NodeManager
from simulation.visualizer import Visualizer
from simulation import config

def main():
    # ROS 2 初期化
    rclpy.init(args=sys.argv)

    # Step 2: コース生成
    cg = CourseGenerator(config.SEGMENTS)
    course_points = cg.generate_course_points()
    node_positions = cg.generate_node_positions()
    left_boundary, right_boundary = cg.generate_boundary_points(course_points)

    # Step 3: 各モジュール初期化
    start_pos = node_positions["N02"]  # スタート地点 (L1中心)
    robot = DifferentialDriveRobot(start_pos[0], start_pos[1], start_theta=0.0)
    node_manager = NodeManager(node_positions)
    visualizer = Visualizer(course_points, node_positions, left_boundary, right_boundary)

    # ROS 2 パブリッシャ & CvBridge
    image_pub = robot.create_publisher(Image, '/camera/image_raw', 10)
    bridge = CvBridge()

    lap_logged = False

    # Step 4: Panda3D用更新タスクの定義
    def simulation_task(task):
        nonlocal lap_logged

        # ROS 2 イベント処理（/cmd_vel 受信など）
        rclpy.spin_once(robot, timeout_sec=0.0)

        # 自律物理移動更新
        robot.update_physics(config.SIMULATION_DT)

        # 3Dモデルの位置・姿勢更新
        visualizer.robot_node.setPos(robot.x, robot.y, 0.1)
        visualizer.robot_node.setHpr(np.degrees(robot.theta) - 90.0, 0, 0)

        # カメラ視点の更新
        visualizer.update_camera(robot.x, robot.y, robot.theta)

        # 仮想カメラ画像の取得 & /camera/image_raw パブリッシュ
        img_bgr = visualizer.get_camera_image()
        if img_bgr is not None:
            try:
                img_msg = bridge.cv2_to_imgmsg(img_bgr, encoding='bgr8')
                img_msg.header.stamp = robot.get_clock().now().to_msg()
                img_msg.header.frame_id = 'camera_link'
                image_pub.publish(img_msg)
            except Exception as e:
                pass

        # ノードマネージャ更新 & ラップ完了判定
        node_manager.update(robot.x, robot.y)
        if node_manager.is_lap_completed() and not lap_logged:
            log_path = os.path.join(config.LOG_DIR, config.LOG_FILENAME)
            node_manager.export_log(log_path)
            print(f"[SUCCESS] LAP COMPLETED! Log saved to {log_path}")
            lap_logged = True

        return task.cont

    # Step 5: アニメーション起動
    print("Starting ROS 2 Autonomous 3D Simulation...")
    visualizer.taskMgr.add(simulation_task, "simulation_task")
    try:
        visualizer.run()
    finally:
        robot.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
