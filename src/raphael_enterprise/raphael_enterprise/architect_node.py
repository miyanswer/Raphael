#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from example_interfaces.srv import Trigger  # ROS 2標準のTrigger型サービス
from openai import OpenAI
import os
import re
from pathlib import Path

class ArchitectNode(Node):
    def __init__(self):
        super().__init__('architect_node')
        
        # 👑 Antigravity IDEのローカルAPIに直結（設計専任モデル）
        self.ai_client = OpenAI(
            base_url="http://localhost:11435/v1",
            api_key="antigravity-integrated-token"
        )
        self.model_name = "antigravity-gemini-3.1-pro-high"

        # ワークスペースPath
        self.workspace_src = Path.home() / "raphael_ws" / "src"
        self.conversation_log = ""

        # 📥 CTOからの設計要請を受け取るROS 2 サービスサーバー
        self.srv = self.create_service(
            Trigger,
            '/raphael/generate_architecture',
            self.generate_architecture_callback
        )
        
        self.get_logger().info('📐 [Architectノード] 起動完了。CTOからの設計要請（Service）を待機中...')

    def scan_workspace(self):
        """~/raphael_ws/src の現状の物理構成を独立スキャン"""
        if not self.workspace_src.exists():
            return "ワークスペース (~/raphael_ws/src) が見つかりません。"

        structure_info = ["【現在のワークスペース物理構造】"]
        for root, dirs, files in os.walk(self.workspace_src):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'build', 'install', 'log']]
            level = root.replace(str(self.workspace_src), '').count(os.sep)
            indent = '  ' * level
            structure_info.append(f"{indent}📁 {os.path.basename(root)}/")
            sub_indent = '  ' * (level + 1)
            for f in files:
                if not f.endswith(('.pyc', '.pyo')):
                    structure_info.append(f"{sub_indent}📄 {f}")
        return "\n".join(structure_info)

    def generate_architecture_callback(self, request, response):
        self.get_logger().info('📐 [Architectノード] CTOから設計要求を受信。独立思考プロセスを開始します...')
        
        # 最新の対話ログファイルを読み込み（または直接テキスト解析）
        log_file = Path.home() / "raphael_ws" / "architectmd" / ".latest_chat.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                chat_log = f.read()
        else:
            chat_log = "会話ログが存在しません。"

        real_structure = self.scan_workspace()

        # 📐 Architect専用の純粋なシステムプロンプト（チャットの概念なし）
        architect_system = (
            "あなたは開発会社『Raphael』の最高建築士（Lead Architect）です。\n"
            "入力された『社長とCTOの決定ログ』と『現状のフォルダ構造』だけを分析し、\n"
            "実装担当者が100%迷わない完璧な設計図（Markdown）を新規構築しなさい。\n\n"
            "【絶対ルール】文頭の1行目には必ず `# ARCH_TITLE: <英語の短い識別名（例: web_fireworks_hello_world）>` を出力しなさい。\n\n"
            "【出力フォーマット】\n"
            "# ARCH_TITLE: <システム識別名>\n"
            "## 1. システム概要と決定された採用技術\n"
            "## 2. フォルダ・ファイル配置案（既存構成への差分）\n"
            "## 3. 各ファイルの役割と必要な実装仕様\n"
            "## 4. データ・制御の処理フロー"
        )

        try:
            prompt = f"{real_structure}\n\n【合意済み会話ログ】\n{chat_log}"
            
            ai_response = self.ai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": architect_system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000
            )
            
            arch_content = ai_response.choices[0].message.content.strip()

            # ファイル名の自動抽出
            filename_match = re.search(r'# ARCH_TITLE:\s*([a-zA-Z0-9_]+)', arch_content)
            custom_filename = filename_match.group(1).strip() if filename_match else "system_architecture"

            # 保存
            architect_dir = Path.home() / "raphael_ws" / "architectmd"
            architect_dir.mkdir(parents=True, exist_ok=True)
            md_file = architect_dir / f"{custom_filename}.md"
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(arch_content)

            self.get_logger().info(f'✅ [Architectノード] 設計書を出力完了: {md_file}')

            response.success = True
            response.message = f"✅ 『~/raphael_ws/architectmd/{custom_filename}.md』に自動保存しました！\n\n" + arch_content

        except Exception as e:
            self.get_logger().error(f'❌ [Architectノード] エラー: {e}')
            response.success = False
            response.message = f"[エラー] Architectノードでの生成失敗: {e}"

        return response

def main(args=None):
    rclpy.init(args=args)
    node = ArchitectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()