#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
制御用・GUI表示ノード (キーボード手動操縦・2値化表示・独立鳥瞰図表示)
- Subscribe: 
  - /camera/image_raw (sensor_msgs/Image) - 一人称カメラ(FPV)
  - /camera/birdseye_image_raw (sensor_msgs/Image) - 全体鳥瞰図(カラー)
- Publish: 
  - /cmd_vel (geometry_msgs/Twist) - キーボード操作コマンド
- GUIウィンドウ構成:
  - ウィンドウ1: [一人称カメラ (カラー) | 一人称２値化 (HSV閾値)] + 日本語操作説明パネル
  - ウィンドウ2: [全体鳥瞰図 (コースマップ)] (独立ウィンドウ・カラー・2値化なし)
- キーボード操作 (W:前進, S:後退, A:左旋回, D:右旋回, Space/X:停止)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image as PILImage

JAPANESE_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def draw_japanese_text(img, text, position, font_size=18, color=(255, 255, 255)):
    """
    Pillowを使用してOpenCV画像(BGR)上に日本語テキストを描画する
    color: (B, G, R)
    """
    try:
        font = ImageFont.truetype(JAPANESE_FONT_PATH, font_size)
    except Exception:
        cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return img

    # BGR -> RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    # PIL fill は (R, G, B)
    rgb_color = (color[2], color[1], color[0])
    draw.text(position, text, font=font, fill=rgb_color)

    # RGB -> BGR
    img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img_bgr

class VisionControlNode(Node):
    def __init__(self):
        super().__init__('vision_control_node')

        self.sub_image = self.create_subscription(Image, '/camera/image_raw', self.image_callback, 10)
        self.sub_birdseye = self.create_subscription(Image, '/camera/birdseye_image_raw', self.birdseye_callback, 10)
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)

        self.cv_bridge = CvBridge()

        # 手動操作用速度状態
        self.target_v = 0.0
        self.target_w = 0.0

        # 白線抽出用 固定HSV閾値 (トラックバー完全廃止)
        self.lower_hsv = np.array([0, 0, 200])
        self.upper_hsv = np.array([180, 40, 255])

        # -------------------------------------------------------------
        # GUI ウィンドウ1: メイン画面 (一人称カラー & 二値化)
        # -------------------------------------------------------------
        self.main_window_name = "一人称ビュー & HSV二値化 [FPV Control UI]"
        cv2.namedWindow(self.main_window_name, cv2.WINDOW_AUTOSIZE)

        # -------------------------------------------------------------
        # GUI ウィンドウ2: 独立鳥瞰図画面 (カラー・２値化なし)
        # -------------------------------------------------------------
        self.birdseye_window_name = "全体鳥瞰図 (コースマップ) [Bird's-eye View]"
        cv2.namedWindow(self.birdseye_window_name, cv2.WINDOW_AUTOSIZE)

        self.get_logger().info("VisionControlNode initialized successfully. Ready for keyboard teleop!")

    def birdseye_callback(self, msg: Image):
        try:
            birdseye_bgr = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            # 鳥瞰図画面に日本語タイトルを表示
            disp_bird = birdseye_bgr.copy()
            disp_bird = draw_japanese_text(disp_bird, "全体鳥瞰図 (カラー映像 / 2値化なし)", (15, 15), font_size=20, color=(0, 255, 255))
            cv2.imshow(self.birdseye_window_name, disp_bird)
            cv2.waitKey(1)
        except Exception as e:
            self.get_logger().error(f"Birdseye cv_bridge error: {e}")

    def image_callback(self, msg: Image):
        try:
            cv_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"cv_bridge conversion error: {e}")
            return

        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        # 固定HSV閾値で白線二値化マスク作成
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

        # 画像下半分のROI（関心領域）
        h, w = mask.shape
        roi = mask[int(h * 0.5):, :]

        # 白線重心（確認用マーク）
        M = cv2.moments(roi)
        if M["m00"] > 500:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.circle(cv_image, (cx, int(h * 0.5) + cy), 8, (0, 255, 0), -1)

        # -------------------------------------------------------------
        # 1. メインGUI表示の作成 (2画面: 一人称カラー | 一人称2値化)
        # -------------------------------------------------------------
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        img_fpv_color = cv_image.copy()
        img_fpv_color = draw_japanese_text(img_fpv_color, "1. 一人称カメラ (カラー)", (15, 15), font_size=20, color=(0, 255, 0))
        img_fpv_color = draw_japanese_text(img_fpv_color, f"走行指令: 前進={self.target_v:.2f}m/s, 旋回={self.target_w:.2f}rad/s", 
                                           (15, 45), font_size=18, color=(0, 255, 255))

        img_fpv_mask = mask_bgr.copy()
        img_fpv_mask = draw_japanese_text(img_fpv_mask, "2. 一人称 2値化マスク (HSV閾値)", (15, 15), font_size=20, color=(255, 255, 255))

        # 2画面横並び連結 (横 640*2 = 1280px)
        combined_views = np.hstack((img_fpv_color, img_fpv_mask))

        # 下部操作説明パネルの作成 (高さ 70px, 横幅 1280px)
        panel_h = 70
        total_w = combined_views.shape[1]
        info_panel = np.zeros((panel_h, total_w, 3), dtype=np.uint8)
        info_panel[:] = (40, 40, 50)  # 濃紺グレー背景

        # 日本語操作説明テキスト描画
        text_line1 = "【キーボード手動操縦 (Teleop)】 W: 前進 (0.4m/s)  |  S: 後退 (-0.2m/s)  |  A: 左旋回 (+0.5rad/s)  |  D: 右旋回 (-0.5rad/s)  |  Space / X: 停止"
        text_line2 = f"【HSV固定閾値】 H: [{self.lower_hsv[0]}-{self.upper_hsv[0]}]  |  S: [{self.lower_hsv[1]}-{self.upper_hsv[1]}]  |  V: [{self.lower_hsv[2]}-{self.upper_hsv[2]}]"

        info_panel = draw_japanese_text(info_panel, text_line1, (15, 15), font_size=18, color=(0, 255, 255))
        info_panel = draw_japanese_text(info_panel, text_line2, (15, 42), font_size=16, color=(200, 255, 200))

        # 2画面と説明パネルを上下連結
        full_gui = np.vstack((combined_views, info_panel))

        cv2.imshow(self.main_window_name, full_gui)
        
        # -------------------------------------------------------------
        # 2. キーボード入力判定 & /cmd_vel 送信
        # -------------------------------------------------------------
        key = cv2.waitKey(1) & 0xFF
        if key != 255:
            if key == ord('w') or key == 82:    # 前進 (W または 矢印上)
                self.target_v = 0.4
                self.target_w = 0.0
            elif key == ord('s') or key == 84:  # 後退 (S または 矢印下)
                self.target_v = -0.2
                self.target_w = 0.0
            elif key == ord('a') or key == 81:  # 左旋回 (A または 矢印左)
                self.target_w = 0.5
            elif key == ord('d') or key == 83:  # 右旋回 (D または 矢印右)
                self.target_w = -0.5
            elif key == ord('x') or key == ord(' ') or key == 32:  # 停止 (X または Space)
                self.target_v = 0.0
                self.target_w = 0.0

        # /cmd_vel の Publish
        cmd_msg = Twist()
        cmd_msg.linear.x = float(self.target_v)
        cmd_msg.angular.z = float(self.target_w)
        self.pub_cmd_vel.publish(cmd_msg)

def main(args=None):
    rclpy.init(args=args)
    node = VisionControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
