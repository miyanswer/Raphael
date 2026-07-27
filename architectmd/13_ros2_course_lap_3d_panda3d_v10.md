# ARCH_TITLE: ros2_course_lap_3d_panda3d_v10

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットがPanda3D環境でコースを周回するPythonシミュレーション。
本バージョン（v10）では、社長とCTOの合意に基づき、3D空間における「空」「大地」「コース外縁の芝生」の描画を3層構造（レイヤー）で再構築し、視覚的なリアリティを向上させる。

| 合意項目 | 決定内容 |
|---------|---------|
| 空（背景色） | `setBackgroundColor` を使用し、背景を **水色（0.53, 0.81, 0.92, 1.0）** に変更 |
| 大地（ベース） | 広大な平面（`-500`〜`500`）の色を **白** に変更し、最下層の **Z = -0.02** に配置 |
| 芝生（コース外縁） | 道路ポリゴンの左右から **外側に4m幅** 分拡張した頂点を計算し、**緑色** の芝生ポリゴンを **Z = -0.01** に新規生成 |
| 道路（コース） | 既存の黒い道路ポリゴン（Z = 0.0）は変更なし |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画・3D | `Panda3D` (`CardMaker`, `GeomTriangles`による頂点計算) | 確定 |
| 数値計算 | `numpy` | 確定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理構造に変更は発生しない。描画ロジックの修正のみとなる。

```text
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # 変更なし
    📄 course.py                  # 変更なし
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # ★変更★ 背景色の変更、白の大地と緑の芝生ポリゴンの追加
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
| **変更** | `simulation/visualizer.py` | `__init__`の背景色変更、`_build_ground_polygon`内に「白い平面」と「緑の芝生」の2段階描画処理を実装 | 小 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `visualizer.py` ― 空間描画の3層レイヤー化

Panda3Dの描画設定を改修する。実装担当者は以下の仕様に従い、既存のメソッドを正確に書き換えること。

#### (1) `__init__` メソッドの背景色変更
```python
    def __init__(self, course_points, node_positions, left_boundary, right_boundary):
        ShowBase.__init__(self)
        self.course_points = course_points
        self.node_positions = node_positions
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary

        # 修正: 背景色（空）を「水色（スカイブルー）」に設定
        self.setBackgroundColor(0.53, 0.81, 0.92, 1.0)

        # 3Dオブジェクトの構築
        self._build_ground_polygon()
        self._build_road_polygon()
        self._build_road_lines()
        self._build_robot_model()
        self._build_node_markers()

        # カメラ設定
        self.camera_mode = "fpv"  # "fpv": 一人称視点, "top": 俯瞰視点
        self.accept('c', self.toggle_camera_mode)
```

#### (2) `_build_ground_polygon` メソッドの全面改修
白い巨大平面（Z=-0.02）と緑の芝生ポリゴン（Z=-0.01）を重ねて描画する。
```python
    def _build_ground_polygon(self):
        """白い広大な大地 (Z=-0.02) と、コース沿い4mの緑の芝生 (Z=-0.01) を生成"""
        
        # 1. 白い広大な大地（ベース）
        cm = CardMaker('ground_plane')
        cm.setFrame(-500, 500, -500, 500)
        ground = self.render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0)
        ground.setPos(0, 0, -0.02)
        ground.setColor(1.0, 1.0, 1.0, 1.0)  # 白

        # 2. 道路の両端+4mの範囲を緑の芝生ポリゴンとして構築
        vdata = GeomVertexData('grass_vertices', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')

        # 延長率 = (現在の道幅の半分 + 芝生の幅4.0m) / 道幅の半分
        half_width = config.COURSE_WIDTH / 2.0
        ratio = (half_width + 4.0) / half_width

        n = len(self.course_points)
        for i in range(n):
            cx, cy = self.course_points[i]
            lx, ly = self.left_boundary[i]
            rx, ry = self.right_boundary[i]

            # 中心座標と境界座標からベクトルを延長して芝生の外縁座標を計算
            gl_x = cx + (lx - cx) * ratio
            gl_y = cy + (ly - cy) * ratio
            gr_x = cx + (rx - cx) * ratio
            gr_y = cy + (ry - cy) * ratio

            vertex.addData3(gl_x, gl_y, -0.01)
            color.addData4(0.0, 0.5, 0.0, 1.0)  # 緑
            vertex.addData3(gr_x, gr_y, -0.01)
            color.addData4(0.0, 0.5, 0.0, 1.0)

        # 三角形を構成してポリゴンを生成
        tris = GeomTriangles(Geom.UHStatic)
        for i in range(n - 1):
            v1, v2, v3, v4 = i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 3
            tris.addVertices(v1, v2, v3)
            tris.addVertices(v2, v4, v3)

        # コースの始点と終点を閉じる
        if n > 0:
            last_idx = (n - 1) * 2
            tris.addVertices(last_idx, last_idx + 1, 0)
            tris.addVertices(last_idx + 1, 1, 0)

        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('grass_node')
        node.addGeom(geom)
        self.render.attachNewNode(node)
```

---

## 4. データ・制御の処理フロー

今回の改修により、Z軸（高さ）を利用した厳密なレイヤー描画処理が行われる。

```text
[初期化フロー]
main.py
  └─► Visualizer() 初期化
        ├─ setBackgroundColor: 空間全体を【水色】で塗りつぶす (空)
        │
        ├─ _build_ground_polygon: 
        │    ├─ Z=-0.02 に【白】の巨大平面を敷く (大地)
        │    └─ Z=-0.01 にコース境界+4mの頂点計算を行い、【緑】のポリゴンを敷く (芝生)
        │
        ├─ _build_road_polygon: 
        │    └─ Z=0.00 に【黒】の路面を構築 (道路)
        │
        └─ _build_road_lines: 
             └─ Z=0.01 に【白】のラインを描画 (白線)

[更新フロー (taskMgr)]
  └─ 変更なし（前バージョンまでの状態量更新と無限ループ処理を維持）
```