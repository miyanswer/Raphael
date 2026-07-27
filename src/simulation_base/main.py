import os
import sys
import numpy as np
from simulation.course import CourseGenerator
from simulation.robot import DifferentialDriveRobot
from simulation.node_manager import NodeManager
from simulation.camera_simulator import CameraSimulator
from simulation.visualizer import Visualizer
from simulation import config

def main():
    # Step 2: コース生成
    cg = CourseGenerator(config.SEGMENTS)
    course_points = cg.generate_course_points()
    node_positions = cg.generate_node_positions()
    left_boundary, right_boundary = cg.generate_boundary_points(course_points)

    # Step 3: 各モジュール初期化
    start_pos = node_positions["N02"]  # スタート地点 (L1中心)
    robot = DifferentialDriveRobot(start_pos[0], start_pos[1], start_theta=0.0)
    node_manager = NodeManager(node_positions)
    camera_sim = CameraSimulator(seed=42)
    visualizer = Visualizer(course_points, node_positions, left_boundary, right_boundary)

    # 状態変数の初期化
    frame_index = 0
    total_frames = len(course_points) - 1
    lap_logged = False

    # Step 4: Panda3D用更新タスクの定義
    def simulation_task(task):
        nonlocal frame_index, lap_logged

        # アニメーション終端に達したら、終了させずにインデックスをリセットする
        if frame_index >= total_frames:
            print("[INFO] Lap finished. Restarting for infinite loop...")
            frame_index = 0  # フレームインデックスを初期化して再スタート

        # ロボット・自己位置状態の更新
        robot.update_along_course(course_points, frame_index)
        node_result = node_manager.update(robot.x, robot.y)
        segment_id = node_manager.get_current_segment_id()
        features = camera_sim.get_features(segment_id, cg)

        # 3Dモデルの位置・姿勢更新
        visualizer.robot_node.setPos(robot.x, robot.y, 0.1)
        # Headingの更新（Panda3D基準: H = theta_deg - 90）
        visualizer.robot_node.setHpr(np.degrees(robot.theta) - 90.0, 0, 0)

        # カメラ視点の更新
        visualizer.update_camera(robot.x, robot.y, robot.theta)

        # ラップ完了判定
        if node_manager.is_lap_completed() and not lap_logged:
            log_path = os.path.join(config.LOG_DIR, config.LOG_FILENAME)
            node_manager.export_log(log_path)
            print(f"[SUCCESS] LAP COMPLETED! Log saved to {log_path}")
            lap_logged = True

        frame_index += 1
        return task.cont

    # Step 5: アニメーション起動
    print(f"Starting 3D simulation animation ({total_frames} frames)...")
    visualizer.taskMgr.add(simulation_task, "simulation_task")
    visualizer.run()

if __name__ == "__main__":
    main()
