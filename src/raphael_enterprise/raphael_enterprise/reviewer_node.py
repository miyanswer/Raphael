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

class ReviewerNode(Node):
    def __init__(self):
        super().__init__('reviewer_node')
        
        # 👑 Antigravity IDEのローカルAPI（正確なGemini IDを指定）
        self.ai_client = OpenAI(
            base_url="http://localhost:11435/v1",
            api_key="antigravity-integrated-token"
        )
        self.model_name = "antigravity-gemini-3.1-pro-high"

        # ワークスペース・設計書・画像ディレクトリ
        self.workspace_src = Path.home() / "raphael_ws" / "src"
        self.architect_dir = Path.home() / "raphael_ws" / "architectmd"
        self.imgs_dir = Path.home() / "raphael_ws" / "imgs"
        self.imgs_dir.mkdir(parents=True, exist_ok=True)

        # 🎯 修正チーム（Reviewer）のシステムプロンプト
        self.conversation_history = [
            {"role": "system", "content": (
                "あなたは開発会社『Raphael』の最高品質管理責任者・コード修正スペシャリスト（Lead Reviewer）です。\n"
                "あなたの役割はプログラムを直接書くことではなく、社長からの『ここを修正したい』『画面が崩れている』という要望や実行結果の画像に対して、\n"
                "既存のソースコードと設計書を分析し、どのように修正・改修すべきかを対話形式で具体的に詰めていくことです。\n"
                "【ルール】\n"
                "1. プログラムコードそのものを全量出力することは禁止します（修正方針・差分のロジックを説明しなさい）。\n"
                "2. 社長から『~/raphael_ws/imgs/』内の画像パスが指定された場合、その画像（実行結果や画面イメージ等）とソースコードを照らし合わせて不具合の原因と修正案を分析しなさい。\n"
                "3. 簡潔で的確な要点のみを返しなさい。"
            )}
        ]

        # 🔗 Architectノードとの通信クライアント
        self.cli = self.create_client(Trigger, '/raphael/generate_architecture')

        # 🌐 Flask (Webサーバー: ポート 5001)
        self.app = Flask(__name__)
        self.setup_routes()

        self.flask_thread = threading.Thread(target=lambda: self.app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False))
        self.flask_thread.daemon = True
        self.flask_thread.start()

        webbrowser.open("http://127.0.0.1:5001")
        self.get_logger().info('🔧 [修正チーム Reviewerノード] 起動完了。 http://127.0.0.1:5001 (ポート 5001)')

    def scan_code_content(self):
        """~/raphael_ws/src 内の主要なソースコードテキストを取得"""
        code_summary = ["【現在の実装コード構造と内容サマリー】"]
        if not self.workspace_src.exists():
            return "ソースコードフォルダが見つかりません。"

        for root, dirs, files in os.walk(self.workspace_src):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'build', 'install', 'log']]
            for f in files:
                if f.endswith('.py'):
                    file_path = Path(root) / f
                    try:
                        with open(file_path, "r", encoding="utf-8") as content_file:
                            code_summary.append(f"\n--- 📄 {file_path.relative_to(self.workspace_src)} ---\n" + content_file.read()[:2000])
                    except Exception:
                        pass
        return "\n".join(code_summary)

    def setup_routes(self):
        HTML_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Raphael Review & Refinement Team</title>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .chat-container { width: 950px; height: 88vh; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.12); display: flex; flex-direction: column; overflow: hidden; position: relative; }
                .chat-header { background: #0f172a; color: #f59e0b; padding: 18px; font-weight: bold; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
                .arch-btn { background: #d97706; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9em; transition: 0.2s; }
                .arch-btn:hover { background: #b45309; }
                .arch-btn:disabled { background: #9ca3af; cursor: not-allowed; }
                .chat-messages { flex: 1; padding: 25px; overflow-y: auto; background: #f8fafc; }
                .message { margin-bottom: 15px; max-width: 88%; padding: 12px 16px; border-radius: 8px; line-height: 1.5; font-size: 1.05em; word-wrap: break-word; white-space: pre-wrap; }
                .message.user { background: #d97706; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
                .message.reviewer { background: #e2e8f0; color: #0f172a; margin-right: auto; border-bottom-left-radius: 2px; }
                .message.arch { background: #fef3c7; color: #78350f; margin: 15px auto; width: 95%; border: 1px solid #fde68a; border-radius: 8px; font-family: monospace; }
                
                .selector-area { padding: 10px 18px; background: #fffbebf; border-bottom: 1px solid #fef3c7; display: flex; align-items: center; gap: 10px; font-size: 0.9em; font-weight: bold; color: #92400e; }
                .doc-select { padding: 6px 10px; border-radius: 4px; border: 1px solid #fde68a; outline: none; background: white; font-weight: bold; }
                
                .chat-input-area { padding: 18px; background: white; border-top: 1px solid #e2e8f0; display: flex; flex-direction: column; }
                .input-row { display: flex; align-items: center; width: 100%; }
                .chat-input { flex: 1; border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; outline: none; font-size: 1.05em; }
                .img-picker-btn { background: #64748b; color: white; border: none; padding: 12px 15px; margin-left: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; }
                .send-btn { background: #d97706; color: white; border: none; padding: 12px 20px; margin-left: 8px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1em; }
                .send-btn:hover { background: #b45309; }

                /* 🖼️ 画像選択モーダル */
                .image-modal { display: none; position: absolute; bottom: 80px; left: 20px; right: 20px; background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-height: 220px; overflow-y: auto; z-index: 10; }
                .image-grid { display: flex; flex-wrap: wrap; gap: 10px; }
                .image-item { border: 2px solid transparent; border-radius: 6px; padding: 4px; cursor: pointer; text-align: center; width: 90px; }
                .image-item.selected { border-color: #d97706; background: #fef3c7; }
                .image-item img { width: 80px; height: 60px; object-fit: cover; border-radius: 4px; }
                .image-item label { font-size: 0.75em; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <span>🔧 Raphael 修正チーム (Lead Reviewer)</span>
                    <button id="archBtn" class="arch-btn" onclick="generateArchitecture()">📐 Architectノードへ修正指示を送信</button>
                </div>

                <div class="selector-area">
                    <span>📄 修正対象の設計書を選択:</span>
                    <select id="docSelect" class="doc-select" onchange="loadSelectedDoc()">
                        <option value="">(選択なし - 現状コードのみ対象)</option>
                    </select>
                </div>

                <div class="chat-messages" id="chatMessages">
                    <div class="message reviewer">Miya社長、お疲れ様です！コード修正・機能追加専門のレビューチームです。\n実行結果のスクリーンショット（~/raphael_ws/imgs/内）を「🖼️」ボタンから選択して、「ここをこう直したい」と指示してください！</div>
                </div>

                <!-- 🖼️ 画像選択モーダル -->
                <div class="image-modal" id="imageModal">
                    <div style="font-weight:bold; font-size:0.9em; margin-bottom:8px; display:flex; justify-content:space-between;">
                        <span>🖼️ ~/raphael_ws/imgs/ 内の実行結果画像を選択</span>
                        <span style="cursor:pointer; color:#ef4444;" onclick="toggleImageModal()">✖ 閉じる</span>
                    </div>
                    <div class="image-grid" id="imageGrid">
                        <!-- 動的に画像一覧が読み込まれる -->
                    </div>
                </div>

                <div class="chat-input-area">
                    <div class="input-row">
                        <input type="text" id="userInput" class="chat-input" placeholder="修正したい内容や不具合を入力..." onkeypress="if(event.keyCode==13) sendMessage()">
                        <button class="img-picker-btn" onclick="toggleImageModal()">🖼️</button>
                        <button class="send-btn" onclick="sendMessage()">送信</button>
                    </div>
                </div>
            </div>

            <script>
                let selectedImages = [];

                window.onload = async function() {
                    await fetchDocs();
                };

                async function fetchDocs() {
                    const response = await fetch('/api/get_docs');
                    const docs = await response.json();
                    const select = document.getElementById('docSelect');
                    docs.forEach(doc => {
                        const opt = document.createElement('option');
                        opt.value = doc;
                        opt.innerText = doc;
                        select.appendChild(opt);
                    });
                }

                async function loadSelectedDoc() {
                    const docName = document.getElementById('docSelect').value;
                    if (!docName) return;
                    
                    const response = await fetch('/api/select_doc', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ doc_name: docName })
                    });
                    const data = await response.json();
                    appendMessage(`📄 設計書 『${docName}』 を読み込みました。`, 'reviewer');
                }

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
                        displayMsg = `[参照実行画面: ${sendImgs.join(', ')}]\n` + text;
                    }
                    appendMessage(displayMsg, 'user');

                    const revContainer = appendMessage('既存コードと実行画像から課題を解析中...', 'reviewer');

                    const response = await fetch('/api/talk', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text, selected_images: sendImgs })
                    });
                    const data = await response.json();
                    revContainer.innerText = data.reply;
                }

                async function generateArchitecture() {
                    const archBtn = document.getElementById('archBtn');
                    archBtn.disabled = true;
                    const archContainer = appendMessage('📐 ROS 2 Service経由で Architectノードへ修正版設計図の作成をリクエスト中...', 'arch');

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

        # 🔍 imgs フォルダ内の画像一覧取得
        @self.app.route('/api/get_imgs')
        def get_imgs():
            valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
            files = [f.name for f in self.imgs_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            return jsonify(files)

        @self.app.route('/api/get_docs')
        def get_docs():
            if not self.architect_dir.exists():
                return jsonify([])
            docs = [f.name for f in self.architect_dir.glob("*.md") if not f.name.startswith(".")]
            return jsonify(docs)

        @self.app.route('/api/select_doc', methods=['POST'])
        def select_doc():
            data = request.json
            doc_name = data.get('doc_name', '')
            doc_path = self.architect_dir / doc_name
            
            if doc_path.exists():
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.conversation_history.append({
                    "role": "user", 
                    "content": f"【修正対象として指定された既存設計書: {doc_name}】\n```markdown\n{content}\n```"
                })
                return jsonify({"status": "ok"})
            return jsonify({"status": "error"})

        @self.app.route('/api/talk', methods=['POST'])
        def talk():
            data = request.json
            miya_text = data.get('message', '')
            selected_images = data.get('selected_images', [])

            code_context = self.scan_code_content()

            if selected_images:
                img_paths_str = "\n".join([f"- {self.imgs_dir / img_name}" for img_name in selected_images])
                combined_prompt = f"{code_context}\n\n【社長が提示した実行結果の画像パス】:\n{img_paths_str}\n\n【社長からの修正・改善要望】:\n{miya_text}"
            else:
                combined_prompt = f"{code_context}\n\n【社長からの修正・改善要望】:\n{miya_text}"

            self.conversation_history.append({"role": "user", "content": combined_prompt})

            try:
                response = self.ai_client.chat.completions.create(
                    model=self.model_name,
                    messages=self.conversation_history,
                    max_tokens=1800
                )
                reply = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": reply})

                # 会話ログを共有ファイルへ出力（Architectノード用）
                log_file = self.architect_dir / ".latest_chat.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                log_lines = [f"{m['role']}: {m['content']}" for m in self.conversation_history if m['role'] != 'system']
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(log_lines))

                return jsonify({"reply": reply.strip()})
            except Exception as e:
                return jsonify({"reply": f"[エラー] Reviewer思考中断: {e}"})

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
    node = ReviewerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()