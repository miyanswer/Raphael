#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI PM (通訳者) Web Interface Node for new_raphael_enterprise
Uses IDE local LLM (http://localhost:11435/v1) and Flask Web UI to interview users
via 3-4 structured choice options, generates requirements.json, and publishes to /raphael/pm_to_cto.
Forbidden: Writing code or complex jargon.
"""

import json
import os
import sys
import threading
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


class InterpreterPMWebNode(Node):

    def __init__(self, node_name='interpreter_pm'):
        super().__init__(node_name)

        # 👑 IDE Local API Configuration (Gemini 3.1 Pro / Antigravity Local)
        if OPENAI_AVAILABLE:
            self.ai_client = OpenAI(
                base_url="http://localhost:11435/v1",
                api_key="antigravity-integrated-token"
            )
        else:
            self.ai_client = None

        self.model_name = "antigravity-gemini-3.1-pro-high"

        # 📡 ROS 2 Publisher for PM -> CTO Topic Communication
        self.pm_publisher = self.create_publisher(String, '/raphael/pm_to_cto', 10)

        # 🎯 AI PM (Interpreter) System Prompt
        self.system_prompt = (
            "あなたはシステム開発プラットフォーム『Raphael』の『AI PM（通訳者）』です。\n"
            "【目的】\n"
            "非エンジニアのユーザーから『こんなシステムを作りたい』という曖昧な要望を聞き出し、選択肢インタビューを通じて要件を深掘りすること。\n"
            "【絶対ルール】\n"
            "1. プログラムのコード生成や技術的な詳細設計は絶対に禁止します。\n"
            "2. 専門用語を避け、ユーザーが直感的に答えられる『2〜4つの明確な選択肢（A, B, C...）』を提示して要件を選択させてください。\n"
            "3. 会話の最後には要件のまとめを提示し、構造化データを作成できる準備を整えてください。\n"
            "4. 丁寧かつ親しみやすい案内役として対話してください。"
        )

        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 🌐 Flask Web Server Setup (Port 5001)
        self.port = 5001
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

        self.get_logger().info(f'📋 AI PM Web Interface running on http://127.0.0.1:{self.port} (Topic: /raphael/pm_to_cto)')

    def setup_routes(self):
        HTML_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Raphael AI PM Office (Interpreter)</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .chat-container { width: 900px; max-width: 95vw; height: 88vh; background: #1e293b; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); display: flex; flex-direction: column; overflow: hidden; border: 1px solid #334155; }
                .chat-header { background: #0f172a; color: #38bdf8; padding: 18px 24px; font-weight: bold; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
                .export-btn { background: #10b981; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.9em; transition: all 0.2s; }
                .export-btn:hover { background: #059669; transform: translateY(-1px); }
                .chat-messages { flex: 1; padding: 24px; overflow-y: auto; background: #0f172a; display: flex; flex-direction: column; gap: 16px; }
                .message { max-width: 85%; padding: 14px 18px; border-radius: 12px; line-height: 1.6; font-size: 1.02em; word-wrap: break-word; white-space: pre-wrap; }
                .message.user { background: #0284c7; color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
                .message.pm { background: #334155; color: #f8fafc; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #475569; }
                .message.system { background: #064e3b; color: #6ee7b7; align-self: center; width: 90%; border: 1px solid #059669; text-align: center; }
                
                .chat-input-area { padding: 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 12px; }
                .chat-input { flex: 1; background: #0f172a; color: white; border: 1px solid #475569; padding: 14px; border-radius: 8px; outline: none; font-size: 1em; }
                .chat-input:focus { border-color: #38bdf8; }
                .send-btn { background: #0284c7; color: white; border: none; padding: 14px 24px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1em; transition: background 0.2s; }
                .send-btn:hover { background: #0369a1; }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <span>📋 Raphael AI PM（要件定義ヒアリング）</span>
                    <button class="export-btn" onclick="exportRequirements()">💾 要件確定 ＆ CTOへ送信 (Topic)</button>
                </div>
                <div class="chat-messages" id="chatMessages">
                    <div class="message pm">こんにちは！Raphael AI PMです。どんなシステムやアプリを作りたいか、思い描いているイメージを教えてください！選択肢を交えながら要件を形にしていきます。</div>
                </div>

                <div class="chat-input-area">
                    <input type="text" id="userInput" class="chat-input" placeholder="例: 野球ゲームを作りたい..." onkeypress="if(event.keyCode==13) sendMessage()">
                    <button class="send-btn" onclick="sendMessage()">送信</button>
                </div>
            </div>

            <script>
                async function sendMessage() {
                    const input = document.getElementById('userInput');
                    const text = input.value.trim();
                    if (!text) return;

                    input.value = '';
                    appendMessage(text, 'user');
                    const pmContainer = appendMessage('考え中...', 'pm');

                    try {
                        const response = await fetch('/api/talk', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: text })
                        });
                        const data = await response.json();
                        pmContainer.innerText = data.reply;
                    } catch (e) {
                        pmContainer.innerText = '[エラー] 通信に失敗しました。';
                    }
                }

                async function exportRequirements() {
                    const sysMsg = appendMessage('💾 要件をまとめ、requirements.json 保存 ＆ トピック(/raphael/pm_to_cto)へ送信中...', 'system');
                    try {
                        const response = await fetch('/api/export_requirements', { method: 'POST' });
                        const data = await response.json();
                        sysMsg.innerText = `✅ 要件確定！(Session ID: ${data.session_id}) トピック配信完了 ➔ CTO自動設計スタート！`;
                    } catch (e) {
                        sysMsg.innerText = '[エラー] 要件定義データの生成・送信に失敗しました。';
                    }
                }

                function appendMessage(text, sender) {
                    const messagesDiv = document.getElementById('chatMessages');
                    const msgDiv = document.createElement('div');
                    msgDiv.className = `message ${sender}`;
                    msgDiv.innerText = text;
                    messagesDiv.appendChild(msgDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    return msgDiv;
                }
            </script>
        </body>
        </html>
        """

        @self.app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)

        @self.app.route('/api/talk', methods=['POST'])
        def talk():
            data = request.json
            user_text = data.get('message', '')

            self.conversation_history.append({"role": "user", "content": user_text})

            if self.ai_client:
                try:
                    response = self.ai_client.chat.completions.create(
                        model=self.model_name,
                        messages=self.conversation_history,
                        max_tokens=1200
                    )
                    pm_reply = response.choices[0].message.content
                except Exception as e:
                    pm_reply = f"[LLM接続エラー] ローカルAPIの呼び出しに失敗しました: {e}"
            else:
                pm_reply = (
                    f"【AI PM応答】『{user_text}』について要件を深掘りします。\n"
                    "以下の選択肢から希望を選んでください：\n\n"
                    "[A] アクション型（打撃・投球操作）\n"
                    "[B] 監督シミュレーション型\n"
                    "[C] スマホ向けカジュアルミニゲーム"
                )

            self.conversation_history.append({"role": "assistant", "content": pm_reply})
            return jsonify({"reply": pm_reply.strip()})

        @self.app.route('/api/export_requirements', methods=['POST'])
        def export_requirements():
            import datetime
            import uuid

            pm_json_dir = Path.home() / "raphael_ws" / "pm_json"
            pm_json_dir.mkdir(parents=True, exist_ok=True)

            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"sess_{now_str}_{uuid.uuid4().hex[:6]}"

            summary_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in self.conversation_history if m['role'] != 'system']
            )
            requirements_data = {
                "session_id": session_id,
                "project_name": "Raphael_User_Project",
                "timestamp": now_str,
                "status": "CONFIRMED_BY_PM",
                "dialogue_history": summary_text
            }

            # 1. Save timestamped unique JSON file
            filename = f"requirements_{now_str}_{session_id}.json"
            filepath = pm_json_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(requirements_data, f, indent=2, ensure_ascii=False)

            # 2. Update latest_requirements.json
            latest_filepath = pm_json_dir / "latest_requirements.json"
            with open(latest_filepath, "w", encoding="utf-8") as f:
                json.dump(requirements_data, f, indent=2, ensure_ascii=False)

            # 📡 3. Publish requirements data to ROS 2 Topic /raphael/pm_to_cto
            msg = String()
            msg.data = json.dumps(requirements_data, ensure_ascii=False)
            self.pm_publisher.publish(msg)
            self.get_logger().info(f'📡 Published requirements for [{session_id}] to ROS 2 topic /raphael/pm_to_cto')

            return jsonify({
                "status": "SUCCESS",
                "session_id": session_id,
                "filepath": str(filepath),
                "latest_filepath": str(latest_filepath)
            })


def main(args=None):
    if not rclpy.ok():
        rclpy.init(args=args)
    node = InterpreterPMWebNode()
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
