# ARCH_TITLE: ros2_course_lap_3d_panda3d_v6

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが台形コース（反時計回り）を一周するPythonシミュレーション。
本バージョンはプロジェクトの大きなマイルストーンとなる**「Panda3Dによる3D化」**と、コースのコーナーをF1コースのように滑らかでダイナミックにする**「カーブ半径の拡大（R=10.0m）」**が追加されたバージョンである。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状 | 台形プロポーション（上辺より下辺が長く、C3/C4=90度）を完全維持 |
| カーブ半径 | **全コーナー r=10.0m**（前バージョンの3.5mから拡大） ← 今バージョン追加 |
| 描画エンジン | **Panda3D**（`matplotlib` を完全廃止してリプレイス） ← 今バージョン追加 |
| ロボットモデル | 仮モデルとして**シンプルな直方体（Cube）**を使用 |
| カメラ視点 | **一人称視点（ロボット同期）と俯瞰視点（上空固定）の切り替え式** |
| 切り替え操作 | キーボードの `[C]` キーでトグル切り替え |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画・3D | **`Panda3D`** (`ShowBase`, `GeomNode`, `LineSegs`) | **確定（新規）** |
| 数値計算 | `numpy` | 確定 |
| 自己位置推定 | 順序制約トポロジカル推定 | 確定 |
| ノード数 | 16ノード（N01〜N16） | 確定 |

※本バージョンから、動作環境に `pip install panda3d` が必須要件として追加される。

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # ★変更★ Panda3DのtaskMgrによるループ制御に変更
    📄 course.py                  # 変更なし（既存のロジックでそのまま機能する）
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # ★変更★ matplotlibを全削除し、Panda3Dベースに全面リプレイス
    📄 config.py                  # ★変更★ SEGMENTSのradiusを10.0に書き換え
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
| **変更** | `simulation/config.py` | `SEGMENTS` 内の全カーブの `radius` を 10.0 に変更 | 極小 |
| **変更** | `simulation/visualizer.py` | `matplotlib` を廃止し、Panda3Dの `ShowBase` を継承して全面再構築 | 大 |
| **変更** | `simulation/main.py` | 描画更新処理を Panda3D の `taskMgr` に登録する方式に変更 | 中 |
| **変更なし** | 上記以外の全ファイル | ロジックや数値計算への影響ゼロ | - |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― カーブ半径の拡大（差分のみ）

**変更ルール**：`SEGMENTS` 定数内の `C1`, `C2`, `C3`, `C4` の `radius` を `3.5` から `10.0` に変更する。
**※注意**：直線の `length` やカーブの `angle_deg` は**絶対に一切変更しない**こと（コースが閉じなくなるため）。

```python
# 【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 15.0},
    {"id": "C1", "type": "arc",      "radius": 10.0, "angle_deg":  45, "direction": "left"},
    {"id": "L2", "type": "straight", "length": 42.43},
    {"id": "C2", "type": "arc",      "radius": 10.0, "angle_deg": 135, "direction": "left"},
    {"id": "L3", "type": "straight", "length": 45.0},
    {"id": "C3", "type": "arc",      "radius": 10.0, "angle_deg":  90, "direction": "left"},
    {"id": "L4", "type": "straight", "length": 30.0},
    {"id": "C4", "type": "arc",      "radius": 10.0, "angle_deg":  90, "direction": "left"},
]
```
※その他の定数パラメータ（幅、色、ノイズ、ログ設定など）はすべて既存のまま維持する。

---

### 3-2. `visualizer.py` ― Panda3D への全面リプレイス

`matplotlib` 関連のコードをすべて削除し、Panda3D の `ShowBase` を継承するクラスとして再構築する。

#### クラス定義と初期化
```python
from direct.showbase.ShowBase import ShowBase
from panda3d.core import LineSegs, NodePath, GeomNode, Vec3, Point3
from panda3d.core import GeomVertexFormat, GeomVertexData, Geom, GeomTriangles
from simulation import config
import numpy as np

class Visualizer(ShowBase):
    def __init__(self, course_points, node_positions, left_boundary, right_boundary):
        ShowBase.__init__(self)
        self.course_points = course_points
        self.node_positions = node_positions
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary

        # 背景色（芝生）の設定
        self.setBackgroundColor(0.0, 0.5, 0.0)  # config.GRASS_COLOR 相当のRGB

        # 3Dオブジェクトの構築
        self._build_road_polygon()
        self._build_road_lines()
        self._build_robot_model()
        self._build_node_markers()

        # カメラ制御の初期化
        self.camera_mode = "fpv"  # "fpv": 一人称, "top": 俯瞰
        self.accept('c', self.toggle_camera_mode)  # [C]キーでトグル
```

#### 各オブジェクトの構築方針（Zファイティング対策必須）
3D空間で面や線が重なってちらつく（Zファイティング）のを防ぐため、Z座標（高さ）をわずかにずらす。

*   **Layer1: 黒路面ポリゴン (Z=0.0)**
    *   `GeomVertexData` と `GeomTriangles` を用いて、`left_boundary` と `right_boundary` の点列間に三角形ポリゴンを敷き詰める。
    *   または、シンプルな実装として Panda3D の `CardMaker` や内蔵のポリゴン生成機能を用いてもよい。色は黒とする。
*   **Layer2: 白線 (Z=0.01)**
    *   `Panda3D.core.LineSegs` を使用し、外側・内側・中心線の各点列 (x, y, 0.01) を `moveTo` と `drawTo` で繋いで線を描画する。
*   **Layer3: ノードマーカー (Z=0.02)**
    *   `node_positions` の座標 (x, y, 0.02) に、小さな球体や円柱（`loader.loadModel`）を配置し、色をオレンジにする。
*   **Layer4: ロボットモデル (Z=0.1)**
    *   仮モデルとして `self.robot_node = self.loader.loadModel("models/box")` を読み込み、適度なスケール（例: `setScale(0.5, 0.8, 0.3)`）を適用。色は青系（`setColor(0.2, 0.4, 0.8)`）にする。

#### カメラ制御メソッド
```python
    def toggle_camera_mode(self):
        self.camera_mode = "top" if self.camera_mode == "fpv" else "fpv"

    def update_camera(self, robot_x, robot_y, robot_theta):
        if self.camera_mode == "fpv":
            # 一人称視点：ロボットの(少し後方・少し上)から前方を見る
            # 例: ロボット位置からZ=0.5、後方に0.5ずらし、向いている方向を見る
            cam_x = robot_x - 0.5 * np.cos(robot_theta)
            cam_y = robot_y - 0.5 * np.sin(robot_theta)
            self.camera.setPos(cam_x, cam_y, 0.5)
            # theta(ラジアン)をPanda3DのHeading(度)に変換（PandaはZ軸回転がH）
            # 数学の極座標系とPandaの座標系の違いに注意。通常 H = (theta * 180 / PI) - 90
            heading = np.degrees(robot_theta) - 90
            self.camera.setHpr(heading, 0, 0)
        else:
            # 俯瞰視点：コース全体が見える上空から見下ろす
            self.camera.setPos(20, 20, 100) # コース中央付近の上空
            self.camera.setHpr(0, -90, 0)   # ピッチ-90度（真下）
```

---

### 3-3. `main.py` ― タスク制御への移行

`matplotlib` の `FuncAnimation` で行っていたフレーム更新を、Panda3D の `taskMgr` を用いたメインループ処理に差し替える。

```python
# 変更箇所：Step 4 と Step 5 を以下のように書き換える

    # 状態変数の初期化
    frame_index = 0
    total_frames = len(course_points) - 1
    lap_logged = False

    # Step 4: Panda3D用更新タスクの定義
    def simulation_task(task):
        nonlocal frame_index, lap_logged

        if frame_index >= total_frames:
            print("[INFO] Animation reached the end.")
            return task.done  # タスク終了

        # 既存のロジック（そのまま流用）
        robot.update_along_course(course_points, frame_index)
        node_result = node_manager.update(robot.x, robot.y)
        segment_id = node_manager.get_current_segment_id()
        features = camera_sim.get_features(segment_id, cg)

        # 3Dモデルの位置・姿勢更新
        visualizer.robot_node.setPos(robot.x, robot.y, 0.1)
        # Headingの更新（Panda3D基準）
        visualizer.robot_node.setHpr(np.degrees(robot.theta) - 90, 0, 0)

        # カメラ視点の更新
        visualizer.update_camera(robot.x, robot.y, robot.theta)

        # ラップ完了判定
        if node_manager.is_lap_completed() and not lap_logged:
            log_path = os.path.join(config.LOG_DIR, config.LOG_FILENAME)
            node_manager.export_log(log_path)
            print(f"[SUCCESS] LAP COMPLETED! Log saved to {log_path}")
            lap_logged = True

        frame_index += 1
        return task.cont  # 次のフレームも継続

    # Step 5: アニメーション起動
    print(f"Starting 3D simulation animation ({total_frames} frames)...")
    visualizer.taskMgr.add(simulation_task, "simulation_task")
    visualizer.run()  # Panda3Dのメインループ起動
```

---

## 4. データ・制御の処理フロー

### 4-1. システム初期化・オブジェクト構築フロー

```
main.py
  │
  ▼
course.py (CourseGenerator)
  │ r=10.0m の広大なカーブを持つ course_points[X, Y] を生成
  │ 法線スムージングも前フェーズのまま動作
  └─► left_boundary, right_boundary
  │
  ▼
visualizer.py (Panda3D: ShowBase)
  │ [1] ウィンドウ初期化・背景緑化
  │ [2] 路面ポリゴン(Z=0.0)を GeomTriangles で構築
  │ [3] 3本の白線(Z=0.01)を LineSegs で構築
  │ [4] ノードマーカー(Z=0.02)を配置
  │ [5] ロボットの仮モデル（box）(Z=0.1)をロード
  │ [6] イベントリスナー追加: [C]キーでトグル
  │
  ▼
main.py
  └─► taskMgr.add(simulation_task)
  └─► visualizer.run() （Panda3D描画ループ開始）
```

### 4-2. 毎フレームの更新フロー (Panda3D taskMgr)

```
taskMgr
  │ (毎フレーム自動実行)
  ▼
simulation_task()
  │
  ├─ 1. ロジック更新: robot.update_along_course(frame)
  ├─ 2. ロジック判定: node_manager.update()
  │
  ├─ 3. ロボット描画更新: visualizer.robot_node.setPos(x, y, 0.1)
  │                       visualizer.robot_node.setHpr(Heading)
  │
  ├─ 4. カメラ制御: visualizer.update_camera(x, y, theta)
  │     ├─ fpvモード時: ロボットの頭上にカメラを配置し進行方向を向く
  │     └─ topモード時: Z=100から真下を見下ろす
  │
  └─ 5. return task.cont (ループ継続)
```

### 4-3. 実行前の準備と動作確認手順（実装担当者への指示）

```
【Step 1: 環境準備】
ターミナルで以下のコマンドを実行し、Panda3Dをインストールすること。
$ pip install panda3d

【Step 2: 既存テストの実行確認】
$ python -m pytest simulation/tests/test_course.py -v
$ python -m pytest simulation/tests/test_node_manager.py -v
※コースの形状（radius=10.0）が変わっても、プロポーション比率が維持されているため、距離誤差は許容範囲に収まりテストはPASSEDになる。

【Step 3: シミュレーション起動】
$ python -m simulation.main

【目視確認チェックリスト】
✅ 3Dウィンドウが立ち上がり、緑の背景が表示される
✅ カメラが「一人称視点」となり、直方体のロボットと共にコース（黒路面＋白線）を反時計回りに走る
✅ 白線のカーブが、前バージョンよりも「F1コースのように非常にゆったりと滑らか」であること
✅ キーボードの『C』キーを押すと、上空からの「俯瞰視点」に切り替わること
✅ コンソールに "LAP COMPLETED" が出力され、ログが書き出されること
```

### 4-4. 次フェーズへの申し送り

| フェーズ | 拡張項目 | 対応内容 |
|---------|---------|---------|
| **画像処理** | OpenCV連携 | 一人称視点カメラから取得した画像をバッファ経由で抽出し、OpenCV（CVBridge同等）に渡す処理の実装 |
| **制御** | ROS2移植 | このPanda3D環境から送られる画像をSubscribeし、自己位置推定とTwistコマンドをパブリッシュするノードの実装 |
| **外観** | 本番モデル適用 | 動作確認完了後、仮モデル(box)を本番のロボット3Dモデル(gltf/obj)に差し替える |