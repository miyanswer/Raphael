#!/usr/bin/env python3
"""
ZED Camera FHD H.264 (MP4) Recorder with OpenCV Live Preview (No ROS 2 Publisher).

This node captures FHD video from a ZED camera at a target frame rate,
saves the left eye video directly to an H.264/MP4 file in real-time,
and displays the live video feed using OpenCV (`cv2.imshow`).
It does NOT publish any ROS 2 image topics.
"""

import os
import sys
import datetime
import rclpy
from rclpy.node import Node
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
        zed_links = [l for l in links if ('ZED' in l or 'STEREOLABS' in l or 'Technologies__Inc._ZED' in l)]
        zed_links.sort(key=lambda x: 0 if 'index0' in x else 1)
        for link_name in zed_links:
            full_path = os.path.join(by_id_path, link_name)
            target = os.path.realpath(full_path)
            if 'video' in target:
                try:
                    device_idx = int(target.replace('/dev/video', ''))
                    return device_idx
                except ValueError:
                    pass
    return None


class ZedH264Recorder(Node):

    def __init__(self):
        super().__init__('zed_h264_recorder')

        auto_detected_id = find_zed_device_id()
        default_device_id = auto_detected_id if auto_detected_id is not None else 0

        # Declare parameters
        self.declare_parameter('video_device', default_device_id)
        self.declare_parameter('frame_rate', 15.0)
        self.declare_parameter('width', 3840)
        self.declare_parameter('height', 1080)
        self.declare_parameter('use_zed_sdk', True)
        self.declare_parameter('save_dir', 'mp4_videos')
        self.declare_parameter('enable_recording', True)
        self.declare_parameter('show_preview', True)
        self.declare_parameter('window_name', 'ZED Camera Live Preview')

        # Get parameter values
        self.device_id = self.get_parameter('video_device').get_parameter_value().integer_value
        self.frame_rate = self.get_parameter('frame_rate').get_parameter_value().double_value
        self.width = self.get_parameter('width').get_parameter_value().integer_value
        self.height = self.get_parameter('height').get_parameter_value().integer_value
        use_zed_sdk = self.get_parameter('use_zed_sdk').get_parameter_value().bool_value
        self.save_dir = self.get_parameter('save_dir').get_parameter_value().string_value
        self.enable_recording = self.get_parameter('enable_recording').get_parameter_value().bool_value
        self.show_preview = self.get_parameter('show_preview').get_parameter_value().bool_value
        self.window_name = self.get_parameter('window_name').get_parameter_value().string_value

        self.zed_sdk_mode = False
        self.cap = None
        self.zed = None
        self.zed_mat = None

        # VideoWriter setup
        self.writer = None
        self.writer_initialized = False

        if self.enable_recording:
            os.makedirs(self.save_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            self.output_filepath = os.path.join(self.save_dir, f"shihou_video_{timestamp}.mp4")
            self.get_logger().info(f'Video recording enabled. MP4 target path: {self.output_filepath}')

        # Attempt PyZED initialization if requested & available
        if use_zed_sdk and PYZED_AVAILABLE:
            self.get_logger().info('Attempting to initialize ZED SDK (pyzed.sl) at FHD resolution...')
            init_params = sl.InitParameters()
            init_params.camera_resolution = sl.RESOLUTION.HD1080
            init_params.camera_fps = int(self.frame_rate)
            
            self.zed = sl.Camera()
            err = self.zed.open(init_params)
            if err == sl.ERROR_CODE.SUCCESS:
                self.get_logger().info('ZED SDK initialized successfully (FHD 1080p)!')
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
                self.get_logger().info(f'Trying camera device /dev/video{dev_id} via OpenCV (target 3840x1080 @ {self.frame_rate}FPS)...')
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

        if self.show_preview:
            self.get_logger().info("OpenCV preview enabled. Focus the preview window and press 'q' or 'ESC' to quit.")

        timer_period = 1.0 / self.frame_rate if self.frame_rate > 0 else 0.033
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f'ZED H.264 Recorder started (Recording & OpenCV Preview only) at {self.frame_rate} FPS')

    def init_video_writer(self, frame_h, frame_w):
        if not self.enable_recording or self.writer_initialized:
            return
        
        # Use H.264 / mp4v codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.output_filepath, fourcc, self.frame_rate, (frame_w, frame_h))
        if self.writer.isOpened():
            self.writer_initialized = True
            self.get_logger().info(f'OpenCV VideoWriter initialized for H.264/MP4 ({frame_w}x{frame_h} @ {self.frame_rate} FPS)')
        else:
            self.get_logger().error(f'Failed to initialize VideoWriter for path {self.output_filepath}')

    def timer_callback(self):
        frame = None

        if self.zed_sdk_mode:
            runtime_params = sl.RuntimeParameters()
            if self.zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                self.zed.retrieve_image(self.zed_mat, sl.VIEW.LEFT)
                bgra_data = self.zed_mat.get_data()
                frame = cv2.cvtColor(bgra_data, cv2.COLOR_BGRA2BGR)
        else:
            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.get_logger().warn('Failed to read frame from OpenCV VideoCapture', throttle_duration_sec=5.0)
                    return
                
                # Crop left eye image if Side-by-Side
                h, w = frame.shape[:2]
                if w > h * 1.5:
                    frame = frame[:, :w // 2]

        if frame is not None:
            # 1. Initialize VideoWriter on first valid frame
            if self.enable_recording and not self.writer_initialized:
                fh, fw = frame.shape[:2]
                self.init_video_writer(fh, fw)

            # 2. Write frame to MP4 file (Record & Compress)
            if self.writer is not None and self.writer.isOpened():
                self.writer.write(frame)

            # 3. Live OpenCV preview (No ROS topic publishing)
            if self.show_preview:
                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'), 27]:  # 'q' or ESC key pressed
                    self.get_logger().info("Quit key pressed in OpenCV window. Shutting down...")
                    rclpy.shutdown()

    def destroy_node(self):
        if self.show_preview:
            cv2.destroyAllWindows()
        if self.writer is not None and self.writer.isOpened():
            self.writer.release()
            self.get_logger().info(f'MP4 VideoWriter released. Saved file: {self.output_filepath}')
        if self.zed_sdk_mode and self.zed is not None:
            self.zed.close()
        elif self.cap is not None and self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZedH264Recorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
