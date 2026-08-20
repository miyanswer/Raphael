#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI CTO (Director & Architect) Node for new_raphael_enterprise
Listens on ROS 2 Topic `/raphael/pm_to_cto` or reads ~/raphael_ws/pm_json/.
Uses Local LLM (http://localhost:11435/v1) with a robust multi-pattern parsing engine
to dynamically generate TypeScript contracts (types.ts), Mermaid diagrams (architecture.mermaid),
and QA test cases (test_cases.json).
Forbidden: Writing actual implementation code.
"""

import json
import os
import sys
import datetime
import re
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ArchitectCTONode(Node):

    def __init__(self, node_name='architect_cto'):
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

        # Directory Setup
        self.pm_json_dir = Path.home() / "raphael_ws" / "pm_json"
        self.cto_output_dir = Path.home() / "raphael_ws" / "cto_output"
        self.pm_json_dir.mkdir(parents=True, exist_ok=True)
        self.cto_output_dir.mkdir(parents=True, exist_ok=True)

        # 📡 ROS 2 Subscriber for PM -> CTO Topic Communication
        self.pm_subscription = self.create_subscription(
            String,
            '/raphael/pm_to_cto',
            self.on_pm_requirements_received,
            10
        )

        # 📡 ROS 2 Publisher for CTO -> Coder Topic Communication
        self.cto_publisher = self.create_publisher(String, '/raphael/cto_to_coder', 10)

        # 🎯 CTO System Prompt
        self.system_prompt = (
            "あなたはシステム開発プラットフォーム『Raphael』の『AI CTO（設計監督）』です。\n"
            "【目的】\n"
            "AI PM（通訳者）から届いた要件定義データを元に、要件に合わせたTypeScript型定義（types.ts）、"
            "Mermaid構成図（architecture.mermaid）、およびQAテスト判定基準（test_cases.json）を動的かつ精密に設計すること。\n"
            "【絶対ルール】\n"
            "1. 実際の詳細なプログラムソースコードを出力することは厳重に禁止します。\n"
            "2. 日本語の曖昧さを排除し、型・インターフェース定義と構造化データで仕様を固定してください。\n"
            "3. 各成果物を明確に識別できるよう、以下のタグで区切って出力してください:\n"
            "```typescript ... ``` (types.ts)\n"
            "```mermaid ... ``` (architecture.mermaid)\n"
            "```json ... ``` (test_cases.json)"
        )

        self.get_logger().info('👔 AI CTO Node initialized with ROS 2 Topic (/raphael/pm_to_cto) and Robust LLM Parser.')

    def on_pm_requirements_received(self, msg: String):
        """ROS 2 Topic Callback triggered when AI PM confirms new requirements."""
        try:
            self.get_logger().info('📡 Received new requirements via ROS 2 Topic /raphael/pm_to_cto!')
            req_data = json.loads(msg.data)
            self.design_system_from_data(req_data, req_file=None)
        except Exception as e:
            self.get_logger().error(f'Error processing topic message: {e}')

    def find_latest_requirements(self) -> tuple[Path, dict]:
        latest_pointer = self.pm_json_dir / "latest_requirements.json"
        if latest_pointer.exists():
            self.get_logger().info(f'Loading requirements from latest pointer: {latest_pointer}')
            with open(latest_pointer, "r", encoding="utf-8") as f:
                data = json.load(f)
            return latest_pointer, data

        req_files = sorted(
            self.pm_json_dir.glob("requirements_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if req_files:
            target_file = req_files[0]
            self.get_logger().info(f'Found latest requirements file by mtime: {target_file}')
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return target_file, data

        self.get_logger().warning('No requirements JSON found in ~/raphael_ws/pm_json/. Using default fallback.')
        fallback_data = {
            "session_id": "sess_default_fallback",
            "project_name": "Raphael_Default_Project",
            "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "status": "FALLBACK",
            "dialogue_history": "ROS 2 アクション型野球ゲーム (PC向け / 打撃・投球操作 / CPU対戦)"
        }
        return None, fallback_data

    def parse_llm_response(self, llm_output: str) -> tuple[str, str, dict]:
        """
        Robust Multi-Pattern Parser: Extracts types.ts, architecture.mermaid, and test_cases.json
        from LLM output using multiple regex strategies.
        """
        types_ts = None
        mermaid = None
        test_cases = None

        # Strategy 1: Codeblock markdown patterns (```ts, ```typescript, ```mermaid, ```json)
        ts_blocks = re.findall(r'```(?:typescript|ts)?\n(.*?)```', llm_output, re.DOTALL | re.IGNORECASE)
        for block in ts_blocks:
            if 'interface' in block or 'type ' in block:
                types_ts = block.strip()
                break

        mermaid_blocks = re.findall(r'```(?:mermaid)?\n(.*?)```', llm_output, re.DOTALL | re.IGNORECASE)
        for block in mermaid_blocks:
            if 'graph' in block or 'sequenceDiagram' in block or 'classDiagram' in block:
                mermaid = block.strip()
                break

        json_blocks = re.findall(r'```(?:json)?\n(.*?)```', llm_output, re.DOTALL | re.IGNORECASE)
        for block in json_blocks:
            if 'test_cases' in block or '"id"' in block:
                try:
                    test_cases = json.loads(block.strip())
                    break
                except Exception:
                    pass

        # Strategy 2: Tag-based patterns (---TYPES_START---, etc.)
        if not types_ts:
            m = re.search(r'---TYPES_START---(.*?)---TYPES_END---', llm_output, re.DOTALL)
            if m:
                types_ts = m.group(1).strip()

        if not mermaid:
            m = re.search(r'---MERMAID_START---(.*?)---MERMAID_END---', llm_output, re.DOTALL)
            if m:
                mermaid = m.group(1).strip()

        if not test_cases:
            m = re.search(r'---TESTCASES_START---(.*?)---TESTCASES_END---', llm_output, re.DOTALL)
            if m:
                try:
                    test_cases = json.loads(m.group(1).strip())
                except Exception:
                    pass

        # Strategy 3: Brute force JSON search for test_cases
        if not test_cases:
            json_candidates = re.findall(r'\{.*"test_cases".*\}', llm_output, re.DOTALL)
            for cand in json_candidates:
                try:
                    test_cases = json.loads(cand)
                    break
                except Exception:
                    pass

        return types_ts, mermaid, test_cases

    def design_system_with_llm(self, requirements_text: str, session_id: str) -> tuple[str, str, dict]:
        prompt = (
            f"以下は AI PM とユーザーの要件定義対話ログです (Session ID: {session_id}):\n"
            f"```\n{requirements_text}\n```\n\n"
            "この要件（例: 野球ゲーム、ロボット制御などユーザーが望む具体的なシステム）に特化した設計を行ってください。\n\n"
            "1. TypeScript の型・インターフェース定義 (types.ts)\n"
            "   ```typescript\n"
            "   // 要件に特化した interface / type を記述\n"
            "   ```\n\n"
            "2. Mermaid システム構成図 (architecture.mermaid)\n"
            "   ```mermaid\n"
            "   graph TD\n"
            "   // システムのデータフロー構成図\n"
            "   ```\n\n"
            "3. QA テスト合格基準 (test_cases.json)\n"
            "   ```json\n"
            "   {{\n"
            "     \"session_id\": \"{session_id}\",\n"
            "     \"test_cases\": [\n"
            "       {{\"id\": \"TC_001\", \"name\": \"...\", \"expected\": \"...\"}}\n"
            "     ]\n"
            "   }}\n"
            "   ```\n"
        )

        if self.ai_client:
            try:
                self.get_logger().info(f'Calling Local LLM for Session [{session_id}] design...')
                response = self.ai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2500
                )
                llm_output = response.choices[0].message.content
                self.get_logger().info('LLM Response received. Parsing artifacts with robust multi-pattern parser...')

                types_ts, mermaid, test_cases = self.parse_llm_response(llm_output)

                if types_ts and mermaid and test_cases:
                    self.get_logger().info('✅ Successfully parsed LLM artifacts!')
                    return types_ts, mermaid, test_cases
            except Exception as e:
                self.get_logger().error(f'LLM architectural design error: {e}')

        # Fallback Generator
        types_ts = f"""// Fallback System Type Definitions
// Session ID: {session_id}
export interface SystemState {{
    session_id: string;
    timestamp: number;
    status: 'IDLE' | 'RUNNING' | 'ERROR';
}}
"""
        mermaid = f"""graph TD
    User --> AIPM
    AIPM --> AICTO
    AICTO --> AICoder
"""
        test_cases = {
            "session_id": session_id,
            "test_cases": [{"id": "TC_001", "name": "Basic Contract Check", "expected": "PASS"}]
        }
        return types_ts, mermaid, test_cases

    def design_system_from_data(self, req_data: dict, req_file: Path = None) -> dict:
        session_id = req_data.get("session_id", "sess_unknown")
        project_name = req_data.get("project_name", "Raphael_Project")
        requirements_text = req_data.get("dialogue_history", "対話ログなし")

        self.get_logger().info(f'👔 AI CTO designing architecture for Session ID: [{session_id}]...')

        session_output_dir = self.cto_output_dir / session_id
        session_output_dir.mkdir(parents=True, exist_ok=True)
        latest_output_dir = self.cto_output_dir / "latest"
        latest_output_dir.mkdir(parents=True, exist_ok=True)

        types_ts, mermaid, test_cases = self.design_system_with_llm(requirements_text, session_id)

        # Save types.ts
        for out_dir in [session_output_dir, latest_output_dir]:
            with open(out_dir / "types.ts", "w", encoding="utf-8") as f:
                f.write(types_ts)

        # Save architecture.mermaid
        for out_dir in [session_output_dir, latest_output_dir]:
            with open(out_dir / "architecture.mermaid", "w", encoding="utf-8") as f:
                f.write(mermaid)

        # Save test_cases.json
        for out_dir in [session_output_dir, latest_output_dir]:
            with open(out_dir / "test_cases.json", "w", encoding="utf-8") as f:
                json.dump(test_cases, f, indent=2, ensure_ascii=False)

        if req_file and req_file.exists():
            req_data["status"] = "PROCESSED_BY_CTO"
            req_data["processed_at"] = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(req_file, "w", encoding="utf-8") as f:
                json.dump(req_data, f, indent=2, ensure_ascii=False)

        # 📡 Publish to /raphael/cto_to_coder for AI Coder
        payload = {
            "session_id": session_id,
            "project_name": project_name,
            "status": "CTO_DESIGN_COMPLETED"
        }
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.cto_publisher.publish(msg)

        self.get_logger().info(f'🎉 CTO completed design for [{session_id}]. Published to /raphael/cto_to_coder.')
        return test_cases

    def design_system(self) -> dict:
        req_file, req_data = self.find_latest_requirements()
        return self.design_system_from_data(req_data, req_file)


def main(args=None):
    if not rclpy.ok():
        rclpy.init(args=args)
    node = ArchitectCTONode()
    
    # If run directly as a CLI command, execute one-shot design and keep spinning for topic events
    node.design_system()
    
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
