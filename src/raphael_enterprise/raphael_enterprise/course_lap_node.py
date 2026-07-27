#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ビジュアルレーシングナビゲーションノード (course_lap_node)
===========================================================
カメラ画像のみを入力として受け取り、以下の制御を実行：
1. 連続トラッキング(ROI±150px) ＆ 最大ブロック抽出による堅牢な4点(0.90, 0.80, 0.70, 0.60)2次関数近似(Polyfit)軌道追従
2. 0.55スキャンラインの路面重心オフセット(15%)による高速レスポンスカーブ先読みと速度制御
3. 画面下部(85%〜100%)の緑色(芝生)割合チェックによる緊急停止機構
"""

import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

# ─────────────────────────────────────────
#  制御パラメータ (連続トラッキング 4点 Polyfit Pure Pursuit & 高速カーブ検知)
# ─────────────────────────────────────────
SCAN_Y_CURVE_RATIO          = 0.55     # 最上段: カーブ検知専用 (0.55)
CURVE_OFFSET_THRESHOLD_RATIO= 0.15     # カーブ検知オフセット閾値 (画面幅の15%)

SCAN_Y_FAR_STEER_RATIO      = 0.60     # 遠方スキャンライン (0.60)
SCAN_Y_MID_STEER_RATIO      = 0.70     # 中間スキャンライン (0.70)
SCAN_Y_NEAR_STEER_RATIO     = 0.80     # 近景スキャンライン (0.80)
SCAN_Y_BOTTOM_STEER_RATIO   = 0.90     # 足元スキャンライン (0.90)

TRACKING_ROI_WIDTH          = 150      # 連続トラッキング探索領域 (±150px)
TRACKING_TARGET_Y_RATIO     = 0.625    # 2次曲線評価・追従目標Y位置 (0.625)

# ─────────────────────────────────────────
#  レーシング制御パラメータ
# ─────────────────────────────────────────
SPEED_FAST          = 2.78      # 直線走行速度（ファストアウト） [m/s]
SPEED_SLOW          = 1.39     # カーブ旋回速度（スローイン） [m/s]
STEER_KP            = 0.005    # ステアリング 比例ゲイン
STEER_KD            = 0.004    # ステアリング 微分ゲイン (ダンパー効果強化)

# HSV色空間閾値（シミュレータ環境）
BLACK_V_MAX         = 50       # 黒路面 V上限
WHITE_V_MIN         = 200      # 白線 V下限
GREEN_H_LOW, GREEN_H_HIGH = 35, 85   # 芝生 H範囲
GREEN_S_LOW, GREEN_S_HIGH = 40, 255  # 芝生 S範囲
GREEN_V_LOW, GREEN_V_HIGH = 40, 255  # 芝生 V範囲

# 安全装置閾値
EMERGENCY_GREEN_RATIO = 0.80   # 画面下部ピクセルで緑が80%を超えたら緊急停止


# ─────────────────────────────────────────
#  ステート定義
# ─────────────────────────────────────────
class State:
    INIT           = "INIT"
    STRAIGHT       = "STRAIGHT"       # 直線（高速）
    PRE_CURVE      = "PRE_CURVE"      # カーブ手前検知（減速）
    TURNING        = "TURNING"        # カーブ旋回中（減速）
    EMERGENCY      = "EMERGENCY"      # 危険（芝生検知による緊急停止）


class CourseLapNode(Node):
    """連続トラッキング＆最大ブロック抽出 4点 Polyfit 2次曲線Pure Pursuitビジュアルレーシングノード"""

    def __init__(self):
        super().__init__('course_lap_node')

        # ────── パラメータ宣言 ──────
        self.declare_parameter('debug_view', True)
        self.debug_view = self.get_parameter('debug_view').value

        # ────── 状態管理 ──────
        self.state = State.INIT
        self.bridge = CvBridge()
        self.prev_error = 0.0
        self.is_emergency_stopped = False  # 緊急停止スパム防止フラグ

        # ────── QoS ──────
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # ────── Publishers & Subscribers ──────
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.dbg_pub = self.create_publisher(Image, '/debug/lane_view', 1)

        self.create_subscription(Image, '/camera/image_raw', self._cb_camera, sensor_qos)

        self.get_logger().info('🏎️ [CourseLapNode] 連続トラッキング4点Polyfit軌道追従ノード起動。')
        self._transition(State.STRAIGHT)

    def _transition(self, next_state: str):
        """ステート遷移"""
        if self.state != next_state:
            self.get_logger().info(f' State: {self.state} → {next_state}')
            self.state = next_state

    def _get_largest_block_center(self, mask_line: np.ndarray, start_x: float, end_x: float, w: int) -> float:
        """
        1次元マスク (mask_line) の [start_x, end_x] の範囲内で、
        True (黒色路面ピクセル) が最も長く連続している塊（最大ブロック）の中心X座標を算出する。
        """
        sx = int(np.clip(start_x, 0, w - 1))
        ex = int(np.clip(end_x, 0, w - 1))
        if sx > ex:
            sx, ex = ex, sx

        sub_mask = mask_line[sx : ex + 1]
        if not np.any(sub_mask):
            return (sx + ex) / 2.0

        diff = np.diff(np.concatenate(([0], sub_mask.astype(np.int8), [0])))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]

        lengths = ends - starts
        max_idx = np.argmax(lengths)

        block_start = sx + starts[max_idx]
        block_end = sx + ends[max_idx] - 1

        return (block_start + block_end) / 2.0

    def _cb_camera(self, msg: Image):
        """連続トラッキング＆最大ブロック抽出 4点Polyfitビジュアルサーボ制御"""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except Exception as e:
            self.get_logger().warn(f'画像変換失敗: {e}')
            return

        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # ─────────────────────────────────────────
        # 1. [安全装置] 画面最下部 (Y: 85%〜100%) で緑色（芝生）を検知
        # ─────────────────────────────────────────
        bottom_roi_y = int(h * 0.85)
        bottom_hsv = hsv[bottom_roi_y:, :]
        green_mask = cv2.inRange(
            bottom_hsv,
            (GREEN_H_LOW, GREEN_S_LOW, GREEN_V_LOW),
            (GREEN_H_HIGH, GREEN_S_HIGH, GREEN_V_HIGH)
        )
        green_ratio = np.count_nonzero(green_mask) / float(green_mask.size)

        if green_ratio > EMERGENCY_GREEN_RATIO:
            if not self.is_emergency_stopped:
                self.get_logger().error(f'🚨 [EMERGENCY] 芝生検出 ({green_ratio*100:.1f}% > {EMERGENCY_GREEN_RATIO*100:.1f}%) → 緊急停止！')
                self._transition(State.EMERGENCY)
                self._stop()
                self.is_emergency_stopped = True
                self._publish_debug(frame, h, w, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, np.array([0.0, 0.0, 0.0]), green_ratio, True)
            return

        if self.state == State.EMERGENCY and green_ratio <= EMERGENCY_GREEN_RATIO:
            self._transition(State.STRAIGHT)
            self.is_emergency_stopped = False

        # ─────────────────────────────────────────
        # 2. [最上段スキャンライン: 高速レスポンス・カーブ検知] Y = h * 0.55
        # ─────────────────────────────────────────
        y_curve = int(h * SCAN_Y_CURVE_RATIO)
        curve_line = v_channel[y_curve, :]
        black_curve_indices = np.where(curve_line <= BLACK_V_MAX)[0]

        is_curve_detected = False
        if len(black_curve_indices) > 0:
            c_min_x, c_max_x = black_curve_indices[0], black_curve_indices[-1]
            c_center = (c_min_x + c_max_x) / 2.0
            offset = abs(c_center - (w / 2.0))
            if offset > (w * CURVE_OFFSET_THRESHOLD_RATIO):
                is_curve_detected = True
        else:
            is_curve_detected = True

        if is_curve_detected:
            if self.state == State.STRAIGHT:
                self._transition(State.PRE_CURVE)
            elif self.state == State.PRE_CURVE:
                self._transition(State.TURNING)
            target_speed = SPEED_SLOW
        else:
            if self.state in (State.PRE_CURVE, State.TURNING):
                self._transition(State.STRAIGHT)
            target_speed = SPEED_FAST

        # ─────────────────────────────────────────
        # 3. [連続トラッキング ＆ 最大ブロック抽出: 下から上へ連鎖探索 (0.90 -> 0.80 -> 0.70 -> 0.60)]
        # ─────────────────────────────────────────
        # ① 足元ライン (Y: 0.90) — 探索範囲: 全幅 [0, w-1]
        y_bottom = int(h * SCAN_Y_BOTTOM_STEER_RATIO)
        bottom_mask = (v_channel[y_bottom, :] <= BLACK_V_MAX)
        center_bottom_x = self._get_largest_block_center(bottom_mask, 0, w - 1, w)

        # ② 近景ライン (Y: 0.80) — 探索範囲: center_bottom_x ± 150px
        y_near = int(h * SCAN_Y_NEAR_STEER_RATIO)
        near_mask = (v_channel[y_near, :] <= BLACK_V_MAX)
        center_near_x = self._get_largest_block_center(
            near_mask, center_bottom_x - TRACKING_ROI_WIDTH, center_bottom_x + TRACKING_ROI_WIDTH, w
        )

        # ③ 中間ライン (Y: 0.70) — 探索範囲: center_near_x ± 150px
        y_mid = int(h * SCAN_Y_MID_STEER_RATIO)
        mid_mask = (v_channel[y_mid, :] <= BLACK_V_MAX)
        center_mid_x = self._get_largest_block_center(
            mid_mask, center_near_x - TRACKING_ROI_WIDTH, center_near_x + TRACKING_ROI_WIDTH, w
        )

        # ④ 遠方ライン (Y: 0.60) — 探索範囲: center_mid_x ± 150px
        y_far = int(h * SCAN_Y_FAR_STEER_RATIO)
        far_mask = (v_channel[y_far, :] <= BLACK_V_MAX)
        center_far_x = self._get_largest_block_center(
            far_mask, center_mid_x - TRACKING_ROI_WIDTH, center_mid_x + TRACKING_ROI_WIDTH, w
        )

        # ⑤ np.polyfit による 4点2次曲線フィッティング (X = a*Y^2 + b*Y + c)
        Y_array = np.array([float(y_bottom), float(y_near), float(y_mid), float(y_far)])
        X_array = np.array([float(center_bottom_x), float(center_near_x), float(center_mid_x), float(center_far_x)])

        try:
            poly_coeffs = np.polyfit(Y_array, X_array, 2)  # [a, b, c]
        except Exception:
            poly_coeffs = np.array([0.0, 0.0, float(center_near_x)])

        # ⑥ 追従目標Y位置 (Y = h * 0.625) での理想の目標X座標を評価
        y_ref = float(h * TRACKING_TARGET_Y_RATIO)
        target_x = (poly_coeffs[0] * (y_ref ** 2)) + (poly_coeffs[1] * y_ref) + poly_coeffs[2]

        # ─────────────────────────────────────────
        # 4. [1次元PID誤差計算 & 操舵]
        # 画面中央 (center_x = w / 2.0) と Polyfit 評価目標 (target_x) の誤差
        # ─────────────────────────────────────────
        center_x = w / 2.0
        error = center_x - target_x
        d_error = error - self.prev_error
        self.prev_error = error

        angular_z = (STEER_KP * error) + (STEER_KD * d_error)
        angular_z = float(np.clip(angular_z, -1.0, 1.0))

        # デバッグログ出力
        self.get_logger().info(
            f"🚦 State: {self.state:<9} | "
            f"PolyTargetX: {target_x:>5.1f} (足:{center_bottom_x:.1f}, 近:{center_near_x:.1f}, 中:{center_mid_x:.1f}, 遠:{center_far_x:.1f}) | "
            f"誤差 Error: {error:>6.1f} | "
            f"出力 v: {target_speed:.2f}, w: {angular_z:.3f}"
        )

        # コマンド送信
        twist = Twist()
        twist.linear.x = float(target_speed)
        twist.angular.z = angular_z
        self.cmd_pub.publish(twist)

        # デバッグ画面出力
        self._publish_debug(frame, h, w, y_bottom, y_near, y_mid, y_far, y_curve, y_ref, center_bottom_x, center_near_x, center_mid_x, center_far_x, target_x, poly_coeffs, green_ratio, False)

    def _stop(self):
        self.cmd_pub.publish(Twist())

    def _publish_debug(self, frame, h, w, y_bottom, y_near, y_mid, y_far, y_curve, y_ref, center_bottom_x, center_near_x, center_mid_x, center_far_x, target_x, poly_coeffs, green_ratio, emergency):
        if not self.debug_view:
            return

        dbg = frame.copy()

        # ① 安全装置ROI (赤枠: 下部 85%〜100%)
        cv2.rectangle(dbg, (0, int(h * 0.85)), (w, h), (0, 0, 255), 2)
        cv2.putText(dbg, "SAFETY ROI (GREEN)", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # ② 最上段: カーブ検知スキャンライン (紫横線 0.55)
        cv2.line(dbg, (0, y_curve), (w, y_curve), (255, 0, 255), 2)
        cv2.putText(dbg, "CURVE SCANLINE (55%)", (10, y_curve - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

        # ③ 遠方スキャンライン (青色横線 0.60)
        cv2.line(dbg, (0, y_far), (w, y_far), (255, 0, 0), 2)
        cv2.putText(dbg, "FAR SCANLINE (60%)", (10, y_far - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        # 探索領域ROIの視覚化 (青色括弧)
        far_sx = int(np.clip(center_mid_x - TRACKING_ROI_WIDTH, 0, w - 1))
        far_ex = int(np.clip(center_mid_x + TRACKING_ROI_WIDTH, 0, w - 1))
        cv2.line(dbg, (far_sx, y_far - 8), (far_sx, y_far + 8), (255, 0, 0), 2)
        cv2.line(dbg, (far_ex, y_far - 8), (far_ex, y_far + 8), (255, 0, 0), 2)

        # ④ 中間スキャンライン (水色横線 0.70)
        cv2.line(dbg, (0, y_mid), (w, y_mid), (255, 255, 0), 2)
        cv2.putText(dbg, "MID SCANLINE (70%)", (10, y_mid - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        mid_sx = int(np.clip(center_near_x - TRACKING_ROI_WIDTH, 0, w - 1))
        mid_ex = int(np.clip(center_near_x + TRACKING_ROI_WIDTH, 0, w - 1))
        cv2.line(dbg, (mid_sx, y_mid - 8), (mid_sx, y_mid + 8), (255, 255, 0), 2)
        cv2.line(dbg, (mid_ex, y_mid - 8), (mid_ex, y_mid + 8), (255, 255, 0), 2)

        # ⑤ 近景スキャンライン (黄色横線 0.80)
        cv2.line(dbg, (0, y_near), (w, y_near), (0, 255, 255), 2)
        cv2.putText(dbg, "NEAR SCANLINE (80%)", (10, y_near - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        near_sx = int(np.clip(center_bottom_x - TRACKING_ROI_WIDTH, 0, w - 1))
        near_ex = int(np.clip(center_bottom_x + TRACKING_ROI_WIDTH, 0, w - 1))
        cv2.line(dbg, (near_sx, y_near - 8), (near_sx, y_near + 8), (0, 255, 255), 2)
        cv2.line(dbg, (near_ex, y_near - 8), (near_ex, y_near + 8), (0, 255, 255), 2)

        # ⑥ 足元スキャンライン (緑色横線 0.90)
        cv2.line(dbg, (0, y_bottom), (w, y_bottom), (0, 255, 0), 2)
        cv2.putText(dbg, "BOTTOM SCANLINE (90%)", (10, y_bottom - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # 緊急停止時は大文字で警告表示
        if emergency:
            cv2.putText(dbg, f"EMERGENCY BRAKE! Green: {green_ratio*100:.1f}%", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        else:
            # 足元重心 (緑丸)
            cv2.circle(dbg, (int(center_bottom_x), y_bottom), 6, (0, 255, 0), -1)
            # 近景重心 (黄丸)
            cv2.circle(dbg, (int(center_near_x), y_near), 6, (0, 255, 255), -1)
            # 中間重心 (水色丸)
            cv2.circle(dbg, (int(center_mid_x), y_mid), 6, (255, 255, 0), -1)
            # 遠方重心 (青丸)
            cv2.circle(dbg, (int(center_far_x), y_far), 6, (255, 0, 0), -1)

            # Polyfit 2次代数曲線のプレビュー描画 (赤色曲線)
            try:
                plot_y = np.linspace(y_far, y_bottom, 30)
                plot_x = (poly_coeffs[0] * (plot_y ** 2)) + (poly_coeffs[1] * plot_y) + poly_coeffs[2]
                pts = np.vstack((plot_x, plot_y)).T.astype(np.int32)
                cv2.polylines(dbg, [pts], isClosed=False, color=(0, 0, 255), thickness=2)
            except Exception:
                pass

            # 最終評価ターゲット (赤丸)
            target_x_int = int(target_x)
            cv2.circle(dbg, (target_x_int, int(y_ref)), 8, (0, 0, 255), -1)

            label = f"STATE: {self.state}  |  Green: {green_ratio*100:.1f}%  PolyTargetX: {target_x:.1f}"
            cv2.putText(dbg, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        # ROS 2 トピックへのパブリッシュ
        try:
            self.dbg_pub.publish(self.bridge.cv2_to_imgmsg(dbg, 'bgr8'))
        except Exception:
            pass

        # リアルタイムデバッグGUIウィンドウ表示
        try:
            cv2.imshow("Raphael Racing - Debug View", dbg)
            cv2.waitKey(1)
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = CourseLapNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
