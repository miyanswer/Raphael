# ARCH_TITLE: ros2_course_lap_2d_road_texture_v4

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが台形コース（反時計回り）を一周するPythonシミュレーション。  
本バージョンは**2D路面テクスチャ実装**が追加された版である。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状 | 台形（上辺L1=15m・斜辺L2=42.43m・下辺L3=45m・左辺L4=30m） |
| 走行方向 | 反時計回り（左回り） |
| カーブ | 全カーブ r=3.5m・C1=45°・C2=135°・C3=90°・C4=90° |
| 路面テクスチャ | **黒路面（各側3.5m）・白線3本・緑背景** ← 今バージョン追加 |
| 描画方式 | matplotlib 2D・`blit=False` に変更 |
| 3D化 | 次フェーズ（Panda3D） |

### 路面断面レイアウト（確定）

```
← 3.5m →   ← 3.5m →
外側白線   中心白線   内側白線
   |           |           |
緑 ｜  黒路面  ｜  黒路面  ｜ 緑
   |           |           |
全幅 = COURSE_WIDTH = 7.0m
```

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画 | `matplotlib` + `FuncAnimation`・`matplotlib.patches.Polygon` | 確定 |
| 数値計算 | `numpy` | 確定 |
| 自己位置推定 | 順序制約トポロジカル推定 | 確定 |
| ノード数 | 16ノード（N01〜N16） | 確定 |
| 3D化 | Panda3D | **次フェーズ** |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # ★変更★ generate_boundary_points()呼び出し追加・Visualizer引数追加
    📄 course.py                  # ★変更★ generate_boundary_points()新規追加・左旋回ロジック追加・終端処理完全実装
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # ★変更★ 路面テクスチャ描画レイヤー全面変更・引数追加・blit=False
    📄 config.py                  # ★変更★ 路面色定数追加
    📁 logs/
      📄 .gitkeep                 # 変更なし
    📁 tests/
      📄 __init__.py              # 変更なし
      📄 test_course.py           # 変更なし
      📄 test_node_manager.py     # 変更なし
```

### 差分サマリー

| 操作 | 対象ファイル | 変更内容 | 変更規模 |
|------|------------|---------|---------|
| **変更** | `simulation/config.py` | 路面・白線・緑の色定数5個追加 | 小 |
| **変更** | `simulation/course.py` | `generate_boundary_points()` 新規追加・左旋回ブロック追加・終端処理完全実装 | 大 |
| **変更** | `simulation/visualizer.py` | 描画レイヤー全面変更・引数追加・`blit=False` | 大 |
| **変更** | `simulation/main.py` | `generate_boundary_points()` 呼び出し追加・`Visualizer` 引数2個追加 | 小 |
| **変更なし** | その他全ファイル | 影響ゼロ | - |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― 追加定数（差分のみ）

**既存パラメータは一切変更しない。以下を【描画パラメータ】ブロックの末尾に追記する。**

```
【追記箇所: 【描画パラメータ】ブロック末尾】

# 路面テクスチャ色定数（今バージョン追加）
ROAD_COLOR         = "black"      # 黒路面の塗り色
ROAD_LINE_COLOR    = "white"      # 白線3本の色（外側・中心・内側）
ROAD_LINE_WIDTH    = 2            # 白線の線幅 [pt]
CENTER_LINE_STYLE  = "--"         # 中心白線は破線
GRASS_COLOR        = "green"      # コース外の芝（背景色）
```

**変更後の【描画パラメータ】ブロック全体イメージ：**

```python
# 【描画パラメータ】
FPS = 30
COURSE_LINE_COLOR  = "black"      # ← 既存（現フェーズでは未使用になる）
COURSE_LINE_WIDTH  = 2            # ← 既存（現フェーズでは未使用になる）
ROBOT_COLOR        = "royalblue"
ROBOT_ARROW_COLOR  = "red"
NODE_MARKER_COLOR  = "orange"
NODE_FONT_SIZE     = 8

# 路面テクスチャ色定数（今バージョン追加）
ROAD_COLOR         = "black"
ROAD_LINE_COLOR    = "white"
ROAD_LINE_WIDTH    = 2
CENTER_LINE_STYLE  = "--"
GRASS_COLOR        = "green"
```

> `COURSE_LINE_COLOR` / `COURSE_LINE_WIDTH` は削除しない。将来のデバッグ用途として残す。

---

### 3-2. `course.py` ― 3種類の変更を一括実装

**既存の `generate_course_points()` の骨格は変更しない。以下3点を実装する。**

---

#### 変更点①：右旋回の終端処理を完全実装

現在 `# 終端` コメントで途切れている箇所に以下を追加する。

```
【右旋回終端処理の追加仕様】

arc セグメントの direction == "right" ブロック内・点列生成ループの直後に追記:

  end_angle = start_angle - angle_rad
  x = cx + radius * cos(end_angle)
  y = cy + radius * sin(end_angle)
  theta = theta - angle_rad

意味:
  end_angle: 旋回終了後の「旋回中心→終点」の角度
  x, y: 次セグメントの開始座標（終端座標）
  theta: 次セグメントの開始進行方向（右旋回なのでthetaが減少）
```

---

#### 変更点②：左旋回ブロックを新規追加

`elif seg_type == "arc":` ブロック内の `if direction == "right":` の直後に追加する。

```
【左旋回処理ロジック（direction == "left" の場合）】

右旋回との対称関係（符号が逆になる箇所）:

  旋回中心の計算:
    cx = x + radius × cos(theta + π/2)   ← 右: (theta - π/2)
    cy = y + radius × sin(theta + π/2)   ← 右: (theta - π/2)

  初期角度の計算:
    start_angle = arctan2(y - cy, x - cx)   ← 右旋回と同じ

  点列の生成（反時計回り = 角度を増やす方向）:
    d_alpha = angle_rad / num_steps
    for step_i in range(num_steps):
      cur_a = start_angle + step_i × d_alpha   ← 右: 「-」 左: 「+」
      px = cx + radius × cos(cur_a)
      py = cy + radius × sin(cur_a)
      points.append([px, py])

  終端座標とthetaの更新:
    end_angle = start_angle + angle_rad          ← 右: 「-」 左: 「+」
    x = cx + radius × cos(end_angle)
    y = cy + radius × sin(end_angle)
    theta = theta + angle_rad                    ← 右: 「-=」 左: 「+=」
```

**変更後の `generate_course_points()` arc 処理ブロック全体構造：**

```
elif seg_type == "arc":
    radius    = seg["radius"]
    angle_deg = seg["angle_deg"]
    angle_rad = np.radians(angle_deg)
    direction = seg.get("direction", "right")

    arc_length = radius * angle_rad
    num_steps  = int(np.ceil(arc_length / STEP_SIZE))
    d_alpha    = angle_rad / num_steps if num_steps > 0 else 0

    if direction == "right":
        cx          = x + radius × cos(theta - π/2)
        cy          = y + radius × sin(theta - π/2)
        start_angle = arctan2(y - cy, x - cx)
        
        for step_i in range(num_steps):
            cur_a = start_angle - step_i × d_alpha   ← 時計回り
            points.append([cx + r×cos(cur_a), cy + r×sin(cur_a)])
        
        end_angle = start_angle - angle_rad
        x = cx + radius × cos(end_angle)
        y = cy + radius × sin(end_angle)
        theta -= angle_rad                           ← 終端処理①

    elif direction == "left":
        cx          = x + radius × cos(theta + π/2)  ← 符号逆
        cy          = y + radius × sin(theta + π/2)
        start_angle = arctan2(y - cy, x - cx)
        
        for step_i in range(num_steps):
            cur_a = start_angle + step_i × d_alpha   ← 反時計回り
            points.append([cx + r×cos(cur_a), cy + r×sin(cur_a)])
        
        end_angle = start_angle + angle_rad          ← 符号逆
        x = cx + radius × cos(end_angle)
        y = cy + radius × sin(end_angle)
        theta += angle_rad                           ← 符号逆
```

---

#### 変更点③：`generate_boundary_points()` 新規追加

`CourseGenerator` クラスに新規メソッドとして追加する。

```
【新規メソッド: generate_boundary_points(course_points)】

引数: course_points: numpy配列 shape=(N, 2)
      （generate_course_points()の戻り値をそのまま渡す）

処理:
  Step1: 各点の進行方向ベクトルを計算（中央差分法）
    N = len(course_points)
    tangents = np.zeros((N, 2))
    
    先頭点 (i=0):
      tangents[0] = course_points[1] - course_points[0]
    末尾点 (i=N-1):
      tangents[N-1] = course_points[N-1] - course_points[N-2]
    中間点 (i=1..N-2):
      tangents[i] = course_points[i+1] - course_points[i-1]
    
    ※ np.diff() でまとめて計算することも可だが、
       端点処理のために明示的に3分岐すること

  Step2: 単位法線ベクトルを計算（進行方向を+90°回転）
    各tangent (dx, dy) に対して:
      norm = sqrt(dx² + dy²)
      if norm < 1e-9: norm = 1.0  ← ゼロ除算防止
      normal_x = -dy / norm
      normal_y =  dx / norm
    
    normals = shape (N, 2) の配列

  Step3: 境界線座標を生成
    half = config.COURSE_WIDTH / 2  →  3.5 [m]
    
    left_boundary[i]  = course_points[i] + half × normals[i]
    right_boundary[i] = course_points[i] - half × normals[i]

戻り値:
  left_boundary  : numpy配列 shape=(N, 2)  ← 外側境界（左）
  right_boundary : numpy配列 shape=(N, 2)  ← 内側境界（右）
```

**実装上の注意：**
```
・left/right の呼称は「反時計回りの進行方向に対して左右」
  → 外側（台形の外）が left_boundary
  → 内側（台形の内）が right_boundary
・カーブ区間で法線が急変する箇所はあるが、STEP_SIZE=0.02mの
  密な点列で中央差分を取るため実用上問題なし
・generate_boundary_points() は generate_course_points() の
  戻り値（numpy配列）を引数に取る設計。内部で再生成しないこと
```

---

### 3-3. `visualizer.py` ― 路面テクスチャ描画レイヤー全面変更

#### `__init__()` のシグネチャ変更

```
変更前:
  def __init__(self, course_points, node_positions):

変更後:
  def __init__(self, course_points, node_positions, left_boundary, right_boundary):
```

#### `__init__()` 内の描画処理全面書き換え

```
【変更前の削除対象】
  ax.grid(True, linestyle='--', alpha=0.5)          ← 削除
  ax.plot(course_points, color="black", ...)         ← 削除

【変更後の描画レイヤー構成（コード順序 = 描画順序）】

Layer 0: 緑背景
  ax.set_facecolor(config.GRASS_COLOR)
  ※ figの背景も合わせる:
    fig.patch.set_facecolor(config.GRASS_COLOR)

Layer 1: 黒路面ポリゴン
  road_polygon_vertices の生成:
    left_boundary の点列（順方向）
    + right_boundary の点列（逆方向）
    を np.concatenate() で連結 → shape=(2N, 2)
  
  from matplotlib.patches import Polygon
  road_patch = Polygon(
      road_polygon_vertices,
      closed=True,
      color=config.ROAD_COLOR,
      zorder=1
  )
  ax.add_patch(road_patch)

Layer 2: 外側白線
  ax.plot(
      left_boundary[:, 0], left_boundary[:, 1],
      color=config.ROAD_LINE_COLOR,
      linewidth=config.ROAD_LINE_WIDTH,
      zorder=2
  )

Layer 3: 内側白線
  ax.plot(
      right_boundary[:, 0], right_boundary[:, 1],
      color=config.ROAD_LINE_COLOR,
      linewidth=config.ROAD_LINE_WIDTH,
      zorder=3
  )

Layer 4: 中心白線（破線）
  ax.plot(
      course_points[:, 0], course_points[:, 1],
      color=config.ROAD_LINE_COLOR,
      linewidth=config.ROAD_LINE_WIDTH,
      linestyle=config.CENTER_LINE_STYLE,
      zorder=4
  )

Layer 5: ノードマーカー
  ax.scatter(..., zorder=5)  ← zorderを5に変更（既存コードの4から）

Layer 6: ノードIDラベル
  ax.text(..., zorder=6)     ← zorderを6に変更（既存コードの5から）

Layer 7: ロボット位置点（動的）
  self.robot_point, = ax.plot(..., zorder=7)   ← zorderを7に変更

Layer 8: ロボット向き矢印（動的）
  self.quiver = ax.quiver(..., zorder=8)       ← zorderを8に変更

【ax の追加設定】
  ax.grid(False)          ← 黒路面上でグリッドが見えないため無効化
  ax.set_aspect('equal')  ← 変更なし
```

#### `run_animation()` の `blit` 変更

```
変更前:
  FuncAnimation(..., blit=True)

変更後:
  FuncAnimation(..., blit=False)

理由:
  matplotlib.patches.Polygon は blit=True の描画更新サイクルに
  対応していない静的オブジェクト。
  blit=False にすることで毎フレーム全画面再描画となるが、
  路面ポリゴンは静的レイヤーのため問題なし。
  速度が問題になる場合は config.FPS を 30 → 15 に下げること。
```

#### `update_frame()` の戻り値変更

```
変更前:
  return self.robot_point, self.quiver

変更後:
  return []

理由: blit=False の場合、戻り値は使用されない。
     空リストを返すことで将来の blit=True 復帰時の誤動作を防ぐ。
```

---

### 3-4. `main.py` ― 差分のみ

```
【変更箇所: Step2とStep3の間に1行追加・Step3のVisualizerを1行変更】

# Step2（既存・変更なし）
cg = CourseGenerator(config.SEGMENTS)
course_points = cg.generate_course_points()
node_positions = cg.generate_node_positions()

# ★ 追加: 境界線点列の生成
left_boundary, right_boundary = cg.generate_boundary_points(course_points)

# Step3（Visualizer引数のみ変更）
start_pos = node_positions["N02"]
robot = DifferentialDriveRobot(start_pos[0], start_pos[1], start_theta=0.0)
node_manager = NodeManager(node_positions)
camera_sim = CameraSimulator(seed=42)

# ★ 変更: 引数に left_boundary, right_boundary を追加
visualizer = Visualizer(course_points, node_positions, left_boundary, right_boundary)

# Step4以降は変更なし
```

---

### 3-5. 変更なし確認済みファイル

| ファイル | 変更不要の理由 |
|---------|-------------|
| `robot.py` | コース点列をなぞるだけ |
| `node_manager.py` | config参照で自動反映済み |
| `camera_simulator.py` | 区間IDと曲率のみ参照 |
| `tests/test_course.py` | `COURSE_CLOSE_TOLERANCE` 参照済み |
| `tests/test_node_manager.py` | ノード座標はCourseGeneratorから動的取得 |

---

## 4. データ・制御の処理フロー

### 4-1. 初期化フロー（変更箇所を★で明示）

```
main.py 起動
  │
  ▼
config.py
  │ SEGMENTS / COURSE_WIDTH / ROAD_COLOR / ROAD_LINE_COLOR /
  │ GRASS_COLOR / CENTER_LINE_STYLE / ROAD_LINE_WIDTH（★追加）
  ▼
course.py
  generate_course_points()
    ├─ direction=="right" → 既存ロジック + ★終端処理追加
    ├─ direction=="left"  → ★新規ブロック（左旋回・反時計回り）
    └─ 全点列を連結 → course_points[N≈8820, 2]
  
  generate_node_positions()
    └─ 16ノード座標を抽出 → node_positions dict
  
  ★ generate_boundary_points(course_points)  ← 新規追加
    ├─ 中央差分で各点の法線を計算
    ├─ left_boundary  = 中心 + 3.5m × 法線
    └─ right_boundary = 中心 - 3.5m × 法線
  │
  ▼
robot.py
  DifferentialDriveRobot(N02座標, theta=0.0)
  │
  ▼
node_manager.py
  NodeManager(node_positions), current_node_index=1(N02)
  │
  ▼
camera_simulator.py
  CameraSimulator(seed=42)
  │
  ▼
★ visualizer.py（全面変更）
  Visualizer(course_points, node_positions, left_boundary, right_boundary)
  │
  ├─ Layer0: ax.set_facecolor("green")         ← 緑背景
  ├─ Layer1: Polygon(road_polygon, "black")     ← 黒路面
  ├─ Layer2: plot(left_boundary, "white")       ← 外側白線
  ├─ Layer3: plot(right_boundary, "white")      ← 内側白線
  ├─ Layer4: plot(course_points, "white", "--") ← 中心白線（破線）
  ├─ Layer5: scatter(ノード, "orange")          ← ノードマーカー
  ├─ Layer6: text(ノードID)                     ← ラベル
  ├─ Layer7: plot([], [], ロボット点)            ← 動的
  └─ Layer8: quiver([], [], [], [], 矢印)       ← 動的
  │
  ▼
FuncAnimation 起動（★blit=False）
```

### 4-2. 境界線生成の内部フロー（新規追加部分の詳細）

```
generate_boundary_points(course_points) の処理

入力: course_points[N, 2]

Step1: 接線ベクトル計算（中央差分）
  tangents = zeros(N, 2)
  
  i=0:     tangents[0]   = cp[1]   - cp[0]
  i=N-1:   tangents[N-1] = cp[N-1] - cp[N-2]
  i=1..N-2: tangents[i]  = cp[i+1] - cp[i-1]

Step2: 法線ベクトル計算（+90°回転・単位化）
  for each tangent (dx, dy):
    norm = sqrt(dx² + dy²)
    if norm < 1e-9: norm = 1.0   ← ゼロ除算ガード
    normal = (-dy/norm, dx/norm)
  
  normals[N, 2]

Step3: 境界線座標
  half = COURSE_WIDTH / 2  = 3.5
  
  left_boundary[i]  = (cp[i,0] + half*normal[i,0],
                        cp[i,1] + half*normal[i,1])
  right_boundary[i] = (cp[i,0] - half*normal[i,0],
                        cp[i,1] - half*normal[i,1])

Step4: 黒路面ポリゴン頂点の構築（visualizer.pyで実行）
  road_polygon = np.concatenate([
      left_boundary,              # N点（順方向）
      right_boundary[::-1]        # N点（逆順）
  ])
  → 閉じたポリゴン shape=(2N, 2)
  → matplotlib.patches.Polygon に渡す

出力:
  left_boundary[N, 2]
  right_boundary[N, 2]
```

### 4-3. 毎フレームの更新フロー

```
FuncAnimation が frame_index を increment → update_frame() 呼び出し
  │
  ▼ （変更なし）
robot.update_along_course(course_points, frame_index)
  │  x, y, theta, odom を更新
  ▼ （変更なし）
node_manager.update(robot.x, robot.y)
  │  次ノード候補との距離 < 0.5m → 遷移確定
  ▼ （変更なし）
node_manager.get_current_segment_id()
  ▼ （変更なし）
camera_sim.get_features(segment_id, cg)
  │  ログ用途のみ（現フェーズ）
  ▼ （★変更あり）
visualizer.update_frame(frame_index, robot, node_manager)
  │  Layer7: ロボット位置点を更新
  │  Layer8: 向き矢印を更新
  │  タイトル: "Frame:xxx | Node:N05 | Segment:L2 | Dist:xxx.xxm"
  │  return []  ← blit=False のため空リスト
  ▼ （変更なし）
ラップ完了チェック → export_log() → "LAP COMPLETED"
  ▼
matplotlib が全画面再描画（blit=False）→ 次フレームへ
```

### 4-4. データ依存関係図

```
config.py
  ├──► SEGMENTS ──────────────────────────────────────┐
  ├──► COURSE_WIDTH (7.0m) ────────────────────────── │ ──► generate_boundary_points()
  ├──► ROAD_COLOR / ROAD_LINE_COLOR / GRASS_COLOR ─── │ ──► visualizer.py __init__()
  │                                                    │
  ▼                                                    │
course.py                                              │
  generate_course_points() ──────────────────────────── ┤
    ├──► course_points[N,2] ──────────────────────────► visualizer.py（Layer4中心白線）
    │                                                   main.py（total_frames）
    │                                                   robot.py（update_along_course）
    └──► generate_boundary_points(course_points)
              ├──► left_boundary[N,2]  ───────────────► visualizer.py（Layer1,2）
              └──► right_boundary[N,2] ───────────────► visualizer.py（Layer1,3）
  
  generate_node_positions() ──────────────────────────► node_manager.py
                                                        visualizer.py（Layer5,6）
                                                        main.py（start_pos=N02）
```

### 4-5. 実装後の動作確認手順（実装担当者への指示）

```
【実行順序を厳守すること】

Step1: テスト実行
  cd src
  python -m pytest simulation/tests/test_course.py -v
  
  確認項目:
  ✅ test_course_is_closed → PASSED（distance < 1.0m）
  ✅ test_node_count       → PASSED（16ノード）
  
  ❌ test_course_is_closed FAILED の場合:
    エラーメッセージの「始点: [...], 終点: [...]」を確認
    終点のX座標が始点より大きい → config.py の L2.length を -0.1m 刻みで減らす
    終点のX座標が始点より小さい → config.py の L2.length を +0.1m 刻みで増やす
    調整後に再テスト

Step2: テスト実行
  python -m pytest simulation/tests/test_node_manager.py -v
  
  確認項目:
  ✅ test_sequential_transition → PASSED
  ✅ test_no_skip_transition    → PASSED
  ✅ test_lap_completion        → PASSED

Step3: シミュレーション起動
  python -m simulation.main

  目視確認チェックリスト:
  ✅ 背景全体が緑色になっている
  ✅ コース形状が台形に黒く塗られている
  ✅ 外側・内側に白の実線が描かれている（各3.5m位置）
  ✅ 中央に白の破線が描かれている
  ✅ 白線の間隔が均等（カーブでも崩れていない）
  ✅ ノードマーカー（orange）が黒路面上に見えている
  ✅ ロボット（royalblue）が反時計回りに走行している
  ✅ L2区間でロボットが斜め方向に走行している
  ✅ "LAP COMPLETED" がコンソールに出力される
  ✅ logs/run_log.csv が生成される

【速度が遅い場合の対処】
  config.py の FPS を 30 → 15 に変更して再起動
```

### 4-6. 将来拡張ポイント（次フェーズへの申し送り）

| フェーズ | 拡張項目 | 使用するパラメータ/ファイル | 注意事項 |
|---------|---------|------------------------|---------|
| **次フェーズ（3D化）** | Panda3D への移行 | `visualizer.py` 全面置換 | `left_boundary` / `right_boundary` のデータ構造はそのまま流用可能 |
| **次フェーズ（3D化）** | ロボット一人称カメラ視点 | `robot.theta` から視点行列生成 | Panda3D の `setHpr()` に `theta` を変換して渡す |
| **次フェーズ（3D化）** | 路面に高さ(Z=0)を追加 | `course_points` に Z列を追加 | `np.hstack([course_points, np.zeros((N,1))])` |
| **将来** | 白線を破線パターンに（外側・内側も） | `config.py` の `ROAD_LINE_STYLE` 追加 | 現状は外側・内側は実線、中心のみ破線 |
| **将来** | blit=True 復帰 | `visualizer.py` | 路面Polygonを初期化後に固定レイヤーとして保持する設計変更が必要 |
| **将来** | 区間識別精度向上 | `camera_simulator.py` | 全カーブが曲率同値(0.286)のため `angle_deg` も特徴量に追加する |
| **将来** | スリップ外乱注入 | `robot.py: inject_slip()` | カメラ主体推定の優位性を検証する実験に使用 |
| **将来** | ROS2ノード化 | `raphael_enterprise/course_lap_node.py` | シミュレーション検証後に移植 |