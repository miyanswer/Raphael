#!/bin/bash
"""
MP4 Video File Publisher Node for ROS 2.

Reads an MP4 video file and publishes sensor_msgs/msg/Image
and sensor_msgs/msg/CompressedImage topics at specified FPS.
"""

import os
import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2


class Mp4Publisher(Node):

    def __init__(self):
        super().__init__('mp4_publisher')

        # Declare parameters
        self.declare_parameter('video_path', '')
        self.declare_parameter('topic_name', '/aiformula_sensing/zed_node/left_image/undistorted')
        self.declare_parameter('frame_id', 'zed_left_camera_optical_frame')
        self.declare_parameter('frame_rate', 15.0)
        self.declare_parameter('loop', True)

        self.video_path = self.get_parameter('video_path').get_parameter_value().string_value
        topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.frame_rate = self.get_parameter('frame_rate').get_parameter_value().double_value
        self.loop = self.get_parameter('loop').get_parameter_value().bool_value

        if not self.video_path:
            # Search for latest video in mp4_videos folder as default fallback
            default_dir = 'mp4_videos'
            if os.path.exists(default_dir):
                files = [os.path.join(default_dir, f) for f in os.listdir(default_dir) if f.endswith('.mp4')]
                if files:
                    files.sort(key=os.path.getmtime, reverse=True)
                    self.video_path = files[0]

        if not self.video_path or not os.path.exists(self.video_path):
            self.get_logger().error(f'Video file not found: "{self.video_path}". Please specify -p video_path:=/path/to/video.mp4')
            sys.exit(1)

        self.get_logger().info(f'Opening MP4 video file: {self.video_path}')
        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open video file {self.video_path}')
            sys.exit(1)

        # Retrieve FPS from video file if available
        video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if video_fps > 0:
            self.frame_rate = video_fps
            self.get_logger().info(f'Detected video FPS: {video_fps}')

        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(Image, topic_name, 10)
        
        compressed_topic_name = f"{topic_name}/compressed" if not topic_name.endswith('/compressed') else topic_name
        self.publisher_compressed_ = self.create_publisher(CompressedImage, compressed_topic_name, 10)

        timer_period = 1.0 / self.frame_rate if self.frame_rate > 0 else 0.033
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f'MP4 Publisher started for "{self.video_path}" on topic "{topic_name}" at {self.frame_rate} FPS')

    def timer_callback(self):
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()

        if not ret or frame is None:
            if self.loop:
                self.get_logger().info('End of video reached. Looping back to start...')
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    return
            else:
                self.get_logger().info('End of video reached. Stopping publisher.')
                self.timer.cancel()
                return

        now = self.get_clock().now().to_msg()

        # Publish raw Image
        raw_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        raw_msg.header.stamp = now
        raw_msg.header.frame_id = self.frame_id
        self.publisher_.publish(raw_msg)

        # Publish CompressedImage
        compressed_msg = self.bridge.cv2_to_compressed_imgmsg(frame, dst_format='jpeg')
        compressed_msg.header.stamp = now
        compressed_msg.header.frame_id = self.frame_id
        self.publisher_compressed_.publish(compressed_msg)

    def destroy_node(self):
        if self.cap is not None:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Mp4Publisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
