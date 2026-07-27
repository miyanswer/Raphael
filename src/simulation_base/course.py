import numpy as np
from simulation import config

STEP_SIZE = 0.02  # [m] 刻み幅

class CourseGenerator:
    def __init__(self, segments=None):
        self.segments = segments if segments is not None else config.SEGMENTS

    def generate_course_points(self):
        """
        config.SEGMENTS に基づいてコース座標列 (N, 2) を生成する。
        L1中心左端を原点 (0, 0) とする。
        """
        x, y = 0.0, 0.0
        theta = 0.0  # [rad]

        points = []

        for seg in self.segments:
            seg_type = seg["type"]

            if seg_type == "straight":
                length = seg["length"]
                num_steps = int(np.ceil(length / STEP_SIZE))
                actual_step = length / num_steps if num_steps > 0 else 0
                dx = actual_step * np.cos(theta)
                dy = actual_step * np.sin(theta)

                for _ in range(num_steps):
                    points.append([x, y])
                    x += dx
                    y += dy

            elif seg_type == "arc":
                radius = seg["radius"]
                angle_deg = seg["angle_deg"]
                angle_rad = np.radians(angle_deg)
                direction = seg.get("direction", "right")

                arc_length = radius * angle_rad
                num_steps = int(np.ceil(arc_length / STEP_SIZE))
                d_alpha = angle_rad / num_steps if num_steps > 0 else 0

                if direction == "right":
                    # 旋回中心: theta - pi/2 方向
                    cx = x + radius * np.cos(theta - np.pi / 2.0)
                    cy = y + radius * np.sin(theta - np.pi / 2.0)
                    # 初期角度 (旋回中心から現在位置への角度)
                    start_angle = np.arctan2(y - cy, x - cx)

                    for step_i in range(num_steps):
                        cur_a = start_angle - step_i * d_alpha
                        px = cx + radius * np.cos(cur_a)
                        py = cy + radius * np.sin(cur_a)
                        points.append([px, py])

                    # 終端状態の更新
                    theta -= angle_rad
                    x = cx + radius * np.cos(start_angle - angle_rad)
                    y = cy + radius * np.sin(start_angle - angle_rad)

                else:  # left
                    cx = x + radius * np.cos(theta + np.pi / 2.0)
                    cy = y + radius * np.sin(theta + np.pi / 2.0)
                    start_angle = np.arctan2(y - cy, x - cx)

                    for step_i in range(num_steps):
                        cur_a = start_angle + step_i * d_alpha
                        px = cx + radius * np.cos(cur_a)
                        py = cy + radius * np.sin(cur_a)
                        points.append([px, py])

                    theta += angle_rad
                    x = cx + radius * np.cos(start_angle + angle_rad)
                    y = cy + radius * np.sin(start_angle + angle_rad)

        points.append([x, y])
        points_arr = np.array(points)

        return points_arr

    def generate_node_positions(self):
        """
        各区間の「入口点」「中心点」の座標を計算し N01〜N16 の辞書を返す。
        """
        node_positions = {}

        # 各区間の開始インデックスと点列を求める
        x, y = 0.0, 0.0
        theta = 0.0

        segment_info = []

        for seg in self.segments:
            seg_type = seg["type"]
            start_x, start_y = x, y

            if seg_type == "straight":
                length = seg["length"]
                num_steps = int(np.ceil(length / STEP_SIZE))
                actual_step = length / num_steps if num_steps > 0 else 0
                dx = actual_step * np.cos(theta)
                dy = actual_step * np.sin(theta)

                mid_x = start_x + (length / 2.0) * np.cos(theta)
                mid_y = start_y + (length / 2.0) * np.sin(theta)
                x += dx * num_steps
                y += dy * num_steps

            elif seg_type == "arc":
                radius = seg["radius"]
                angle_deg = seg["angle_deg"]
                angle_rad = np.radians(angle_deg)
                direction = seg.get("direction", "right")

                if direction == "right":
                    cx = x + radius * np.cos(theta - np.pi / 2.0)
                    cy = y + radius * np.sin(theta - np.pi / 2.0)
                    start_angle = np.arctan2(y - cy, x - cx)
                    mid_angle = start_angle - angle_rad / 2.0
                    mid_x = cx + radius * np.cos(mid_angle)
                    mid_y = cy + radius * np.sin(mid_angle)
                    theta -= angle_rad
                    x = cx + radius * np.cos(start_angle - angle_rad)
                    y = cy + radius * np.sin(start_angle - angle_rad)
                else:
                    cx = x + radius * np.cos(theta + np.pi / 2.0)
                    cy = y + radius * np.sin(theta + np.pi / 2.0)
                    start_angle = np.arctan2(y - cy, x - cx)
                    mid_angle = start_angle + angle_rad / 2.0
                    mid_x = cx + radius * np.cos(mid_angle)
                    mid_y = cy + radius * np.sin(mid_angle)
                    theta += angle_rad
                    x = cx + radius * np.cos(start_angle + angle_rad)
                    y = cy + radius * np.sin(start_angle + angle_rad)

            segment_info.append({
                "id": seg["id"],
                "start": (start_x, start_y),
                "mid": (mid_x, mid_y)
            })

        # N01 ~ N16 のマッピング
        # N01: L1入口, N02: L1中心, N03: C1入口, N04: C1頂点(中心), ...
        node_positions["N01"] = segment_info[0]["start"]  # L1 start
        node_positions["N02"] = segment_info[0]["mid"]    # L1 mid
        node_positions["N03"] = segment_info[1]["start"]  # C1 start
        node_positions["N04"] = segment_info[1]["mid"]    # C1 mid
        node_positions["N05"] = segment_info[2]["start"]  # L2 start
        node_positions["N06"] = segment_info[2]["mid"]    # L2 mid
        node_positions["N07"] = segment_info[3]["start"]  # C2 start
        node_positions["N08"] = segment_info[3]["mid"]    # C2 mid
        node_positions["N09"] = segment_info[4]["start"]  # L3 start
        node_positions["N10"] = segment_info[4]["mid"]    # L3 mid
        node_positions["N11"] = segment_info[5]["start"]  # C3 start
        node_positions["N12"] = segment_info[5]["mid"]    # C3 mid
        node_positions["N13"] = segment_info[6]["start"]  # L4 start
        node_positions["N14"] = segment_info[6]["mid"]    # L4 mid
        node_positions["N15"] = segment_info[7]["start"]  # C4 start
        node_positions["N16"] = segment_info[7]["mid"]    # C4 mid

        return node_positions

    def get_segment_curvature(self, segment_id):
        """
        区間ID文字列から曲率を返す。
        直線 = 0.0, 円弧 = 1.0 / radius
        """
        for seg in self.segments:
            if seg["id"] == segment_id:
                if seg["type"] == "straight":
                    return 0.0
                elif seg["type"] == "arc":
                    return 1.0 / seg["radius"]
        return 0.0

    def generate_boundary_points(self, course_points):
        """
        コース中心点列 course_points (N, 2) から、コース全幅 (config.COURSE_WIDTH) に基いて
        反時計回りの進行方向に対する外側 (left_boundary) と内側 (right_boundary) の境界線座標列を生成する。
        """
        n_points = len(course_points)
        tangents = np.zeros((n_points, 2))

        if n_points > 1:
            tangents[0] = course_points[1] - course_points[0]
            tangents[-1] = course_points[-1] - course_points[-2]
            if n_points > 2:
                tangents[1:-1] = course_points[2:] - course_points[:-2]

        normals = np.zeros((n_points, 2))
        for i in range(n_points):
            dx, dy = tangents[i]
            norm = np.hypot(dx, dy)
            if norm < 1e-9:
                norm = 1.0
            # 進行方向 (dx, dy) に対して左に90度回転した法線 (-dy, dx)
            normals[i] = [-dy / norm, dx / norm]

        # 法線ベクトルの移動平均によるスムージング (A案: 窓幅 W=BOUNDARY_SMOOTH_WINDOW)
        w_size = getattr(config, "BOUNDARY_SMOOTH_WINDOW", 50)
        if w_size > 1 and n_points >= w_size:
            kernel = np.ones(w_size) / float(w_size)
            nx_smooth = np.convolve(normals[:, 0], kernel, mode='same')
            ny_smooth = np.convolve(normals[:, 1], kernel, mode='same')

            # 再単位化（長さ=1に標準化）
            lengths = np.hypot(nx_smooth, ny_smooth)
            lengths = np.where(lengths < 1e-9, 1.0, lengths)

            normals[:, 0] = nx_smooth / lengths
            normals[:, 1] = ny_smooth / lengths

        half_width = config.COURSE_WIDTH / 2.0
        left_boundary = course_points + half_width * normals
        right_boundary = course_points - half_width * normals

        return left_boundary, right_boundary

