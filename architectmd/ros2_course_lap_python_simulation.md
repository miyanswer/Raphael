# ARCH_TITLE: ros2_course_lap_python_simulation

## 1. システム概要と決定された採用技術

### システム概要
差動二輪ロボット（後部オムニホイール従属輪付き）が、直線4区間（L1〜L4）とカーブ4区間（C1〜C4）から成るループコースを一周するPythonシミュレーションシステム。カメラ・IMU・ODOMのみを使った**計算リソース低負荷な自己位置推定**の概念実証（PoC）フェーズ。Unityとの連携は後回しとし、まずPython単体で動作検証を完結させる。

### 決定された採用技術

| 項目 | 採用技術 | 決定根拠 |
|------|---------|---------|
| 言語 | Python 3.10以上 | 既存ROS2パッケージと同一言語 |
| コース描画・アニメーション | `matplotlib` + `matplotlib.animation.FuncAnimation` | 追加依存なし・軽量 |
| 数値計算・座標生成 | `numpy` | 標準的・高速 |
| 自己位置推定方式 | **順序制約トポロジカル推定**（カメラ主軸・IMU/ODOMは補助） | スリップ耐性・低計算コスト |
| 仮想カメラ特徴量 | ライン曲率・左右非対称性の数値シミュレート | Unityなしで概念実証可能 |
| ノード構成 | 16ノード（各区間に入口・中心を定義） | 社長・CTO合意済み |
| コース寸法 | 下記パラメータテーブル参照 | CTO提案・社長承認済み |

### 確定コース寸法パラメータ

| 区間 | 長さ / 曲率半径 | 旋回角度 | 特性 |
|------|--------------|---------|------|
| L1 | 5.0 m | - | スタート/ゴール基準直線 |
| C1 | r = 2.0 m | 45° 右旋回 | 緩やかカーブ |
| L2 | 3.0 m | - | 直線 |
| C2 | r = 0.8 m | 45° 右旋回 | 急カーブ |
| L3 | 4.0 m | - | 直線 |
| C3 | r = 1.0 m | 90° 右旋回 | 直角カーブ |
| L4 | 3.0 m | - | 直線 |
| C4 | r = 1.0 m | 90° 右旋回 | 直角カーブ |

### 確定ノード一覧

| ノードID | 位置 | 種別 |
|---------|------|------|
| N01 | L1入口（＝C4終点・ゴール） | 直線入口 |
| N02 | L1中心（**スタート地点**） | 直線中心 |
| N03 | C1入口（L1終点） | カーブ入口 |
| N04 | C1頂点 | カーブ頂点 |
| N05 | L2入口（C1終点） | 直線入口 |
| N06 | L2中心 | 直線中心 |
| N07 | C2入口（L2終点） | カーブ入口 |
| N08 | C2頂点 | カーブ頂点 |
| N09 | L3入口（C2終点） | 直線入口 |
| N10 | L3中心 | 直線中心 |
| N11 | C3入口（L3終点） | カーブ入口 |
| N12 | C3頂点 | カーブ頂点 |
| N13 | L4入口（C3終点） | 直線入口 |
| N14 | L4中心 | 直線中心 |
| N15 | C4入口（L4終点） | カーブ入口 |
| N16 | C4頂点 | カーブ頂点 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```
📁 src/
  📁 raphael_enterprise/          # 既存・変更なし
    （省略）
  📁 web/                         # 既存・変更なし
    （省略）
  📁 simulation/                  # ★新規作成★
    📄 __init__.py                # ★新規作成★
    📄 main.py                    # ★新規作成★ エントリーポイント
    📄 course.py                  # ★新規作成★ コース形状定義
    📄 robot.py                   # ★新規作成★ 差動二輪モデル
    📄 node_manager.py            # ★新規作成★ ノード管理・遷移判定
    📄 camera_simulator.py        # ★新規作成★ 仮想カメラ特徴量生成
    📄 visualizer.py              # ★新規作成★ 描画・アニメーション
    📄 config.py                  # ★新規作成★ 全パラメータ一元管理
    📁 logs/                      # ★新規作成★ 走行ログ出力先
      📄 .gitkeep                 # ★新規作成★ ディレクトリ保持用
    📁 tests/                     # ★新規作成★
      📄 test_course.py           # ★新規作成★ コース閉じ確認テスト
      📄 test_node_manager.py     # ★新規作成★ ノード遷移テスト
```

### 差分サマリー

| 操作 | 対象 | 理由 |
|------|------|------|
| **新規作成** | `src/simulation/` 以下全体 | PoCシミュレーション専用パッケージ |
| **変更なし** | `src/raphael_enterprise/` | 既存ROS2パッケージに影響させない |
| **変更なし** | `src/web/` | フロントエンドに影響させない |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― 全パラメータ一元管理

**役割**: 全ファイルが参照するパラメータをここだけに集約する。数値変更時はこのファイルのみ編集で完結させる。

**実装仕様**:

```
【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 5.0},
    {"id": "C1", "type": "arc",      "radius": 2.0, "angle_deg": 45,  "direction": "right"},
    {"id": "L2", "type": "straight", "length": 3.0},
    {"id": "C2", "type": "arc",      "radius": 0.8, "angle_deg": 45,  "direction": "right"},
    {"id": "L3", "type": "straight", "length": 4.0},
    {"id": "C3", "type": "arc",      "radius": 1.0, "angle_deg": 90,  "direction": "right"},
    {"id": "L4", "type": "straight", "length": 3.0},
    {"id": "C4", "type": "arc",      "radius": 1.0, "angle_deg": 90,  "direction": "right"},
]

【ロボットパラメータ】
ROBOT_WHEEL_BASE = 0.3         # 左右輪間距離 [m]
ROBOT_SPEED = 0.5              # 走行速度 [m/s]
SIMULATION_DT = 0.05           # 時間刻み [s]（=20Hz相当）

【描画パラメータ】
FPS = 30                       # アニメーションフレームレート
COURSE_LINE_COLOR = "black"
COURSE_LINE_WIDTH = 2
ROBOT_COLOR = "royalblue"
ROBOT_ARROW_COLOR = "red"
NODE_MARKER_COLOR = "orange"
NODE_FONT_SIZE = 8

【ノード認識パラメータ】
NODE_TRIGGER_DISTANCE = 0.1    # ノードとみなす距離閾値 [m]

【ログパラメータ】
LOG_DIR = "logs/"
LOG_FILENAME = "run_log.csv"
```

---

### 3-2. `course.py` ― コース形状定義

**役割**: `config.py` のパラメータを読み込み、コース全体の座標点列・各ノード座標・各区間の曲率情報を生成する。他のファイルはすべてこのモジュールから座標を取得する。

**実装仕様**:

```
【クラス】CourseGenerator

【メソッド: generate_course_points()】
  入力  : config.SEGMENTS
  処理  :
    初期状態 = (x=0.0, y=0.0, theta=0.0[rad])  ← L1中心左端を原点とする
    SEGMENTS を順番にループ：
      type == "straight" のとき：
        direction_vector = (cos(theta), sin(theta))
        点列 = 始点から length を STEP_SIZE 刻みで生成
        theta は変化しない
      type == "arc" のとき：
        direction == "right" → 旋回中心はtheta - 90度方向にradiusだけ離れた点
        angle_deg をラジアンに変換
        点列 = 旋回中心を基準に円弧上をSTEP_SIZE刻みで生成
        theta += angle_rad（右旋回なのでマイナス方向に注意）
    全点列を連結して返す
  出力  : numpy配列 shape=(N, 2)  ← コース全点列のXY座標

【メソッド: generate_node_positions()】
  入力  : generate_course_points()の結果 + config.SEGMENTS
  処理  :
    各区間の「入口点」「中心点」のインデックスを計算して座標を抽出
    N01〜N16 の辞書を生成 {"N01": (x,y), "N02": (x,y), ...}
  出力  : dict

【メソッド: get_segment_curvature(segment_id)】
  入力  : 区間ID文字列
  処理  :
    type == "straight" → curvature = 0.0
    type == "arc"      → curvature = 1.0 / radius（右旋回は正値）
  出力  : float

【閉じ確認ロジック】
  generate_course_points()の最終点と初期点(0,0)の距離が
  NODE_TRIGGER_DISTANCE 以下であることをアサーションで確認する
  → 失敗したらValueErrorを出してコース設計の誤りをすぐ検知できるようにする
```

**実装上の注意点**:
- `theta` の更新は右手系か左手系かを統一して扱うこと（numpy の `cos`/`sin` はラジアン）
- 右旋回の場合 `theta` は減少方向（`theta -= angle_rad`）
- `STEP_SIZE = 0.02` [m] 推奨（コース全長約20m → 約1000点）

---

### 3-3. `robot.py` ― 差動二輪モデル

**役割**: 差動二輪ロボットの運動モデルを定義する。コース座標列に沿って状態量（x, y, theta）を更新する。将来的にスリップ外乱を注入する口もここで持つ。

**実装仕様**:

```
【クラス】DifferentialDriveRobot

【状態変数】
  self.x      : float  ← 世界座標X [m]
  self.y      : float  ← 世界座標Y [m]
  self.theta  : float  ← 機体向き [rad]
  self.speed  : float  ← 走行速度 [m/s]（config.ROBOT_SPEEDで初期化）
  self.odom_distance : float  ← 累積走行距離（ODOMシミュレート用）

【メソッド: __init__(start_x, start_y, start_theta)】
  状態変数を初期化する

【メソッド: update_along_course(course_points, step_index)】
  入力  : コース座標列全体 + 現在のステップインデックス
  処理  :
    次のステップ座標 = course_points[step_index + 1]
    dx = 次X - 現在X
    dy = 次Y - 現在Y
    self.x = 次X
    self.y = 次Y
    self.theta = arctan2(dy, dx)
    self.odom_distance += sqrt(dx^2 + dy^2)
  出力  : なし（状態変数を直接更新）

【メソッド: inject_slip(slip_distance)】
  ※将来拡張用・現時点では実装不要だがメソッドは定義しておく
  処理  : odom_distance に slip_distance を加算（誤差シミュレート）

【メソッド: get_state()】
  出力  : dict {"x": float, "y": float, "theta": float, "odom": float}

【プロパティ: position】
  出力  : (self.x, self.y) のタプル
```

---

### 3-4. `camera_simulator.py` ― 仮想カメラ特徴量生成

**役割**: 実カメラの代わりに、コース上の現在位置・区間情報から「カメラで見えるはずの特徴量」を数値として生成する。自己位置推定ロジックの入力となる。

**実装仕様**:

```
【クラス】CameraSimulator

【生成する特徴量の定義】
  curvature_estimate : float
    → 現在の区間の曲率値（course.get_segment_curvature()から取得）
    → 直線=0.0、緩カーブ=0.5、急カーブ=1.25、90度カーブ=1.0
    → ノイズを加算してリアルに見せる（後述）

  line_asymmetry : float
    → 左右ラインの非対称性を [-1.0, 1.0] で表現
    → 直線=0.0（左右対称）
    → 右旋回カーブ=正値（値は曲率に比例）

  line_convergence : float
    → ラインの消失点への収束度 [0.0, 1.0]
    → 直線=1.0（強く収束）、カーブ=0.0〜0.5

【メソッド: get_features(current_segment_id, course_generator)】
  入力  : 現在の区間ID + CourseGeneratorインスタンス
  処理  :
    curvature = course_generator.get_segment_curvature(current_segment_id)
    ガウスノイズ(mean=0, std=0.05)を各特徴量に加算
  出力  : dict {"curvature": float, "asymmetry": float, "convergence": float}

【ノイズパラメータ】
  NOISE_STD = 0.05  ← config.pyに定義して参照する
  numpy.random.normal を使用
  シード固定オプション（再現性のため）: numpy.random.seed(42)
```

---

### 3-5. `node_manager.py` ― ノード管理・遷移判定

**役割**: 現在の機体位置とN01〜N16のノード座標を比較し、どのノードにいるかを判定する。順序制約（前のノードの次のノードしかあり得ない）を適用して誤認識を防ぐ。

**実装仕様**:

```
【クラス】NodeManager

【定数: NODE_SEQUENCE】
  ["N01","N02","N03","N04","N05","N06","N07","N08",
   "N09","N10","N11","N12","N13","N14","N15","N16"]
  ※ N16の次はN01（ループ）

【状態変数】
  self.current_node_index : int  ← 現在のノードのインデックス（0〜15）
  self.node_positions     : dict ← CourseGeneratorから受け取った{ID:(x,y)}
  self.visit_count        : dict ← 各ノードの通過回数（ログ用）

【メソッド: __init__(node_positions)】
  node_positionsを受け取り状態変数を初期化
  current_node_index = 1（N02=スタート地点）で開始

【メソッド: update(robot_x, robot_y)】
  入力  : ロボットの現在XY座標
  処理  :
    ① 次のノードIDを計算：
       next_index = (current_node_index + 1) % 16
       next_node_id = NODE_SEQUENCE[next_index]
    ② 次ノードとの距離を計算：
       dist = sqrt((robot_x - next_node_pos.x)^2 + (robot_y - next_node_pos.y)^2)
    ③ dist < NODE_TRIGGER_DISTANCE（config参照）なら：
       current_node_index = next_index
       visit_count[next_node_id] += 1
       遷移イベントを返す
  出力  : dict {"transitioned": bool, "current_node": str, "visit_count": int}

  ※ 順序制約の実現：
    「次のノードだけ」を監視することで、コース上に同じ特徴の場所があっても
    誤ってジャンプしない設計

【メソッド: get_current_node_id()】
  出力  : str  例: "N05"

【メソッド: get_current_segment_id()】
  処理  :
    current_node_id の先頭文字がLかCかを判定するテーブルで対応
    対応テーブル：
      N01,N02,N03 → "L1"
      N03,N04,N05 → "C1"
      N05,N06,N07 → "L2"
      N07,N08,N09 → "C2"
      N09,N10,N11 → "L3"
      N11,N12,N13 → "C3"
      N13,N14,N15 → "L4"
      N15,N16,N01 → "C4"
  出力  : str  例: "C2"

【メソッド: is_lap_completed()】
  処理  : visit_count["N01"] >= 2 なら True（スタートを2周目以降に再通過）
  出力  : bool

【メソッド: export_log(filepath)】
  処理  : visit_count と通過順序のリストをCSVファイルに書き出す
  出力  : なし
```

---

### 3-6. `visualizer.py` ― 描画・アニメーション

**役割**: コース形状・ノード・機体位置・現在のノードIDをmatplotlibで描画し、FuncAnimationで走行アニメーションを生成する。

**実装仕様**:

```
【クラス】Visualizer

【メソッド: __init__(course_points, node_positions)】
  処理  :
    fig, ax を生成（figsize=(10,10)、縦横比1:1固定 → ax.set_aspect('equal')）
    コース全体をplot（静的レイヤー、config.COURSE_LINE_COLORで描画）
    ノードN01〜N16を scatter で描画（NODE_MARKER_COLOR）
    各ノードIDのテキストラベルをノード座標近くに描画
    ロボットの現在位置を表す点オブジェクト（動的）を初期化
    ロボットの向き矢印オブジェクトを初期化

【メソッド: init_animation()】
  処理  : アニメーション初期フレームの設定（FuncAnimationのinit_func用）

【メソッド: update_frame(frame_index, robot, node_manager)】
  処理  :
    robot.get_state() から現在位置・角度を取得
    ロボットの点オブジェクトの座標を更新
    ロボットの向き矢印をquiverで更新（cos(theta),sin(theta)方向）
    タイトルに以下を表示：
      "Frame:{frame_index} | Node:{current_node_id} | Segment:{current_segment_id} | Dist:{odom:.2f}m"

【メソッド: run_animation(update_func, total_frames)】
  処理  :
    matplotlib.animation.FuncAnimation を使用
      fig=self.fig
      func=update_func
      frames=total_frames
      interval=1000/config.FPS（ms単位）
      blit=True（高速描画）
    plt.show() で表示

【描画レイヤー構成（重ね順）】
  Layer1: コース輪郭線（静的・ax.plot）
  Layer2: ノードマーカー（静的・ax.scatter）
  Layer3: ノードIDラベル（静的・ax.text）
  Layer4: ロボット位置（動的・ax.plot→点オブジェクト）
  Layer5: ロボット向き矢印（動的・ax.quiver）
  Layer6: タイトル文字列（動的・ax.set_title）
```

---

### 3-7. `main.py` ― エントリーポイント

**役割**: 全モジュールを初期化し、シミュレーションループを制御してアニメーションを起動する。

**実装仕様**:

```
【処理フロー（詳細は第4章参照）】

Step1: インポート
  from simulation.course import CourseGenerator
  from simulation.robot import DifferentialDriveRobot
  from simulation.node_manager import NodeManager
  from simulation.camera_simulator import CameraSimulator
  from simulation.visualizer import Visualizer
  from simulation import config

Step2: コース生成
  cg = CourseGenerator(config.SEGMENTS)
  course_points = cg.generate_course_points()
  node_positions = cg.generate_node_positions()
  ← コース閉じ確認はcourse.py内のアサーションが自動実行

Step3: 各モジュール初期化
  スタート地点（N02の座標）をnode_positionsから取得
  robot = DifferentialDriveRobot(start_x, start_y, start_theta=0.0)
  node_manager = NodeManager(node_positions)
  camera_sim = CameraSimulator()
  visualizer = Visualizer(course_points, node_positions)

Step4: update_frameクロージャの定義
  def update_frame(frame_index):
    robot.update_along_course(course_points, frame_index)
    node_result = node_manager.update(robot.x, robot.y)
    segment_id = node_manager.get_current_segment_id()
    features = camera_sim.get_features(segment_id, cg)
    ← featuresは現時点では描画には使わず、将来の推定ロジック用にログ出力のみ
    visualizer.update_frame(frame_index, robot, node_manager)
    if node_manager.is_lap_completed():
      node_manager.export_log(config.LOG_DIR + config.LOG_FILENAME)
      print("LAP COMPLETED")

Step5: アニメーション起動
  total_frames = len(course_points) - 1
  visualizer.run_animation(update_frame, total_frames)
```

---

### 3-8. `tests/test_course.py` ― コース閉じ確認テスト

**役割**: コース生成の閉じ（終点≒始点）をユニットテストで確認する。

**実装仕様**:

```
test_course_is_closed():
  cg = CourseGenerator(config.SEGMENTS)
  points = cg.generate_course_points()
  start = points[0]
  end = points[-1]
  distance = numpy.linalg.norm(start - end)
  assert distance < config.NODE_TRIGGER_DISTANCE
  → 失敗すればコース設計パラメータの修正が必要と即判断できる

test_node_count():
  node_positions = cg.generate_node_positions()
  assert len(node_positions) == 16
```

---

### 3-9. `tests/test_node_manager.py` ― ノード遷移テスト

**役割**: 順序制約ロジックが正しく動作するかを確認する。

**実装仕様**:

```
test_sequential_transition():
  N01〜N16 の座標を順に与えたとき
  current_node_id が順番に遷移することを確認

test_no_skip_transition():
  N01 → N03の座標を与えたとき
  N02 を飛ばして N03 に遷移しないことを確認
  （順序制約により N02 に留まるはず）

test_lap_completion():
  N01〜N16〜N01 と順に座標を与えたとき
  is_lap_completed() が True を返すことを確認
```

---

## 4. データ・制御の処理フロー

### 4-1. 初期化フロー

```
main.py 起動
  │
  ▼
config.py ─────────────────────────────────────────────┐
  │ SEGMENTS / ROBOT_* / FPS / NODE_TRIGGER_DISTANCE    │
  ▼                                                    │
course.py                                              │
  generate_course_points()                              │
    ├─ SEGMENTSをループ処理                              │
    │    直線 → 方向ベクトル × 長さ で点列生成            │
    │    円弧 → 旋回中心基準の円弧点列生成                │
    │    区間終端で theta を更新                         │
    └─ 全点列を連結 → course_points[N,2]                │
  generate_node_positions()                             │
    └─ 各区間入口・中心のインデックスから座標抽出          │
        → node_positions{"N01":(x,y),...,"N16":(x,y)}  │
  コース閉じアサーション確認                             │
  │                                                    │
  ▼                                                    │
robot.py                                               │
  DifferentialDriveRobot(N02の座標, theta=0.0)          │
  │                                                    │
  ▼                                                    │
node_manager.py                                        │
  NodeManager(node_positions)                          │
  current_node_index = 1 (N02)                         │
  │                                                    │
  ▼                                                    │
camera_simulator.py                                    │
  CameraSimulator() ← numpy.random.seed(42)            │
  │                                                    │
  ▼                                                    │
visualizer.py                                          │
  Visualizer(course_points, node_positions)            │
  ├─ fig/ax 生成・aspect='equal'固定                    │
  ├─ Layer1: コース描画（静的）                          │
  ├─ Layer2,3: ノードマーカー+ラベル（静的）              │
  └─ Layer4,5,6: ロボット描画オブジェクト初期化           │
  │                                                    │
  ▼                                                    │
FuncAnimation 起動 ────────────────────────────────────┘
```

---

### 4-2. 毎フレームの更新フロー

```
FuncAnimation が frame_index を increment して update_frame() を呼ぶ
  │
  ▼
【robot.py】 update_along_course(course_points, frame_index)
  │  course_points[frame_index] → x,y,theta を更新
  │  odom_distance += 移動量
  │
  ▼
【node_manager.py】 update(robot.x, robot.y)
  │  次ノード候補（current+1のみ）との距離を計算
  │  距離 < NODE_TRIGGER_DISTANCE → ノード遷移確定
  │  visit_count を更新
  │  current_node_index を更新
  │
  ▼
【node_manager.py】 get_current_segment_id()
  │  現在ノードIDから区間ID（L1〜C4）を返す
  │
  ▼
【camera_simulator.py】 get_features(segment_id, course_generator)
  │  curvature / asymmetry / convergence を計算しガウスノイズを付加
  │  ※ 現フェーズでは推定ロジックへは未接続・ログ用途のみ
  │
  ▼
【visualizer.py】 update_frame(frame_index, robot, node_manager)
  │  Layer4: ロボット位置点を更新
  │  Layer5: 向き矢印を更新
  │  Layer6: タイトル文字列を更新
  │  "Frame:xxx | Node:N05 | Segment:L2 | Dist:3.21m"
  │
  ▼
【main.py】 ラップ完了チェック
  │  is_lap_completed() == True なら
  │  export_log() → logs/run_log.csv 書き出し
  │  コンソールに "LAP COMPLETED" 表示
  │
  ▼
matplotlib が描画を更新 → 次フレームへ
```

---

### 4-3. データ依存関係図

```
config.py
  ├──► course.py ──────────────────────► course_points[N,2]
  │        └──────────────────────────► node_positions{16個}
  │                                          │
  ├──► robot.py ◄────────────────────────────┤（N02座標で初期化）
  │        └─── get_state() ──────────────────────────────────┐
  │                                          │                │
  ├──► node_manager.py ◄──────────────────────┤（node_positions）
  │        ├─── update(x,y) ◄─────────────────────────────────┤
  │        ├─── get_current_segment_id()                      │
  │        └─── is_lap_completed()                            │
  │                  │                                        │
  ├──► camera_simulator.py ◄──── segment_id                  │
  │        └─── get_features() → features（将来の推定ロジック用）│
  │                                                           │
  └──► visualizer.py ◄────────────────────────────────────────┘
           ├── course_points（初期化時）
           ├── node_positions（初期化時）
           ├── robot.get_state()（毎フレーム）
           └── node_manager.get_current_node_id()（毎フレーム）
```

---

### 4-4. 将来拡張ポイント（実装担当者への申し送り）

| 拡張項目 | 場所 | 内容 |
|---------|------|------|
| スリップ外乱注入 | `robot.py` → `inject_slip()` | ODOMに誤差を加えてカメラ主体推定を検証 |
| カメラ特徴量→推定ロジック接続 | `main.py` の update_frame | `features` を使った区間分類ロジックを追加 |
| Unityデータとの差し替え | `camera_simulator.py` | `get_features()` をUnity出力の実画像処理に置換 |
| DTWマッチング | 新規 `estimator.py` | IMU+ODOMの軌跡を事前データと照合する将来モジュール |
| ROS2ノード化 | `raphael_enterprise/course_lap_node.py` | シミュレーション検証後に既存ROS2パッケージへ移植 |