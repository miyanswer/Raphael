#!/usr/bin/env python3
"""
Web / QR Code Instant Smartphone IMU Publisher Node

Starts a lightweight Web & WebSocket/HTTP server that prints a QR code in the terminal.
Scanning the QR code with a smartphone opens a web page that automatically reads the
phone's IMU sensors (DeviceMotionEvent) and streams 6DoF IMU data to ROS 2 topic
/aiformula_sensing/zed_node/imu.
"""

import json
import math
import os
import socket
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3


def get_local_ip():
    """Find local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def print_qr_code(url):
    """Print ASCII QR Code in terminal if qrcode package is available, else print big URL box."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        print("\n" + "=" * 60)
        print(" 📱 SCAN THIS QR CODE WITH YOUR SMARTPHONE CAMERA:")
        print("=" * 60 + "\n")
        qr.print_ascii(invert=True)
        print("\n" + "=" * 60)
        print(f" URL: {url}")
        print("=" * 60 + "\n")
    except ImportError:
        print("\n" + "=" * 65)
        print(" 📱 OPEN THIS URL IN YOUR SMARTPHONE BROWSER (Safari/Chrome):")
        print("=" * 65)
        print(f"\n   👉   {url}   👈\n")
        print(" (Tip: Run 'pip install qrcode' to display QR code directly in terminal)")
        print("=" * 65 + "\n")


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZED Smartphone IMU Streamer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
            text-align: center;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 24px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 1px solid #334155;
        }
        h1 { font-size: 1.5rem; margin-top: 0; color: #38bdf8; }
        .status {
            font-size: 1.1rem;
            font-weight: bold;
            padding: 12px;
            border-radius: 8px;
            margin: 16px 0;
        }
        .connected { background: #065f46; color: #34d399; }
        .disconnected { background: #991b1b; color: #fca5a5; }
        .btn {
            background: #2563eb;
            color: white;
            border: none;
            padding: 14px 28px;
            font-size: 1.1rem;
            font-weight: bold;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 4px 12px rgba(37,99,235,0.4);
        }
        .btn:active { transform: scale(0.98); }
        .val-box {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 16px;
            font-size: 0.9rem;
            text-align: left;
        }
        .val-item {
            background: #0f172a;
            padding: 10px;
            border-radius: 8px;
        }
        .val-title { color: #94a3b8; font-size: 0.75rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📱 ZED ROS 2 IMU Streamer</h1>
        <p style="color: #94a3b8; font-size: 0.9rem;">Real-time Smartphone Motion Sensor Streamer</p>
        
        <div id="status" class="status disconnected">Disconnected / Waiting for Start</div>

        <button id="startBtn" class="btn" onclick="startIMU()">🚀 START SENSOR STREAMING</button>

        <div class="val-box">
            <div class="val-item">
                <div class="val-title">ACCEL (m/s²)</div>
                <div id="accelVal">X: 0.0<br>Y: 0.0<br>Z: 0.0</div>
            </div>
            <div class="val-item">
                <div class="val-title">GYRO (rad/s)</div>
                <div id="gyroVal">X: 0.0<br>Y: 0.0<br>Z: 0.0</div>
            </div>
        </div>
    </div>

    <script>
        let isStreaming = false;
        let lastSendTime = 0;
        const SEND_INTERVAL_MS = 15; // ~60Hz

        async function startIMU() {
            const statusEl = document.getElementById('status');
            const btnEl = document.getElementById('startBtn');

            // Request iOS permission if needed
            if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
                try {
                    const response = await DeviceMotionEvent.requestPermission();
                    if (response !== 'granted') {
                        alert('Permission to access motion sensors was denied.');
                        return;
                    }
                } catch (e) {
                    console.error(e);
                }
            }

            window.addEventListener('devicemotion', handleMotion, true);
            isStreaming = true;
            statusEl.className = 'status connected';
            statusEl.innerText = '🟢 Streaming Active to ROS 2';
            btnEl.innerText = '⚡ Streaming Running...';
            btnEl.style.background = '#059669';
        }

        function handleMotion(event) {
            if (!isStreaming) return;
            const now = performance.now();
            if (now - lastSendTime < SEND_INTERVAL_MS) return;
            lastSendTime = now;

            const accel = event.accelerationIncludingGravity || event.acceleration || {x: 0, y: 0, z: 9.81};
            const gyro = event.rotationRate || {alpha: 0, beta: 0, gamma: 0};

            const ax = accel.x || 0;
            const ay = accel.y || 0;
            const az = accel.z || 9.81;

            // Convert deg/s to rad/s
            const DEG2RAD = Math.PI / 180.0;
            const gx = (gyro.beta || 0) * DEG2RAD;  # X axis rotation rate
            const gy = (gyro.gamma || 0) * DEG2RAD; # Y axis rotation rate
            const gz = (gyro.alpha || 0) * DEG2RAD; # Z axis rotation rate

            document.getElementById('accelVal').innerHTML = `X: ${ax.toFixed(2)}<br>Y: ${ay.toFixed(2)}<br>Z: ${az.toFixed(2)}`;
            document.getElementById('gyroVal').innerHTML = `X: ${gx.toFixed(2)}<br>Y: ${gy.toFixed(2)}<br>Z: ${gz.toFixed(2)}`;

            const payload = JSON.stringify({ ax, ay, az, gx, gy, gz });

            fetch('/imu', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload
            }).catch(err => console.error(err));
        }
    </script>
</body>
</html>
"""


class WebImuPublisher(Node):
    """ROS 2 Node that receives HTTP IMU posts from smartphone browser."""

    def __init__(self):
        super().__init__('web_imu_publisher')

        # Parameters
        self.declare_parameter('port', 8000)
        self.declare_parameter('host_ip', '')
        self.declare_parameter('topic_name', '/aiformula_sensing/zed_node/imu')
        self.declare_parameter('frame_id', 'zed_imu_link')

        self.port = self.get_parameter('port').get_parameter_value().integer_value
        self.host_ip = self.get_parameter('host_ip').get_parameter_value().string_value
        self.topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value

        self.publisher_ = self.create_publisher(Imu, self.topic_name, 10)
        self.get_logger().info(f'Publishing Smartphone IMU to: {self.topic_name}')
        self.get_logger().info(f'Using frame_id: {self.frame_id}')

        local_ip = self.host_ip if self.host_ip else get_local_ip()
        url = f"http://{local_ip}:{self.port}"
        print_qr_code(url)

        # Start HTTP Server thread
        self.server = None
        self._start_http_server()

    def _start_http_server(self):
        node_ref = self

        class IMUHTTPRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default HTTP logging to keep console clean

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML_PAGE.encode('utf-8'))

            def do_POST(self):
                if self.path == '/imu':
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        node_ref.publish_imu(data)
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b'OK')
                    except Exception as e:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(str(e).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

        try:
            self.server = HTTPServer(('0.0.0.0', self.port), IMUHTTPRequestHandler)
            server_thread = Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()
            self.get_logger().info(f"Web IMU Server running on port {self.port}")
        except Exception as e:
            self.get_logger().error(f"Failed to start HTTP Server on port {self.port}: {e}")

    def publish_imu(self, data):
        """Publish sensor_msgs/msg/Imu message from smartphone JSON data."""
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.orientation_covariance[0] = -1.0

        ax = float(data.get('ax', 0.0))
        ay = float(data.get('ay', 0.0))
        az = float(data.get('az', 9.81))

        gx = float(data.get('gx', 0.0))
        gy = float(data.get('gy', 0.0))
        gz = float(data.get('gz', 0.0))

        msg.linear_acceleration = Vector3(x=ax, y=ay, z=az)
        msg.angular_velocity = Vector3(x=gx, y=gy, z=gz)

        self.publisher_.publish(msg)

    def destroy_node(self):
        if self.server:
            self.server.shutdown()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebImuPublisher()
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
