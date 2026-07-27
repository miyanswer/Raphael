# ARCH_TITLE: ros2_course_lap_3d_panda3d_v8

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットがPanda3D環境で台形コース（反時計回り）を周回するPythonシミュレーション。
本バージョン（v8）では、社長のフィードバックに基づき、3D空間の視覚的リアリティの向上とカメラ視点の最適化を行う。

| 合意項目 | 決定内容 |
|---------|---------|
| 空間背景色 | **背景色（空）を「白」に変更**（前バージョンの緑から変更） |
| 地面（芝生） | **広大な緑色の平面ポリゴンをZ=-0.01に新規生成し、地面を表現** |
| FPVカメラ位置 | 機体の前方（+0.6m）配置は維持し、**高さ（Z）を0.3mから0.4mへ引き上げ** |
| 俯瞰カメラ位置 | コース全景を見切れずに収めるため、**高度（Z）を150mに引き上げ、中央座標(X=20, Y=30)に移動** |
| シミュレーション動作 | 1周完了時に初期位置にリセットされ、無限に周回を続ける（前バージョンから維持） |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画・3D | `Panda3D` (`ShowBase`, `GeomNode`, `CardMaker` 等) | 確定 |
| 数値計算 | `numpy` | 確定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理構造に変更は発生しない。ロジックの修正のみとなる。

```text
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # 変更なし（v7の無限ループ化コードを維持）
    📄 course.py                  # 変更なし
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # ★変更★ 背景色白化・芝生ポリゴン追加・カメラ座標修正
    📄 config.py                  # 変更なし
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
| **変更** | `simulation/visualizer.py` | 背景色の変更、`CardMaker`による地面追加、カメラ座標調整 | 小 |
| **維持** | `simulation/main.py` | 既存の「1周完了時のフレームインデックスリセット」ロジックを確実に残す | ゼロ |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `visualizer.py` ― 空間描画とカメラ視点の改修

Panda3D環境の視覚的調整とカメラ座標の変更を行う。実装担当者は以下の仕様に沿ってコードを修正すること。

#### (1) 初期化・背景色・地面ポリゴンの追加
```python
from panda3d.core import CardMaker  # 追加インポート

class Visualizer(ShowBase):
    def __init__(self, course_points, node_positions, left_boundary, right_boundary):
        ShowBase.__init__(self)
        self.course_points = course_points
        self.node_positions = node_positions
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary

        # 修正: 背景色（空）を「白」に設定
        self.setBackgroundColor(1.0, 1.0, 1.0, 1.0)

        # 3Dオブジェクトの構築
        self._build_ground_polygon()  # ★新規追加
        self._build_road_polygon()
        self._build_road_lines()
        self._build_robot_model()
        self._build_node_markers()

        # カメラ設定（変更なし）
        self.camera_mode = "fpv"
        self.accept('c', self.toggle_camera_mode)

    def _build_ground_polygon(self):
        """緑の巨大な芝生ポリゴン (Z=-0.01) を生成"""
        cm = CardMaker('ground_plane')
        # -500から500の広大な四角形を作成
        cm.setFrame(-500, 500, -500, 500) 
        ground = self.render.attachNewNode(cm.generate())
        
        # CardMakerはデフォルトでXZ平面を作るので、P(ピッチ)を-90度回転してXY平面(地面)にする
        ground.setHpr(0, -90, 0)
        
        # 路面(Z=0.0)より少し下のZ=-0.01に配置し、色を緑色に設定
        ground.setPos(0, 0, -0.01)
        ground.setColor(0.0, 0.5, 0.0, 1.0)
```

#### (2) カメラ座標の調整
```python
    def update_camera(self, robot_x, robot_y, robot_theta):
        if self.camera_mode == "fpv":
            # 一人称視点：ロボットの前方に配置
            cam_x = robot_x + 0.6 * np.cos(robot_theta)
            cam_y = robot_y + 0.6 * np.sin(robot_theta)
            
            # 修正: 高さを 0.3 から 0.4 に引き上げ
            self.camera.setPos(cam_x, cam_y, 0.4)
            
            heading = np.degrees(robot_theta) - 90.0
            self.camera.setHpr(heading, 0, 0)
        else:
            # 俯瞰視点：コース中央上空に配置し、全景が見切れないようにする
            # 修正: 座標を (20, 30, 150) に変更
            self.camera.setPos(20, 30, 150)
            self.camera.setHpr(0, -90, 0)
```

---

### 3-2. `main.py` ― 無限周回の維持確認（実装担当者への念押し）

前バージョンの要望で実装された「無限周回ロジック」が消えないように、以下の構造が保たれていることを確認すること。

```python
    def simulation_task(task):
        nonlocal frame_index, lap_logged

        # フレーム終端到達時、タスクを終了させずに0にリセットして継続
        if frame_index >= total_frames:
            print("[INFO] Lap finished. Restarting for infinite loop...")
            frame_index = 0

        # ... (中略) ...

        # 常に task.cont を返す
        frame_index += 1
        return task.cont
```

---

## 4. データ・制御の処理フロー

今回の修正による、空間構築と毎フレームの更新フローは以下のようになる。

```text
[初期化フロー]
main.py
  └─► Visualizer() 初期化
        ├─ setBackgroundColor: 空を【白】で塗りつぶす
        ├─ _build_ground_polygon: Z=-0.01 に【緑】の巨大平面を敷く
        ├─ _build_road_polygon: Z=0.0 に【黒】の路面を構築
        └─ _build_road_lines: Z=0.01 に【白】のラインを描画

[更新フロー (taskMgr)]
simulation_task() (毎フレーム実行・無限ループ)
  ├─ ロボット位置・自己位置更新
  ├─ 3Dモデル描画更新 (setPos / setHpr)
  ├─ カメラ制御: visualizer.update_camera(x, y, theta)
  │    ├─ fpvモード時: ロボットの【前方+0.6m / 高さZ=0.4m】にカメラを配置
  │    └─ topモード時: コース中央上空【X=20, Y=30, Z=150m】から見下ろす
  └─ return task.cont
```