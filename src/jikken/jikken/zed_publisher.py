#!/usr/bin/env python3
"""
ZED Camera Video Publisher Node for ROS 2.

This node captures video frames from a USB-connected ZED camera
(using PyZED SDK if available, or falling back to OpenCV VideoCapture)
and publishes the Left Eye image as ROS 2 sensor_msgs/msg/Image messages.
"""

import os
import sys
import glob
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2

# Try importing pyzed SDK if available
try:
    import pyzed.sl as sl
    PYZED_AVAILABLE = True
except ImportError:
    PYZED_AVAILABLE = False


def find_zed_device_id():
    """Attempt to auto-detect ZED camera video device index from /dev/v4l/by-id/"""
    by_id_path = '/dev/v4l/by-id/'
    if os.path.exists(by_id_path):
        links = sorted(os.listdir(by_id_path))
        # Prioritize index0 for main video stream
        zed_links = [l for l in links if ('ZED' in l or 'STEREOLABS' in l or 'Technologies__Inc._ZED' in l)]
        zed_links.sort(key=lambda x: 0 if 'index0' in x else 1)
        for link_name in zed_links:
            full_path = os.path.join(by_id_path, link_name)
            target = os.path.realpath(full_path)
            if 'video' in target:
                try:
                    # e.g., /dev/video2 -> 2
                    device_idx = int(target.replace('/dev/video', ''))
                    return device_idx
                except ValueError:
                    pass
    return None


class ZedPublisher(Node):

    def __init__(self):
        super().__init__('zed_publisher')

        # Detect ZED camera device ID automatically if possible
        auto_detected_id = find_zed_device_id()
        default_device_id = auto_detected_id if auto_detected_id is not None else 0

        # Declare parameters
        self.declare_parameter('video_device', default_device_id)
        self.declare_parameter('frame_rate', 15.0)
        self.declare_parameter('topic_name', '/aiformula_sensing/zed_node/left_image/undistorted')
        self.declare_parameter('frame_id', 'zed_left_camera_optical_frame')
        self.declare_parameter('width', 1080)
        self.declare_parameter('height', 720)
        self.declare_parameter('use_zed_sdk', True)
        self.declare_parameter('jpeg_quality', 80)

        # Get parameter values
        self.device_id = self.get_parameter('video_device').get_parameter_value().integer_value
        self.frame_rate = self.get_parameter('frame_rate').get_parameter_value().double_value
        topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.width = self.get_parameter('width').get_parameter_value().integer_value
        self.height = self.get_parameter('height').get_parameter_value().integer_value
        use_zed_sdk = self.get_parameter('use_zed_sdk').get_parameter_value().bool_value
        self.jpeg_quality = self.get_parameter('jpeg_quality').get_parameter_value().integer_value

        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(Image, topic_name, 10)
        
        # Compressed Image Publisher (zed_cam_left_image_raw/compressed)
        compressed_topic_name = f"{topic_name}/compressed" if not topic_name.endswith('/compressed') else topic_name
        self.publisher_compressed_ = self.create_publisher(CompressedImage, compressed_topic_name, 10)

        self.zed_sdk_mode = False
        self.cap = None
        self.zed = None
        self.zed_mat = None

        # Attempt PyZED initialization if requested & available
        if use_zed_sdk and PYZED_AVAILABLE:
            self.get_logger().info('Attempting to initialize ZED SDK (pyzed.sl)...')
            init_params = sl.InitParameters()
            init_params.camera_resolution = sl.RESOLUTION.HD720
            init_params.camera_fps = int(self.frame_rate)
            
            self.zed = sl.Camera()
            err = self.zed.open(init_params)
            if err == sl.ERROR_CODE.SUCCESS:
                self.get_logger().info('ZED SDK initialized successfully!')
                self.zed_sdk_mode = True
                self.zed_mat = sl.Mat()
            else:
                self.get_logger().warn(f'ZED SDK open failed ({err}). Falling back to OpenCV...')

        if not self.zed_sdk_mode:
            candidate_ids = [self.device_id]
            for candidate in [2, 3, 0, 1]:
                if candidate not in candidate_ids:
                    candidate_ids.append(candidate)
            
            opened = False
            for dev_id in candidate_ids:
                self.get_logger().info(f'Trying camera device /dev/video{dev_id} via OpenCV...')
                cap = cv2.VideoCapture(dev_id)
                if cap.isOpened():
                    if self.width > 0 and self.height > 0:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.frame_rate)
                    
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                        self.device_id = dev_id
                        opened = True
                        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        self.get_logger().info(f'Camera /dev/video{dev_id} successfully opened ({actual_w}x{actual_h})')
                        break
                    else:
                        cap.release()

            if not opened:
                self.get_logger().error('Failed to open any valid camera video device')

        # Setup timer loop
        timer_period = 1.0 / self.frame_rate if self.frame_rate > 0 else 0.033
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f'ZED Publisher started on topic "{topic_name}" at {self.frame_rate} FPS')

    def timer_callback(self):
        frame = None

        if self.zed_sdk_mode:
            runtime_params = sl.RuntimeParameters()
            if self.zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                self.zed.retrieve_image(self.zed_mat, sl.VIEW.LEFT)
                # Convert BGRA to BGR
                bgra_data = self.zed_mat.get_data()
                frame = cv2.cvtColor(bgra_data, cv2.COLOR_BGRA2BGR)
        else:
            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.get_logger().warn('Failed to read frame from OpenCV VideoCapture', throttle_duration_sec=5.0)
                    return
                
                # If frame is Side-by-Side (width is significantly wider than height), crop the left half (Left eye)
                h, w = frame.shape[:2]
                if w > h * 1.5:
                    frame = frame[:, :w // 2]

        if frame is not None:
            now = self.get_clock().now().to_msg()

            # 1. Convert OpenCV frame to raw ROS 2 Image msg
            raw_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            raw_msg.header.stamp = now
            raw_msg.header.frame_id = self.frame_id
            self.publisher_.publish(raw_msg)

            # 2. Convert OpenCV frame to ROS 2 CompressedImage msg (JPEG format)
            compressed_msg = self.bridge.cv2_to_compressed_imgmsg(frame, dst_format='jpeg')
            compressed_msg.header.stamp = now
            compressed_msg.header.frame_id = self.frame_id
            self.publisher_compressed_.publish(compressed_msg)

    def destroy_node(self):
        if self.zed_sdk_mode and self.zed is not None:
            self.zed.close()
        elif self.cap is not None and self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZedPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
