# ARCH_TITLE: ros2_course_lap_simulation_revised_v2

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが8区間（直線L1〜L4・カーブC1〜C4）から成るループコースを一周するPythonシミュレーション。  
今回の改訂では以下3点が社長・CTO間で合意済み・確定した。

| 合意項目 | 決定内容 |
|---------|---------|
| コース寸法 | L1=15m基準・比率1:5:3:4・カーブはβ案（閉じ条件逆算） |
| ロボット車幅 | ROBOT_WHEEL_BASE を 0.3m → **0.8m** に変更 |
| コース幅 | COURSE_WIDTH = **7.0m**（中心線から3.5mずつ）をconfig.pyに定義のみ追加 |
| 将来予定 | 3D表示（Panda3D/Pygame）・路面テクスチャ（黒路面・白線・緑エリア）は次フェーズ |

### 確定コース寸法パラメータ（改訂版）

#### 閉じ条件の数学的証明

全カーブが90°右旋回×4回 = 合計360°旋回により方向は自動的に元に戻る。  
XY方向の移動量を閉じさせるための拘束式：

```
(C1_r + C2_r) - (C3_r + C4_r) = L2 - L4
(12.0 + 10.0) - (3.5  + 3.5 ) = 75.0 - 60.0
            15.0               =    15.0   ✅
```

#### 確定パラメータテーブル

| 区間 | 種別 | 長さ / 半径 | 角度 | 備考 |
|------|------|------------|------|------|
| L1 | 直線 | **15.0 m** | - | スタート/ゴール基準直線（比率基準=1） |
| C1 | 円弧 | r = **12.0 m** | 90° 右旋回 | β案逆算・大カーブ |
| L2 | 直線 | **75.0 m** | - | 比率×5 |
| C2 | 円弧 | r = **10.0 m** | 90° 右旋回 | β案逆算・中カーブ |
| L3 | 直線 | **45.0 m** | - | 比率×3 |
| C3 | 円弧 | r = **3.5 m** | 90° 右旋回 | コース幅内最小半径 |
| L4 | 直線 | **60.0 m** | - | 比率×4 |
| C4 | 円弧 | r = **3.5 m** | 90° 右旋回 | コース幅内最小半径 |

### 決定された採用技術（変更なし）

| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10以上 |
| 描画 | `matplotlib` + `FuncAnimation`（現フェーズ） |
| 数値計算 | `numpy` |
| 自己位置推定 | 順序制約トポロジカル推定（カメラ主軸） |
| ノード数 | 16ノード（N01〜N16） |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```
📁 src/
  📁 raphael_enterprise/          # 変更なし
    （省略）
  📁 web/                         # 変更なし
    （省略）
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # 変更なし
    📄 course.py                  # 変更なし（ロジック変更不要）
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # 変更なし
    📄 config.py                  # ★変更★ 今回の唯一の修正対象
    📁 logs/
      📄 .gitkeep                 # 変更なし
    📁 tests/
      📄 __init__.py              # 変更なし
      📄 test_course.py           # ★注意★ 後述の閉じ判定追加が必要
      📄 test_node_manager.py     # 変更なし
```

### 差分サマリー

| 操作 | 対象ファイル | 変更内容 |
|------|------------|---------|
| **変更** | `simulation/config.py` | SEGMENTS寸法・ROBOT_WHEEL_BASE・COURSE_WIDTH新規追加・NODE_TRIGGER_DISTANCE・COURSE_CLOSE_TOLERANCE |
| **注意** | `simulation/tests/test_course.py` | 閉じ距離assertが未実装のまま。本設計書で仕様を確定する |
| **変更なし** | 上記以外の全ファイル | 既存ロジックへの影響ゼロ |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― 変更仕様（完全差分）

**変更ルール**：このファイルのみ編集する。他ファイルは一切触らない。

#### 変更前 → 変更後 の差分一覧

**【SEGMENTS ブロック】完全置き換え**

```
# 変更前
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 5.0},
    {"id": "C1", "type": "arc", "radius": 2.0,  "angle_deg": 90, "direction": "right"},
    {"id": "L2", "type": "straight", "length": 3.0},
    {"id": "C2", "type": "arc", "radius": 0.8,  "angle_deg": 90, "direction": "right"},
    {"id": "L3", "type": "straight", "length": 6.2},
    {"id": "C3", "type": "arc", "radius": 1.0,  "angle_deg": 90, "direction": "right"},
    {"id": "L4", "type": "straight", "length": 3.8},
    {"id": "C4", "type": "arc", "radius": 1.0,  "angle_deg": 90, "direction": "right"},
]

# 変更後
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 15.0},
    {"id": "C1", "type": "arc", "radius": 12.0, "angle_deg": 90, "direction": "right"},
    {"id": "L2", "type": "straight", "length": 75.0},
    {"id": "C2", "type": "arc", "radius": 10.0, "angle_deg": 90, "direction": "right"},
    {"id": "L3", "type": "straight", "length": 45.0},
    {"id": "C3", "type": "arc", "radius": 3.5,  "angle_deg": 90, "direction": "right"},
    {"id": "L4", "type": "straight", "length": 60.0},
    {"id": "C4", "type": "arc", "radius": 3.5,  "angle_deg": 90, "direction": "right"},
]
```

**【ロボットパラメータ ブロック】1行変更 + 1行追加**

```
# 変更前
ROBOT_WHEEL_BASE = 0.3    # 左右輪間距離 [m]

# 変更後
ROBOT_WHEEL_BASE = 0.8    # 左右輪間距離 [m] ← 0.3 → 0.8 に変更
```

**【コース幅パラメータ】新規追加（ロボットパラメータブロックの直下に挿入）**

```
# 新規追加
COURSE_WIDTH = 7.0        # コース全幅 [m]（中心線から左右それぞれ3.5m）
# 現フェーズでは定義のみ。visualizer.py からの参照は3D実装フェーズで行う。
```

**【ノード認識パラメータ ブロック】変更 + 追加**

```
# 変更前
NODE_TRIGGER_DISTANCE = 0.1    # ノードとみなす距離閾値 [m]

# 変更後
NODE_TRIGGER_DISTANCE = 0.5    # ノードとみなす距離閾値 [m]
                               # ← 0.1 → 0.5 に変更
                               # 理由: コース全長が約9倍になりSTEP_SIZE積算誤差が拡大

# 新規追加（NODE_TRIGGER_DISTANCEの直下に挿入）
COURSE_CLOSE_TOLERANCE = 1.0   # コース閉じ判定の許容距離 [m]
                               # NODE_TRIGGER_DISTANCEとは独立したパラメータ
                               # test_course.py の test_course_is_closed() が参照する
```

#### 変更後の `config.py` 完成イメージ（全体構造）

```
import os

# 【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 15.0},
    {"id": "C1", "type": "arc", "radius": 12.0, "angle_deg": 90, "direction": "right"},
    {"id": "L2", "type": "straight", "length": 75.0},
    {"id": "C2", "type": "arc", "radius": 10.0, "angle_deg": 90, "direction": "right"},
    {"id": "L3", "type": "straight", "length": 45.0},
    {"id": "C3", "type": "arc", "radius": 3.5,  "angle_deg": 90, "direction": "right"},
    {"id": "L4", "type": "straight", "length": 60.0},
    {"id": "C4", "type": "arc", "radius": 3.5,  "angle_deg": 90, "direction": "right"},
]

# 【ロボットパラメータ】
ROBOT_WHEEL_BASE = 0.8         # 左右輪間距離 [m] ← 更新
ROBOT_SPEED = 0.5              # 走行速度 [m/s]（変更なし）
SIMULATION_DT = 0.05           # 時間刻み [s]（変更なし）

# 【コース幅パラメータ】← 新規追加ブロック
COURSE_WIDTH = 7.0             # コース全幅 [m]（中心線から左右3.5mずつ）
                               # 現フェーズ: 定義のみ（3D実装フェーズで使用）

# 【描画パラメータ】（変更なし）
FPS = 30
COURSE_LINE_COLOR = "black"
COURSE_LINE_WIDTH = 2
ROBOT_COLOR = "royalblue"
ROBOT_ARROW_COLOR = "red"
NODE_MARKER_COLOR = "orange"
NODE_FONT_SIZE = 8

# 【ノード認識パラメータ】← 変更あり
NODE_TRIGGER_DISTANCE = 0.5    # ノードとみなす距離閾値 [m] ← 0.1 → 0.5 に更新
COURSE_CLOSE_TOLERANCE = 1.0   # コース閉じ判定許容距離 [m] ← 新規追加

# 【カメラシミュレータパラメータ】（変更なし）
NOISE_STD = 0.05

# 【ログパラメータ】（変更なし）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILENAME = "run_log.csv"
```

---

### 3-2. `tests/test_course.py` ― 閉じ判定の仕様確定（実装必須）

現在の `test_course_is_closed()` は **コースが閉じているかどうかを検証していない**（形状チェックのみ）。  
今回 `COURSE_CLOSE_TOLERANCE` を追加したタイミングで以下の仕様に更新する。

**変更前の問題箇所：**

```
# 現在のコード（閉じ確認が欠落している）
def test_course_is_closed():
    cg = CourseGenerator(config.SEGMENTS)
    points = cg.generate_course_points()
    assert len(points) > 0
    assert points.shape[1] == 2
    # ← ここで終わっており、始点と終点の距離チェックが存在しない
```

**変更後の実装仕様：**

```
def test_course_is_closed():
    【追加する処理】
    cg = CourseGenerator(config.SEGMENTS)
    points = cg.generate_course_points()

    # 既存のアサーション（変更なし）
    assert len(points) > 0
    assert points.shape[1] == 2

    # ★ 以下を追記 ★
    start = points[0]    # コース始点 (0.0, 0.0)
    end   = points[-1]   # コース終点（閉じていれば始点に近い）
    distance = numpy.linalg.norm(end - start)

    assert distance < config.COURSE_CLOSE_TOLERANCE, (
        f"コースが閉じていません: 始点-終点間距離 = {distance:.4f}m "
        f"(許容値: {config.COURSE_CLOSE_TOLERANCE}m)\n"
        f"始点: {start}, 終点: {end}"
    )
```

**変更対象：** `simulation/tests/test_course.py`  
**追加import：** ファイル先頭の `import numpy as np` は既に存在するため追加不要  
**追加参照：** `config.COURSE_CLOSE_TOLERANCE`（今回新規定義済み）

---

### 3-3. 変更なし確認済みファイル

以下のファイルは **コードの1行も変更しない**。  
実装担当者は触らないこと。

| ファイル | 理由 |
|---------|------|
| `course.py` | SEGMENTSのループ処理ロジックは汎用設計済み。寸法変更を自動吸収する |
| `robot.py` | ROBOT_WHEEL_BASEを参照していない（ロジックに未使用）。変更不要 |
| `node_manager.py` | NODE_TRIGGER_DISTANCEはconfig参照のため自動反映される |
| `camera_simulator.py` | 変更なし |
| `visualizer.py` | COURSE_WIDTHは参照していない。変更なし |
| `main.py` | 変更なし |

---

## 4. データ・制御の処理フロー

### 4-1. 今回の変更がシステム全体に波及する経路

```
config.py（変更）
  │
  ├─ SEGMENTS（寸法変更）
  │    └──► course.py: generate_course_points()
  │              │  ループ処理は変更なし
  │              │  出力される course_points の総点数が増加
  │              │  （旧: 約600点 → 新: 約約11,450点 ※STEP_SIZE=0.02m時）
  │              │
  │              ├──► visualizer.py: __init__() でコース描画
  │              │         → 描画範囲が自動的に拡大（set_aspect('equal')で吸収）
  │              │
  │              └──► main.py: total_frames = len(course_points) - 1
  │                        → フレーム数が自動的に増加（約11,449フレーム）
  │
  ├─ NODE_TRIGGER_DISTANCE（0.1 → 0.5）
  │    └──► node_manager.py: update() の dist 判定閾値が自動反映
  │
  ├─ COURSE_CLOSE_TOLERANCE（新規追加）
  │    └──► tests/test_course.py: test_course_is_closed() で参照（要追記）
  │
  ├─ ROBOT_WHEEL_BASE（0.3 → 0.8）
  │    └──► 現フェーズでは参照箇所なし（影響ゼロ）
  │         将来: robot.py の差動二輪制御計算で使用予定
  │
  └─ COURSE_WIDTH（新規追加）
       └──► 現フェーズでは参照箇所なし（影響ゼロ）
            将来: visualizer.py の路面ポリゴン描画で使用予定
```

### 4-2. 毎フレームの更新フロー（変更なし・参考）

```
FuncAnimation が frame_index を increment → update_frame() 呼び出し
  │
  ▼
robot.update_along_course(course_points, frame_index)
  │  course_points[frame_index] → x, y, theta を更新
  │  odom_distance += 移動量
  ▼
node_manager.update(robot.x, robot.y)
  │  次ノード候補（current_index + 1 のみ）との距離を計算
  │  距離 < NODE_TRIGGER_DISTANCE（= 0.5m）→ ノード遷移確定
  ▼
node_manager.get_current_segment_id()
  │  現在ノードIDから区間ID（L1〜C4）を返す
  ▼
camera_sim.get_features(segment_id, cg)
  │  curvature / asymmetry / convergence を計算（ログ用途のみ）
  ▼
visualizer.update_frame(frame_index, robot, node_manager)
  │  Layer4: ロボット位置点を更新
  │  Layer5: 向き矢印を更新
  │  Layer6: タイトル文字列を更新
  │  "Frame:xxx | Node:N05 | Segment:L2 | Dist:xxx.xxm"
  ▼
ラップ完了チェック → export_log() → "LAP COMPLETED"
  ▼
matplotlib が描画を更新 → 次フレームへ
```

### 4-3. 実装後の動作確認手順（実装担当者への指示）

実装完了後、以下の順序で確認すること。

```
Step1: テスト実行
  cd src/simulation
  python -m pytest tests/test_course.py -v
  
  確認項目：
  ✅ test_course_is_closed  → PASSED（距離 < 1.0m）
  ✅ test_node_count        → PASSED（16ノード）

Step2: テスト実行
  python -m pytest tests/test_node_manager.py -v
  
  確認項目：
  ✅ test_sequential_transition  → PASSED
  ✅ test_no_skip_transition     → PASSED
  ✅ test_lap_completion         → PASSED

Step3: シミュレーション起動
  cd src
  python -m simulation.main
  
  目視確認項目：
  ✅ コース形状が「角丸四角形」でなく、各辺の長さ比が明確に異なる形状になっている
     （L1:L2:L3:L4 = 15:75:45:60 m の長方形系）
  ✅ C1・C2（r=12, 10m）が緩い大カーブに見える
  ✅ C3・C4（r=3.5m）が鋭い小カーブに見える
  ✅ ロボットがN02スタートからN01に戻るまで走行する
  ✅ "LAP COMPLETED" がコンソールに出力される
  ✅ logs/run_log.csv が生成される
```

### 4-4. 将来拡張ポイント（次フェーズへの申し送り）

| フェーズ | 拡張項目 | 使用するconfig変数 | 対象ファイル |
|---------|---------|-----------------|------------|
| 次フェーズ（3D化） | 路面ポリゴン（黒路面・白線） | `COURSE_WIDTH = 7.0` | `visualizer.py` に新規レイヤー追加 |
| 次フェーズ（3D化） | コース外緑エリア描画 | `COURSE_WIDTH` | `visualizer.py` |
| 次フェーズ（3D化） | ロボット一人称カメラ視点 | - | `visualizer.py` をPanda3D等に置換 |
| 将来 | 差動二輪制御の正確なモデル化 | `ROBOT_WHEEL_BASE = 0.8` | `robot.py` の update ロジック更新 |
| 将来 | スリップ外乱注入 | - | `robot.py: inject_slip()` を活性化 |