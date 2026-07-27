# ARCH_TITLE: ros2_course_lap_trapezoid_ccw_v3

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが**台形コース（反時計回り）**を一周するPythonシミュレーション。  
本バージョンは以下3点が社長・CTO間で最終合意済みの確定版である。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状 | **台形**（上辺L1=15m・斜辺L2=42.43m・下辺L3=45m・左辺L4=30m） |
| 走行方向 | **反時計回り（左回り）** ← 前バージョンの時計回りから変更 |
| カーブ角度配分 | C1=45°・C2=135°・C3=90°・C4=90°（合計360°・閉じ条件成立） |
| カーブ半径 | 全カーブ統一 r = **3.5m**（C案：コース幅内最小半径で統一） |
| ロボット車幅 | `ROBOT_WHEEL_BASE = 0.8m` |
| コース幅 | `COURSE_WIDTH = 7.0m`（中心線から左右3.5mずつ・定義のみ） |
| 将来予定 | 3D表示・路面テクスチャ（黒路面・白線・緑エリア）は次フェーズ |

### 台形コースの幾何学的証明

```
閉じ条件（反時計回り・全旋回角の合計）:
  C1 + C2 + C3 + C4 = 45° + 135° + 90° + 90° = 360° ✅

L2長さの逆算（カーブ半径無視の純粋直線近似）:
  Δx = L3 - L1 = 45.0 - 15.0 = 30.0 m
  Δy = L4 = 30.0 m
  tan(α) = Δx / Δy = 30/30 = 1.0  →  α = 45°（C1角度と一致）
  L2 = √(30² + 30²) ≈ 42.43 m

カーブ半径の影響による誤差:
  r=3.5mのカーブが4箇所あるため実際の閉じ距離に誤差が生じる。
  COURSE_CLOSE_TOLERANCE = 1.0m の範囲内に収まるかテストで確認。
  失敗時はL2を±1.0m範囲で微調整すること。
```

### コース形状の確認図

```
（反時計回り）

         L1 = 15m（上辺）
N01────────────────N03
↑                   ↘ C1（45°左旋回 r=3.5m）
│C4                 N05
│(90°左旋回         │
│r=3.5m)           │L2 = 42.43m（斜辺・右下方向）
N16                 │
↑                   N07
│L4=30m              ↘ C2（135°左旋回 r=3.5m）
N15                  N09
↑C3(90°左旋回        │
│r=3.5m)            │L3 = 45m（下辺）
N13────────────────────────────────N11
```

### 確定コース寸法パラメータ

| 区間 | 種別 | 値 | 角度 | 方向 | 備考 |
|------|------|-----|------|------|------|
| L1 | 直線 | **15.0 m** | - | - | 上辺・スタート/ゴール基準 |
| C1 | 円弧 | r = **3.5 m** | **45°** | **left** | 台形右上コーナー |
| L2 | 直線 | **42.43 m** | - | - | 斜辺（右上→右下） |
| C2 | 円弧 | r = **3.5 m** | **135°** | **left** | 台形右下コーナー（鈍角） |
| L3 | 直線 | **45.0 m** | - | - | 下辺 |
| C3 | 円弧 | r = **3.5 m** | **90°** | **left** | 台形左下コーナー |
| L4 | 直線 | **30.0 m** | - | - | 左辺 |
| C4 | 円弧 | r = **3.5 m** | **90°** | **left** | 台形左上コーナー |

### 確定ノード一覧（変更なし）

| ノードID | 位置 | 種別 |
|---------|------|------|
| N01 | L1入口（＝C4終点・ゴール） | 直線入口 |
| N02 | L1中心（**スタート地点**） | 直線中心 |
| N03 | C1入口（L1終点） | カーブ入口 |
| N04 | C1頂点（45°弧の中間点） | カーブ頂点 |
| N05 | L2入口（C1終点） | 直線入口 |
| N06 | L2中心 | 直線中心 |
| N07 | C2入口（L2終点） | カーブ入口 |
| N08 | C2頂点（135°弧の中間点） | カーブ頂点 |
| N09 | L3入口（C2終点） | 直線入口 |
| N10 | L3中心 | 直線中心 |
| N11 | C3入口（L3終点） | カーブ入口 |
| N12 | C3頂点 | カーブ頂点 |
| N13 | L4入口（C3終点） | 直線入口 |
| N14 | L4中心 | 直線中心 |
| N15 | C4入口（L4終点） | カーブ入口 |
| N16 | C4頂点 | カーブ頂点 |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画 | `matplotlib` + `FuncAnimation` | 現フェーズ確定 |
| 数値計算 | `numpy` | 確定 |
| 自己位置推定 | 順序制約トポロジカル推定 | 確定 |
| ノード数 | 16ノード（N01〜N16） | 確定 |
| 3D表示 | Panda3D/Pygame | **次フェーズ** |
| 路面テクスチャ | 黒路面・白線・緑エリア | **次フェーズ** |

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
    📄 course.py                  # ★変更★ 左旋回ロジック追加・終端処理完全実装
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし（config参照で自動反映）
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # 変更なし
    📄 config.py                  # ★変更★ SEGMENTS全面書き換え
    📁 logs/
      📄 .gitkeep                 # 変更なし
    📁 tests/
      📄 __init__.py              # 変更なし
      📄 test_course.py           # 変更なし（COURSE_CLOSE_TOLERANCE参照済み）
      📄 test_node_manager.py     # 変更なし
```

### 差分サマリー

| 操作 | 対象ファイル | 変更内容 | 影響範囲 |
|------|------------|---------|---------|
| **変更** | `simulation/config.py` | SEGMENTS全面書き換え（左旋回・台形寸法） | 大 |
| **変更** | `simulation/course.py` | `direction=="left"` ブロック追加・終端処理完全実装 | 大 |
| **変更なし** | 上記以外の全ファイル | 既存ロジックへの影響ゼロ | - |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― 変更仕様（完全差分）

**変更ルール**：SEGMENTS ブロックの完全置き換えのみ。他パラメータは前バージョンから引き継ぎ。

#### 変更後の `config.py` 完成イメージ（全体）

```python
import os

# 【コース寸法パラメータ】
# 台形コース・反時計回り（左回り）
# 閉じ条件: C1(45°) + C2(135°) + C3(90°) + C4(90°) = 360° ✅
# L2長さ: √((L3-L1)² + L4²) = √(30²+30²) ≈ 42.43m（カーブ補正前近似値）
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 15.0},
    {"id": "C1", "type": "arc",      "radius": 3.5, "angle_deg":  45, "direction": "left"},
    {"id": "L2", "type": "straight", "length": 42.43},
    {"id": "C2", "type": "arc",      "radius": 3.5, "angle_deg": 135, "direction": "left"},
    {"id": "L3", "type": "straight", "length": 45.0},
    {"id": "C3", "type": "arc",      "radius": 3.5, "angle_deg":  90, "direction": "left"},
    {"id": "L4", "type": "straight", "length": 30.0},
    {"id": "C4", "type": "arc",      "radius": 3.5, "angle_deg":  90, "direction": "left"},
]

# 【ロボットパラメータ】
ROBOT_WHEEL_BASE = 0.8         # 左右輪間距離 [m]（0.3→0.8に更新済み）
ROBOT_SPEED = 0.5              # 走行速度 [m/s]
SIMULATION_DT = 0.05           # 時間刻み [s]（=20Hz相当）

# 【コース幅パラメータ】（定義のみ・3D実装フェーズで使用）
COURSE_WIDTH = 7.0             # コース全幅 [m]（中心線から左右3.5mずつ）

# 【描画パラメータ】（変更なし）
FPS = 30
COURSE_LINE_COLOR = "black"
COURSE_LINE_WIDTH = 2
ROBOT_COLOR = "royalblue"
ROBOT_ARROW_COLOR = "red"
NODE_MARKER_COLOR = "orange"
NODE_FONT_SIZE = 8

# 【ノード認識パラメータ】（変更なし）
NODE_TRIGGER_DISTANCE = 0.5    # ノードとみなす距離閾値 [m]
COURSE_CLOSE_TOLERANCE = 1.0   # コース閉じ判定許容距離 [m]

# 【カメラシミュレータパラメータ】（変更なし）
NOISE_STD = 0.05

# 【ログパラメータ】（変更なし）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILENAME = "run_log.csv"
```

#### L2微調整ルール

```
初期値: 42.43m でテスト実行
test_course_is_closed() が FAILED の場合:
  閉じ距離の方向を確認し以下の規則で微調整する

  終点が始点より「右にずれている」→ L2を短くする（-0.1m刻み）
  終点が始点より「左にずれている」→ L2を長くする（+0.1m刻み）
  終点が始点より「上にずれている」→ L4を短くする（±0.1m刻み）
  終点が始点より「下にずれている」→ L4を長くする（±0.1m刻み）

許容範囲: distance < COURSE_CLOSE_TOLERANCE(1.0m) に収めること
```

---

### 3-2. `course.py` ― 左旋回ロジック追加・終端処理完全実装

**変更ルール**：既存の `direction == "right"` ブロックは変更しない。`elif direction == "left":` ブロックを追加する。さらに両方向の終端処理（現コードで `# 終端` コメントで途切れている箇所）を完全実装する。

#### 変更箇所の詳細仕様

**【変更点①】右旋回の終端処理を完全実装**

現在 `# 終端` コメントで実装が途切れている。以下を追加する。

```
右旋回の終端座標とthetaの更新:
  終端角度 = start_angle - angle_rad
  終端x    = cx + radius × cos(終端角度)
  終端y    = cy + radius × sin(終端角度)
  x = 終端x
  y = 終端y
  theta = theta - angle_rad   ← 右旋回はthetaが減少
```

**【変更点②】左旋回ブロックを新規追加**

右旋回ブロックの `if direction == "right":` に続けて `elif direction == "left":` を追加する。

```
左旋回の処理ロジック（右旋回との対称関係）:

  旋回中心の計算:
    cx = x + radius × cos(theta + π/2)   ← 右旋回は(theta - π/2)
    cy = y + radius × sin(theta + π/2)   ← 符号が逆

  初期角度の計算:
    start_angle = arctan2(y - cy, x - cx)   ← 同じ

  点列の生成（加算方向・反時計回り）:
    for step_i in range(num_steps):
      cur_a = start_angle + step_i × d_alpha   ← 右旋回は「-」・左旋回は「+」
      px = cx + radius × cos(cur_a)
      py = cy + radius × sin(cur_a)
      points.append([px, py])

  終端座標とthetaの更新:
    終端角度 = start_angle + angle_rad   ← 右旋回は「-」・左旋回は「+」
    x = cx + radius × cos(終端角度)
    y = cy + radius × sin(終端角度)
    theta = theta + angle_rad            ← 右旋回は「-=」・左旋回は「+=」
```

#### `course.py` の `generate_course_points()` 完成後の構造イメージ

```
def generate_course_points(self):
    x, y = 0.0, 0.0
    theta = 0.0
    points = []

    for seg in self.segments:
        seg_type = seg["type"]

        if seg_type == "straight":
            【既存実装・変更なし】
            ※ ただし終端後の x, y が正しく更新されていることを確認

        elif seg_type == "arc":
            radius = seg["radius"]
            angle_deg = seg["angle_deg"]
            angle_rad = np.radians(angle_deg)
            direction = seg.get("direction", "right")

            arc_length = radius * angle_rad
            num_steps = int(np.ceil(arc_length / STEP_SIZE))
            d_alpha = angle_rad / num_steps if num_steps > 0 else 0

            if direction == "right":
                【既存実装 + 終端処理を追加】
                終端: x, y, theta を更新（theta -= angle_rad）

            elif direction == "left":
                【新規追加】
                旋回中心: theta + π/2 方向
                点列生成: cur_a = start_angle + step_i × d_alpha
                終端: x, y, theta を更新（theta += angle_rad）

    return np.array(points)
```

#### `generate_node_positions()` への影響確認

ノード位置はコース点列のインデックスから抽出するため、直線・円弧の生成ロジックが正しければ変更不要。ただし以下を確認すること。

```
N04（C1頂点）: C1は45°なので弧の中間点 = step_num/2 番目の点
N08（C2頂点）: C2は135°なので弧の中間点 = step_num/2 番目の点
  ※ 頂点の定義が「弧の中間点」で実装されているかを確認
  ※ C2は135°と角度が大きいため、頂点が視覚的に鈍角コーナーの外側に来ることに注意
```

#### `get_segment_curvature()` への影響

全カーブがr=3.5mで統一されたため、C1〜C4の曲率値がすべて同一になる。

```
curvature("L1") = 0.0
curvature("C1") = 1.0 / 3.5 ≈ 0.286
curvature("L2") = 0.0
curvature("C2") = 1.0 / 3.5 ≈ 0.286  ← C1と同値
curvature("L3") = 0.0
curvature("C3") = 1.0 / 3.5 ≈ 0.286  ← C1と同値
curvature("L4") = 0.0
curvature("C4") = 1.0 / 3.5 ≈ 0.286  ← C1と同値
```

**将来の区間識別への影響**：現フェーズではcamera_simulatorの出力はログ用途のみのため、全カーブが同一曲率でも機能上の問題なし。次フェーズで区間識別ロジックを実装する際に `angle_deg` も特徴量に加える設計変更が必要になる（将来拡張ポイントに記載）。

---

### 3-3. 変更なし確認済みファイル

以下のファイルは **コードの1行も変更しない**。実装担当者は触らないこと。

| ファイル | 変更不要の理由 |
|---------|-------------|
| `robot.py` | コース点列をなぞるだけ。方向・寸法変更を自動吸収 |
| `node_manager.py` | `NODE_TRIGGER_DISTANCE` は config 参照で自動反映。`direction` には非依存 |
| `camera_simulator.py` | 区間IDから曲率を取得するだけ。変更不要 |
| `visualizer.py` | コース点列を描画するだけ。形状変更を自動吸収。`set_aspect('equal')` で台形も正確に表示される |
| `main.py` | `total_frames = len(course_points) - 1` で自動追従 |
| `tests/test_course.py` | `COURSE_CLOSE_TOLERANCE` 参照済み。変更不要 |
| `tests/test_node_manager.py` | ノード座標は `CourseGenerator` から動的取得。変更不要 |

---

## 4. データ・制御の処理フロー

### 4-1. 今回の変更がシステム全体に波及する経路

```
config.py（変更）
  │
  ├─ SEGMENTS（direction="left"・台形寸法）
  │    └──► course.py: generate_course_points()
  │              │  新規: direction=="left" ブロックが実行される
  │              │  出力: course_points の総点数
  │              │    L1: 15.0/0.02 = 750点
  │              │    C1: (3.5×π/4)/0.02 ≈ 275点
  │              │    L2: 42.43/0.02 ≈ 2122点
  │              │    C2: (3.5×3π/4)/0.02 ≈ 824点
  │              │    L3: 45.0/0.02 = 2250点
  │              │    C3: (3.5×π/2)/0.02 ≈ 550点
  │              │    L4: 30.0/0.02 = 1500点
  │              │    C4: (3.5×π/2)/0.02 ≈ 550点
  │              │    合計: 約 8,821点（≒8,820フレーム）
  │              │
  │              ├──► visualizer.py: コース形状が台形として描画される
  │              └──► main.py: total_frames ≈ 8,820
  │
  ├─ NODE_TRIGGER_DISTANCE = 0.5（変更なし・前バージョンから引き継ぎ）
  │    └──► node_manager.py: update() の dist 判定閾値（自動反映済み）
  │
  ├─ COURSE_CLOSE_TOLERANCE = 1.0（変更なし・前バージョンから引き継ぎ）
  │    └──► tests/test_course.py: test_course_is_closed() で参照
  │
  ├─ ROBOT_WHEEL_BASE = 0.8（変更なし・前バージョンから引き継ぎ）
  │    └──► 現フェーズでは参照箇所なし（影響ゼロ）
  │
  └─ COURSE_WIDTH = 7.0（変更なし・前バージョンから引き継ぎ）
       └──► 現フェーズでは参照箇所なし（影響ゼロ）
```

### 4-2. 左旋回処理の内部フロー（course.py 新規追加部分の詳細）

```
arc セグメント処理（direction == "left" の場合）

入力状態: 現在位置(x, y)、進行方向 theta [rad]

Step1: 旋回中心を計算
  旋回中心は進行方向の「左90°」方向にradiusだけ離れた点
  cx = x + radius × cos(theta + π/2)
  cy = y + radius × sin(theta + π/2)
  ※ theta + π/2 は進行方向を反時計回りに90°回転した方向

Step2: 初期角度を計算
  start_angle = arctan2(y - cy, x - cx)
  ※ 旋回中心から現在位置への角度

Step3: 点列を生成（反時計回り = 角度を増やす方向）
  d_alpha = angle_rad / num_steps
  for step_i in 0..num_steps-1:
    cur_a = start_angle + step_i × d_alpha  ← 「+」が左旋回の核心
    px = cx + radius × cos(cur_a)
    py = cy + radius × sin(cur_a)
    points.append([px, py])

Step4: 終端座標とthetaを更新
  end_angle = start_angle + angle_rad       ← 「+」が左旋回の核心
  x = cx + radius × cos(end_angle)
  y = cy + radius × sin(end_angle)
  theta = theta + angle_rad                 ← 「+=」が左旋回の核心

出力状態: 更新された(x, y, theta)で次のセグメント処理へ
```

### 4-3. 毎フレームの更新フロー（変更なし・参考）

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
  │  反時計回りのためN01→N02→...→N16→N01と遷移
  ▼
node_manager.get_current_segment_id()
  │  現在ノードIDから区間ID（L1〜C4）を返す（mapping変更なし）
  ▼
camera_sim.get_features(segment_id, cg)
  │  全カーブがr=3.5mで統一のため曲率値は一定（0.286）
  │  現フェーズはログ用途のみ
  ▼
visualizer.update_frame(frame_index, robot, node_manager)
  │  Layer4: ロボット位置点を更新
  │  Layer5: 向き矢印を更新（反時計回りなので矢印方向に注意）
  │  Layer6: タイトル文字列を更新
  │  "Frame:xxx | Node:N05 | Segment:L2 | Dist:xxx.xxm"
  ▼
ラップ完了チェック → export_log() → "LAP COMPLETED"
  ▼
matplotlib が描画を更新 → 次フレームへ
```

### 4-4. 実装後の動作確認手順（実装担当者への指示）

```
【実行順序を厳守すること】

Step1: コース閉じテスト
  cd src
  python -m pytest simulation/tests/test_course.py -v

  期待結果:
  ✅ test_course_is_closed → PASSED（distance < 1.0m）
  ✅ test_node_count       → PASSED（16ノード）

  ❌ FAILEDの場合の対処:
    エラーメッセージの「始点: [...], 終点: [...]」を確認
    終点のX座標が始点より大きい → L2を -0.1m ずつ減らす
    終点のX座標が始点より小さい → L2を +0.1m ずつ増やす
    config.py の L2.length を調整して再テスト

Step2: ノード遷移テスト
  python -m pytest simulation/tests/test_node_manager.py -v

  期待結果:
  ✅ test_sequential_transition → PASSED
  ✅ test_no_skip_transition    → PASSED
  ✅ test_lap_completion        → PASSED

Step3: シミュレーション起動
  python -m simulation.main

  目視確認チェックリスト:
  ✅ コース形状が「台形」に見える
     （左辺L4が短く、上辺L1が短い・下辺L3が長い・斜辺L2が右から下へ）
  ✅ ロボットが「反時計回り」に走行している
     （N01→N02→N03→...の順で左回り）
  ✅ L2区間でロボットが斜め方向に走行している
  ✅ C2コーナーで135°の鈍角カーブを描いている
  ✅ C3・C4で直角（90°）に曲がっている
  ✅ N02スタートからN01再到達でラップ完了
  ✅ "LAP COMPLETED" がコンソールに出力される
  ✅ logs/run_log.csv が生成される
```

### 4-5. 将来拡張ポイント（次フェーズへの申し送り）

| フェーズ | 拡張項目 | 使用するパラメータ/ファイル | 注意事項 |
|---------|---------|------------------------|---------|
| **次フェーズ（3D化）** | 路面ポリゴン（黒路面・白線） | `COURSE_WIDTH = 7.0` / `visualizer.py` | コース中心線から法線方向±3.5mにポリゴン生成するロジックが必要 |
| **次フェーズ（3D化）** | コース外緑エリア描画 | `COURSE_WIDTH` / `visualizer.py` | 外側をfill描画・`matplotlib.patches.Polygon` 使用 |
| **次フェーズ（3D化）** | ロボット一人称カメラ視点 | - | `visualizer.py` をPanda3D等に置換。`robot.theta` から視点行列を生成 |
| **将来** | 区間識別精度向上 | `camera_simulator.py` | 全カーブが曲率同値になったため `angle_deg` も特徴量に追加する必要あり |
| **将来** | 差動二輪制御の正確なモデル化 | `ROBOT_WHEEL_BASE = 0.8` / `robot.py` | `inject_slip()` の活性化と連動 |
| **将来** | スリップ外乱注入 | `robot.py: inject_slip()` | カメラ主体推定の優位性を検証する実験に使用 |
| **将来** | ROS2ノード化 | `raphael_enterprise/course_lap_node.py` | シミュレーション検証後に既存ROS2パッケージへ移植 |