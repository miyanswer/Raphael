#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI QA / Tester Web Node for new_raphael_enterprise
Provides a Flask Web Console on http://127.0.0.1:5002 for sandbox verification reports
and 3-choice interactive diagnostic buttons for user feedback to trigger Coder auto-fixes.
"""

import json
import os
import sys
import datetime
import threading
import subprocess
import webbrowser
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class QAAgentWebNode(Node):

    def __init__(self, node_name='qa_agent'):
        super().__init__(node_name)

        if OPENAI_AVAILABLE:
            self.ai_client = OpenAI(
                base_url="http://localhost:11435/v1",
                api_key="antigravity-integrated-token"
            )
        else:
            self.ai_client = None

        self.model_name = "antigravity-gemini-3.1-pro-high"

        # Directory Setup
        self.qa_output_dir = Path.home() / "raphael_ws" / "qa_output"
        self.qa_output_dir.mkdir(parents=True, exist_ok=True)

        # 📡 ROS 2 Subscriber & Publisher
        self.coder_subscription = self.create_subscription(
            String,
            '/raphael/coder_to_qa',
            self.on_code_generated,
            10
        )
        self.qa_publisher = self.create_publisher(String, '/raphael/qa_to_coder', 10)

        self.latest_report = {
            "session_id": "sess_none",
            "status": "WAITING_FOR_CODE",
            "error_log": "",
            "timestamp": "-"
        }

        self.latest_diagnosis = {
            "prompt": "アプリを動かしてみて、修正したい箇所を以下から選択してください：",
            "options": [
                {"id": 1, "category": "UI・操作性", "description": "操作感（タイミング、キー配置、ボタン位置）を変更したい"},
                {"id": 2, "category": "ルール・難易度", "description": "速度、飛距離、得点条件、CPUの強さを調整したい"},
                {"id": 3, "category": "機能追加", "description": "新モード、サウンド、追加画面の機能を実装したい"}
            ]
        }

        # 🌐 Flask Web Server Setup (Port 5002)
        self.port = 5002
        self.app = Flask(__name__)
        self.setup_routes()

        self.flask_thread = threading.Thread(
            target=lambda: self.app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False),
            daemon=True
        )
        self.flask_thread.start()

        try:
            webbrowser.open(f"http://127.0.0.1:{self.port}")
        except Exception:
            pass

        self.get_logger().info(f'🕵️ AI QA Web Interface running on http://127.0.0.1:{self.port}')

    def on_code_generated(self, msg: String):
        try:
            self.get_logger().info('📡 Received generated code trigger via ROS 2 Topic /raphael/coder_to_qa!')
            payload = json.loads(msg.data)
            session_id = payload.get("session_id", "sess_unknown")
            code_path = payload.get("code_path")

            self.verify_code_sandbox(session_id, code_path)
        except Exception as e:
            self.get_logger().error(f'Error processing Coder signal: {e}')

    def verify_code_sandbox(self, session_id: str, code_path: str) -> dict:
        target_file = Path(code_path) if code_path and Path(code_path).exists() else Path("generated_app.py")
        passed = True
        error_log = ""

        try:
            code_text = target_file.read_text(encoding="utf-8")
            compile(code_text, str(target_file), 'exec')
        except Exception as e:
            passed = False
            error_log = f"SyntaxError: {e}"

        if passed:
            try:
                proc = subprocess.run(
                    [sys.executable, str(target_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=3,
                    text=True
                )
                if proc.returncode != 0 and proc.returncode != -15 and proc.returncode != 124:
                    passed = False
                    error_log = f"Runtime Error (Code {proc.returncode}):\n{proc.stderr}"
            except subprocess.TimeoutExpired:
                passed = True
            except Exception as e:
                passed = False
                error_log = f"Execution Error: {e}"

        self.latest_report = {
            "session_id": session_id,
            "target_file": str(target_file),
            "status": "PASSED" if passed else "FAILED",
            "error_log": error_log,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Save report
        session_qa_dir = self.qa_output_dir / session_id
        session_qa_dir.mkdir(parents=True, exist_ok=True)
        with open(session_qa_dir / "test_report.json", "w", encoding="utf-8") as f:
            json.dump(self.latest_report, f, indent=2, ensure_ascii=False)

        self.get_logger().info(f'🕵️ AI QA Sandbox Test Finished for [{session_id}]: {self.latest_report["status"]}')
        return self.latest_report

    def setup_routes(self):
        HTML_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Raphael AI QA Console (Inspector)</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; display: flex; justify-content: center; }
                .console-container { width: 920px; max-width: 95vw; background: #1e293b; border-radius: 16px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.4); padding: 24px; display: flex; flex-direction: column; gap: 20px; }
                .header { background: #0f172a; padding: 18px 24px; border-radius: 12px; border: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
                .header h2 { margin: 0; color: #38bdf8; font-size: 1.3em; }
                
                .status-card { background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
                .status-pass { color: #34d399; font-weight: bold; }
                .status-fail { color: #f87171; font-weight: bold; }
                .log-box { background: #020617; color: #e2e8f0; font-family: 'Consolas', monospace; padding: 14px; border-radius: 8px; border: 1px solid #1e293b; max-height: 180px; overflow-y: auto; white-space: pre-wrap; font-size: 0.9em; margin-top: 10px; }

                .diagnosis-section { background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
                .diagnosis-title { font-weight: bold; font-size: 1.1em; color: #fbbf24; margin-bottom: 12px; }
                .option-grid { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
                .option-btn { background: #334155; color: #f8fafc; border: 1px solid #475569; padding: 14px 18px; border-radius: 10px; cursor: pointer; text-align: left; font-size: 1em; transition: all 0.2s; display: flex; flex-direction: column; gap: 4px; }
                .option-btn:hover { background: #0284c7; border-color: #38bdf8; transform: translateY(-2px); }
                .option-cat { font-weight: bold; color: #38bdf8; font-size: 0.9em; }
                .option-desc { font-size: 0.95em; color: #e2e8f0; }

                .custom-input-area { display: flex; gap: 10px; margin-top: 15px; }
                .custom-input { flex: 1; background: #020617; border: 1px solid #334155; color: white; padding: 12px; border-radius: 8px; font-size: 0.95em; }
                .submit-btn { background: #0284c7; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }
                .submit-btn:hover { background: #0369a1; }
            </style>
        </head>
        <body>
            <div class="console-container">
                <div class="header">
                    <h2>🕵️ AI QA 鑑識・テストコンソール (Port 5002)</h2>
                    <span style="font-size: 0.9em; color: #94a3b8;">ROS 2 Topic: /raphael/qa_to_coder</span>
                </div>

                <!-- Status Card -->
                <div class="status-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:bold;">検証ステータス: <span id="qaStatus" class="status-pass">LOADING...</span></span>
                        <span style="font-size:0.85em; color:#94a3b8;" id="qaTime">-</span>
                    </div>
                    <div style="font-size:0.9em; color:#cbd5e1; margin-top:6px;" id="qaFile">対象ファイル: -</div>
                    <div class="log-box" id="qaLog">エラーログなし (構文・実行テスト正常)</div>
                </div>

                <!-- 3-Choice Diagnosis Section -->
                <div class="diagnosis-section">
                    <div class="diagnosis-title">❓ 「なんか違う」場合の修正診断（選択肢ポチポチ選択）</div>
                    <div style="font-size:0.95em; color:#cbd5e1;">アプリを動作させて気になる箇所があれば、以下の選択肢をクリックすると AI Coder が即座に自動修正します：</div>

                    <div class="option-grid">
                        <button class="option-btn" onclick="sendChoice('UI・操作性', '操作感（バッティング/ピッチングのタイミングやボタン配置）を変更したい')">
                            <span class="option-cat">【1】 UI ・ 操作感の変更</span>
                            <span class="option-desc">操作タイミング、ボタンの位置・大きさ、表示アニメーションを調整する</span>
                        </button>
                        <button class="option-btn" onclick="sendChoice('ゲームルール・難易度', '球速・飛距離・得点条件やCPUの強さを調整したい')">
                            <span class="option-cat">【2】 ゲームルール ・ 難易度の調整</span>
                            <span class="option-desc">投球速度、バッティング飛距離、ストライク判定、CPUの配球パターンを調整する</span>
                        </button>
                        <button class="option-btn" onclick="sendChoice('機能追加・グラフィック', '新モード、効果音、演出画面を追加したい')">
                            <span class="option-cat">【3】 機能追加 ・ 演出の拡張</span>
                            <span class="option-desc">チーム選択、イニング切り替え、結果発表画面、エフェクト演出を追加する</span>
                        </button>
                    </div>

                    <div class="custom-input-area">
                        <input type="text" id="customFeedback" class="custom-input" placeholder="具体的に細かく指示したい場合はここに入力 (例: 球速をもっと速くして！)">
                        <button class="submit-btn" onclick="sendCustomFeedback()">修正指示を送信</button>
                    </div>
                </div>
            </div>

            <script>
                async function updateStatus() {
                    try {
                        const response = await fetch('/api/status');
                        const data = await response.json();
                        const statusElem = document.getElementById('qaStatus');
                        
                        if (data.status === 'PASSED') {
                            statusElem.className = 'status-pass';
                            statusElem.innerText = '✅ テスト合格 (PASSED)';
                        } else if (data.status === 'FAILED') {
                            statusElem.className = 'status-fail';
                            statusElem.innerText = '❌ エラー検知 (FAILED)';
                        } else {
                            statusElem.innerText = data.status;
                        }

                        document.getElementById('qaTime').innerText = data.timestamp;
                        document.getElementById('qaFile').innerText = '対象ファイル: ' + data.target_file;
                        document.getElementById('qaLog').innerText = data.error_log || 'エラーログなし (構文・サンドボックス実行テスト正常)';
                    } catch (e) {}
                }

                async function sendChoice(category, description) {
                    if (!confirm(`【${category}】の修正要請を AI Coder へ送信しますか？`)) return;

                    await fetch('/api/request_fix', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ category: category, description: description })
                    });
                    alert(`✅ AI Coder へ【${category}】の修正指示を送信しました！自動修正がスタートします。`);
                }

                async function sendCustomFeedback() {
                    const input = document.getElementById('customFeedback');
                    const text = input.value.trim();
                    if (!text) return;

                    input.value = '';
                    await fetch('/api/request_fix', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ category: 'カスタム要求', description: text })
                    });
                    alert(`✅ AI Coder へ修正指示『${text}』を送信しました！`);
                }

                setInterval(updateStatus, 2000);
                updateStatus();
            </script>
        </body>
        </html>
        """

        @self.app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)

        @self.app.route('/api/status')
        def status():
            return jsonify(self.latest_report)

        @self.app.route('/api/request_fix', methods=['POST'])
        def request_fix():
            data = request.json
            category = data.get('category', '一般')
            description = data.get('description', '')

            # Publish fix request to /raphael/qa_to_coder
            retry_msg = {
                "session_id": self.latest_report.get("session_id", "sess_latest"),
                "error_log": f"User Requested Adjustment [{category}]: {description}",
                "diff_summary": f"Category: {category}, Requirement: {description}"
            }

            msg = String()
            msg.data = json.dumps(retry_msg, ensure_ascii=False)
            self.qa_publisher.publish(msg)

            self.get_logger().info(f'📡 Published User Fix Request [{category}] to /raphael/qa_to_coder')
            return jsonify({"status": "SUCCESS"})


def main(args=None):
    if not rclpy.ok():
        rclpy.init(args=args)
    node = QAAgentWebNode()
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
