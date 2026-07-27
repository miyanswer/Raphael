# ARCH_TITLE: sim_multi_window_fpv_isolation

## 1. システム概要と決定された採用技術

### システム概要
本設計は、ロボットレーシングシミュレータの可視化モジュール（`visualizer.py`）における、「俯瞰視点映像が画像処理AIノードに送信されてしまい誤動作を引き起こす」という不具合を抜本的に解決し、併せてUIの視認性を向上させる改修設計である。
現状のCキーによる単一ウィンドウでの視点切り替えを廃止し、Panda3Dのマルチウィンドウ機能を活用して「FPV（一人称）専用ウィンドウ」と「俯瞰（上空）専用ウィンドウ」を独立して同時に描画する。画像処理AIへはFPVウィンドウのバッファのみを送信することで、AIの混乱を完全に排除する。
また、地面（背景）の色を白色から茶色（大地色）へ変更し、コースや白線のコントラストを向上させる。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| 3Dエンジン | Panda3D (ShowBase) |
| 通信・ミドルウェア | ROS 2 (rclpy), `cv_bridge` |
| 画像処理 | OpenCV (`cv2`), Numpy |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

物理的なフォルダ構造の追加・削除は発生しない。シミュレーション可視化モジュールの1ファイルをピンポイントで修正する。

```text
📁 src/
  📁 simulation/
    📄 visualizer.py   # ★修正: 大地色の変更、サブウィンドウ(俯瞰)の追加、画像取得元の固定
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `simulation/visualizer.py` | `_build_ground_polygon`での地面色変更。`__init__`でのキーバインド廃止と`openWindow`によるサブウィンドウ作成。`update_camera`での2カメラ同時制御。`get_camera_image`でのメインウィンドウからの画像取得固定。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `simulation/visualizer.py` (3D描画・可視化モジュール)

*   **【★修正1】地面（大地）のカラー変更**
    `_build_ground_polygon` メソッド内で、ベースとなる大地のポリゴンの色指定を白から茶色（サドルブラウン等）に変更する。
    ```python
    def _build_ground_polygon(self):
        # ...既存のCardMaker生成処理...
        ground = self.render.attachNewNode(cm.generate())
        # ...
        # [修正前] ground.setColor(1.0, 1.0, 1.0, 1.0)
        # [修正後] 茶色に設定 (R:0.55, G:0.27, B:0.07 等)
        ground.setColor(0.55, 0.27, 0.07, 1.0)
    ```

*   **【★修正2】Cキー切り替えの廃止とサブウィンドウ（俯瞰専用）の構築**
    `__init__` メソッドから視点切り替えイベントを削除し、Panda3Dの `openWindow()` を用いて俯瞰用のサブウィンドウと専用カメラを新規生成する。
    ```python
    def __init__(self, course_points, node_positions, left_boundary, right_boundary):
        ShowBase.__init__(self)
        # ... 既存の初期化処理 ...

        # [削除] self.camera_mode = "fpv"
        # [削除] self.accept('c', self.toggle_camera_mode)
        # [削除] toggle_camera_mode メソッド自体も削除する

        # 【追加】サブウィンドウ（俯瞰視点用）の生成
        self.sub_win = self.openWindow(name="Top View Window")
        # サブウィンドウ用のカメラノードを生成し、レンダーツリーにアタッチ
        self.sub_cam = self.makeCamera(self.sub_win)
        self.sub_cam.reparentTo(self.render)
    ```

*   **【★修正3】2つのカメラの同時姿勢更新**
    `update_camera` メソッドを改修し、メインカメラ（`self.camera`）はFPV視点に、サブカメラ（`self.sub_cam`）は俯瞰視点にそれぞれ毎フレーム同時に更新する。
    ```python
    def update_camera(self, robot_x, robot_y, robot_theta):
        """FPVカメラと俯瞰カメラの位置・姿勢を同時に更新する"""
        # 1. メインカメラ (FPV視点) の更新
        # ロボットの少し上、少し前に配置する (既存のFPVロジックを流用)
        z_fpv = 0.5
        # Panda3DのHpr (Heading, Pitch, Roll) に合わせる
        h_fpv = np.degrees(robot_theta) - 90.0
        self.camera.setPos(robot_x, robot_y, z_fpv)
        self.camera.setHpr(h_fpv, 0, 0)

        # 2. サブカメラ (俯瞰視点) の更新
        # ロボットの真上から見下ろす
        z_top = 20.0  # 視野に合わせて高さを調整
        self.sub_cam.setPos(robot_x, robot_y, z_top)
        self.sub_cam.setHpr(0, -90, 0)  # Pitchを-90度にして真下を向く
    ```

*   **【★修正4】AIノード向け画像の抽出領域固定 (重要)**
    `get_camera_image` メソッドにおいて、画像を取得するバッファを「メインウィンドウ（FPV）」に明示的に限定する。
    ```python
    def get_camera_image(self):
        """画像処理AIに渡すための純粋なFPV映像のみを取得する"""
        # self.win (メインウィンドウ) の DisplayRegion からテクスチャを取得
        # ※ self.sub_win からは取得しないため、俯瞰ウィンドウがどう描画されてもAIには影響しない
        region = self.win.getDisplayRegion(0)
        screenshot = region.getScreenshot()
        
        if screenshot is None:
            return None
            
        # 既存の screenshot から numpy (BGR) 配列への変換ロジックを維持
        # ...
    ```

---

## 4. データ・制御の処理フロー

本改修を適用した後の、シミュレータから画像処理AIへのデータフローは以下の通り完全に分離される。

```text
【毎フレームの描画・画像送信フロー】

1. [Physics Update] ロボットの物理挙動・位置更新
   └─ simulation_task にて x, y, theta が計算される。

2. [Camera Update] Visualizerでの2カメラ同時制御
   ├─ FPVカメラ (self.camera): メインウィンドウ用。ロボットの視点に追従。
   └─ 俯瞰カメラ (self.sub_cam): サブウィンドウ用。ロボットの上空に追従。

3. [Rendering] Panda3Dによる並行描画
   ├─ メインウィンドウ (Window 1): FPV視点の描画 (地面は茶色)
   └─ サブウィンドウ (Window 2): 俯瞰視点の描画 (地面は茶色)

4. [Image Extraction] FPV映像の抽出と配信
   ├─ get_camera_image() が呼び出される。
   ├─ メインウィンドウ(self.win)のDisplayRegionのバッファのみをNumpy配列化。
   └─ /camera/image_raw トピックとしてパブリッシュ。
   
5. [AI Control]
   └─ AIノード (course_lap_node.py) は純粋なFPV映像のみを受信し、安全かつ正確に目標位置を算出。
```