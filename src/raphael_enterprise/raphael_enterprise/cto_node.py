#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from example_interfaces.srv import Trigger
from openai import OpenAI
import threading
import webbrowser
import os
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory

class CtoNode(Node):
    def __init__(self):
        super().__init__('cto_node')
        
        # 👑 Antigravity IDEのローカルAPI（Gemini 3.1 Pro）
        self.ai_client = OpenAI(
            base_url="http://localhost:11435/v1",
            api_key="antigravity-integrated-token"
        )
        self.model_name = "antigravity-gemini-3.1-pro-high"

        # 🖼️ 画像保存用ディレクトリ (~/raphael_ws/imgs/)
        self.imgs_dir = Path.home() / "raphael_ws" / "imgs"
        self.imgs_dir.mkdir(parents=True, exist_ok=True)

        # 🎯 CTOのシステムプロンプト
        self.conversation_history = [
            {"role": "system", "content": (
                "あなたは開発会社『Raphael』のCTOであり、Miya社長の対等な技術パートナー（右腕）です。\n"
                "【絶対ルール】\n"
                "1. プログラムのコードを直接出力することは厳重に禁止します。\n"
                "2. 社長から『~/raphael_ws/imgs/』内の画像パスが指定された場合、その画像（構成図やイメージ等）の内容を深く分析してフィードバックを行いなさい。\n"
                "3. 社長から要望を受け取ったら、技術的な仕様について『2〜4つの明確な選択肢（A, B, C...）』を提示しなさい。\n"
                "4. 簡潔でスッキリした要点のみを返しなさい。"
            )}
        ]

        # 🔗 Architectノードとの通信
        self.cli = self.create_client(Trigger, '/raphael/generate_architecture')

        # 🌐 Flask（Webサーバー）
        self.app = Flask(__name__)
        self.setup_routes()

        self.flask_thread = threading.Thread(target=lambda: self.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False))
        self.flask_thread.daemon = True
        self.flask_thread.start()

        webbrowser.open("http://127.0.0.1:5000")
        self.get_logger().info('👔 [CTOノード] 起動完了。~/raphael_ws/imgs/ 連携機能対応。')

    def setup_routes(self):
        HTML_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Raphael CTO Office</title>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .chat-container { width: 900px; height: 85vh; background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: flex; flex-direction: column; overflow: hidden; }
                .chat-header { background: #0f172a; color: #38bdf8; padding: 18px; font-weight: bold; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
                .arch-btn { background: #10b981; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9em; }
                .chat-messages { flex: 1; padding: 25px; overflow-y: auto; background: #f8fafc; }
                .message { margin-bottom: 15px; max-width: 85%; padding: 12px 16px; border-radius: 8px; line-height: 1.5; font-size: 1.05em; word-wrap: break-word; white-space: pre-wrap; }
                .message.user { background: #0284c7; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
                .message.cto { background: #e2e8f0; color: #0f172a; margin-right: auto; border-bottom-left-radius: 2px; }
                .message.arch { background: #dcfce7; color: #14532d; margin: 15px auto; width: 95%; border: 1px solid #86efac; border-radius: 8px; font-family: monospace; }
                
                .chat-input-area { padding: 18px; background: white; border-top: 1px solid #e2e8f0; display: flex; flex-direction: column; }
                .input-row { display: flex; align-items: center; width: 100%; }
                .chat-input { flex: 1; border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; outline: none; font-size: 1.05em; }
                .img-picker-btn { background: #64748b; color: white; border: none; padding: 12px 15px; margin-left: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; }
                .send-btn { background: #0284c7; color: white; border: none; padding: 12px 20px; margin-left: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1em; }

                /* 🖼️ 画像選択モーダル・エリア */
                .image-modal { display: none; position: absolute; bottom: 80px; left: 20px; right: 20px; background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 220px; overflow-y: auto; z-index: 10; }
                .image-grid { display: flex; flex-wrap: wrap; gap: 10px; }
                .image-item { border: 2px solid transparent; border-radius: 6px; padding: 4px; cursor: pointer; text-align: center; width: 90px; }
                .image-item.selected { border-color: #0284c7; background: #e0f2fe; }
                .image-item img { width: 80px; height: 60px; object-fit: cover; border-radius: 4px; }
                .image-item label { font-size: 0.75em; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <span>👔 Raphael CTO (Gemini 3.1 Pro)</span>
                    <button id="archBtn" class="arch-btn" onclick="generateArchitecture()">📐 Architectノードへ設計要請</button>
                </div>
                <div class="chat-messages" id="chatMessages">
                    <div class="message cto">Miya社長、お疲れ様です！『~/raphael_ws/imgs/』に画像を置いて「🖼️」ボタンを押すと、読ませたい画像だけを選択して議論できます！</div>
                </div>

                <!-- 🖼️ 画像選択モーダル -->
                <div class="image-modal" id="imageModal">
                    <div style="font-weight:bold; font-size:0.9em; margin-bottom:8px; display:flex; justify-content:space-between;">
                        <span>🖼️ ~/raphael_ws/imgs/ 内の画像を選択</span>
                        <span style="cursor:pointer; color:#ef4444;" onclick="toggleImageModal()">✖ 閉じる</span>
                    </div>
                    <div class="image-grid" id="imageGrid">
                        <!-- 動的に画像一覧がここに読み込まれる -->
                    </div>
                </div>

                <div class="chat-input-area">
                    <div class="input-row">
                        <input type="text" id="userInput" class="chat-input" placeholder="要望やメッセージを入力..." onkeypress="if(event.keyCode==13) sendMessage()">
                        <button class="img-picker-btn" onclick="toggleImageModal()">🖼️</button>
                        <button class="send-btn" onclick="sendMessage()">送信</button>
                    </div>
                </div>
            </div>

            <script>
                let selectedImages = [];

                async function toggleImageModal() {
                    const modal = document.getElementById('imageModal');
                    if (modal.style.display === 'block') {
                        modal.style.display = 'none';
                    } else {
                        modal.style.display = 'block';
                        await loadImgsFolder();
                    }
                }

                async function loadImgsFolder() {
                    const response = await fetch('/api/get_imgs');
                    const files = await response.json();
                    const grid = document.getElementById('imageGrid');
                    grid.innerHTML = '';

                    if (files.length === 0) {
                        grid.innerHTML = '<span style="font-size:0.85em; color:#64748b;">~/raphael_ws/imgs/ 内に画像が見つかりません。</span>';
                        return;
                    }

                    files.forEach(filename => {
                        const isSelected = selectedImages.includes(filename);
                        const item = document.createElement('div');
                        item.className = `image-item ${isSelected ? 'selected' : ''}`;
                        item.onclick = () => toggleSelectImage(filename, item);

                        item.innerHTML = `
                            <img src="/imgs_static/${filename}" />
                            <label>${filename}</label>
                        `;
                        grid.appendChild(item);
                    });
                }

                function toggleSelectImage(filename, element) {
                    if (selectedImages.includes(filename)) {
                        selectedImages = selectedImages.filter(f => f !== filename);
                        element.classList.remove('selected');
                    } else {
                        selectedImages.push(filename);
                        element.classList.add('selected');
                    }
                }

                async function sendMessage() {
                    const input = document.getElementById('userInput');
                    const text = input.value.trim();
                    if (!text && selectedImages.length === 0) return;

                    input.value = '';
                    const sendImgs = [...selectedImages];
                    selectedImages = [];
                    document.getElementById('imageModal').style.display = 'none';

                    let displayMsg = text;
                    if (sendImgs.length > 0) {
                        displayMsg = `[参照画像: ${sendImgs.join(', ')}]\n` + text;
                    }
                    appendMessage(displayMsg, 'user');

                    const ctoContainer = appendMessage('思考中...', 'cto');

                    const response = await fetch('/api/talk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text, selected_images: sendImgs })
                    });
                    const data = await response.json();
                    ctoContainer.innerText = data.reply;
                }

                async function generateArchitecture() {
                    const archBtn = document.getElementById('archBtn');
                    archBtn.disabled = true;
                    const archContainer = appendMessage('📐 ROS 2 Service経由で Architectノードを起動中...', 'arch');

                    const response = await fetch('/api/architect', { method: 'POST' });
                    const data = await response.json();
                    archContainer.innerText = data.architecture;
                    archBtn.disabled = false;
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

        # 📂 imgs フォルダ内の静的ファイル提供
        @self.app.route('/imgs_static/<filename>')
        def serve_img(filename):
            return send_from_directory(self.imgs_dir, filename)

        # 🔍 imgs フォルダ内の画像ファイル一覧を取得
        @self.app.route('/api/get_imgs')
        def get_imgs():
            valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
            files = [f.name for f in self.imgs_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            return jsonify(files)

        @self.app.route('/api/talk', methods=['POST'])
        def talk():
            data = request.json
            miya_text = data.get('message', '')
            selected_images = data.get('selected_images', [])

            # 画像パスをメッセージに明示的に挿入
            if selected_images:
                img_paths_str = "\n".join([f"- {self.imgs_dir / img_name}" for img_name in selected_images])
                combined_text = f"【社長が指定したローカル参照画像パス】:\n{img_paths_str}\n\n【社長のコメント】:\n{miya_text}"
            else:
                combined_text = miya_text

            self.conversation_history.append({"role": "user", "content": combined_text})

            try:
                response = self.ai_client.chat.completions.create(
                    model=self.model_name,
                    messages=self.conversation_history,
                    max_tokens=1500
                )
                cto_reply = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": cto_reply})

                # 会話ログ（テキスト形式）を一時ファイルへ保存
                log_file = Path.home() / "raphael_ws" / "architectmd" / ".latest_chat.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)

                log_lines = [f"{m['role']}: {m['content']}" for m in self.conversation_history if m['role'] != 'system']
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(log_lines))

                return jsonify({"reply": cto_reply.strip()})
            except Exception as e:
                return jsonify({"reply": f"[エラー] CTO思考中断: {e}"})

        @self.app.route('/api/architect', methods=['POST'])
        def architect():
            if not self.cli.wait_for_service(timeout_sec=3.0):
                return jsonify({"architecture": "[エラー] Architectノードが起動していません。"})

            req = Trigger.Request()
            future = self.cli.call_async(req)

            while rclpy.ok() and not future.done():
                pass

            if future.result() is not None:
                res = future.result()
                return jsonify({"architecture": res.message})
            else:
                return jsonify({"architecture": "[エラー] Architectノード通信失敗"})

def main(args=None):
    rclpy.init(args=args)
    node = CtoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()