# ARCH_TITLE: course_lap_sim_visual_racing_integration

## 1. システム概要と決定された採用技術

### システム概要
本システムは、社長とCTOの合意に基づき、固定座標の軌道をなぞる従来のシミュレータを「自律走行型のROS 2ロボットシミュレータ」へと抜本的に改修し、画像情報のみで走行するビジュアルレーシングAI（`course_lap_node.py`）と相互連携させる。
また、開発およびデバッグ効率を最大化するため、制御ノード側で処理している内部情報（関心領域=ROI、重心位置、目標軌道ライン、現在のステート）をカメラ画像にオーバーレイ表示する「デバッグ用リアルタイムHUD（ヘッドアップディスプレイ）」を実装する。

| 合意項目 | 決定内容 |
|---------|---------|
| シミュレータのROS化 | シミュレータ内のロボットモデルをROS 2ノード化し、`/cmd_vel`を受信して自律的に物理移動（位置更新）を行うよう改修 |
| 仮想カメラパブリッシュ | Panda3Dの描画バッファから画像を取得し、`/camera/image_raw`トピックとして毎フレーム配信する |
| ビジュアルサーボAI | カメラ画像をHSV変換して黒・白・緑を抽出し、ステートマシンで「緊急停止」「カーブ減速」「アウト・イン・アウト軌道」を自律制御 |
| リアルタイムHUD表示 | 受信した画像上に各ROIの枠（赤・青・黄）、算出した路面重心（赤ドット）、制御目標ライン（緑縦線）、ステート情報をリアルタイム描画 |

### 決定された採用技術
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| 3Dシミュレータ / 画像取得 | Panda3D, `numpy` |
| ROS 2通信 / 画像変換 | `rclpy`, `geometry_msgs/Twist`, `sensor_msgs/Image`, `cv_bridge` |
| 画像処理 / HUD描画 | `OpenCV` (`cv2`) |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理構造に変更は発生しない。対象ファイルの内部ロジックを全面改修する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★変更大 (ビジュアルサーボ制御＆HUD可視化の実装)
📁 simulation/
  📄 main.py                      # ★変更大 (ROS 2通信ループと3D描画ループの統合、カメラ配信)
  📄 robot.py                     # ★変更大 (配列移動の廃止、Twistによるオドメトリ物理移動)
  📄 visualizer.py                # ★変更中 (Panda3D描画バッファからの画像抽出メソッド追加)
```

### 差分サマリー

| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | ROS 2トピックのPub/Sub、3段ROI解析（安全/カーブ/軌道）、動的オフセットPID制御、HUD描画の実装 |
| `main.py` | `rclpy`の初期化、`/camera/image_raw`の配信、毎フレームの`spin_once`処理の統合 |
| `robot.py` | ROS 2 `Node`クラスの継承、`/cmd_vel`の購読、`update_physics(dt)`による自律位置更新ロジックの追加 |
| `visualizer.py` | `get_camera_image()`の実装（画面キャプチャからBGR numpy配列への変換） |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `simulation/robot.py`
決められた配列上の座標移動処理を破棄し、外部からのコマンドを待つ自律モデルに変更する。

*   **ノード化と通信定義**:
    *   `rclpy.node.Node` を継承し、クラスをROSノード化。
    *   初期化時に `/cmd_vel` (`geometry_msgs/Twist`) のサブスクライバを定義し、受信した速度 (`linear.x`) と角速度 (`angular.z`) をクラス変数に保持する。
*   **物理更新ロジックの刷新**:
    *   既存の `update_along_course()` を削除。
    *   新規に `update_physics(dt)` を実装し、以下の式でオドメトリを更新する。
        *   `self.theta += self.cmd_w * dt`
        *   `self.x += self.cmd_v * np.cos(self.theta) * dt`
        *   `self.y += self.cmd_v * np.sin(self.theta) * dt`

### 3-2. `simulation/visualizer.py`
Panda3Dの3DビューをROS 2に連携するための画像出力インターフェースを追加する。

*   **`get_camera_image()` メソッドの追加と型安全ガード**:
    *   `self.win.getDisplayRegion(0).getScreenshot()` を用いて現在の描画バッファを取得。
    *   **ぬるぽ/初期化ガード:** 画面初期化直後の `tex is None` や `ConstPointerToArray` の要素数 `len(data) == 0` を判定し、安全に `None` を返却する。
    *   取得したピクセルデータを `numpy` 配列の BGR 画像 `(height, width, 3)` に変換して返却する。

### 3-3. `simulation/main.py`
シミュレータのメインループにROS 2ノードの処理を相乗りさせる。

*   **ROS 2初期化**:
    *   `rclpy.init()` を実行。
    *   `/camera/image_raw` 用のパブリッシャと `CvBridge` を初期化。
*   **`simulation_task` の改修**:
    *   既存の配列インデックス (`frame_index`) に依存する処理やループ終了判定を全削除。
    *   `rclpy.spin_once(robot, timeout_sec=0)` を実行し、`/cmd_vel` の受信をさばく。
    *   `robot.update_physics(config.SIMULATION_DT)` を実行して物理状態を更新。
    *   `visualizer.get_camera_image()` で画像を取得し、`cv_bridge` 経由でROSメッセージに変換して `/camera/image_raw` にパブリッシュする。

### 3-4. `course_lap_node.py` (src/raphael_enterprise/raphael_enterprise/)
受信した画像を解析し、制御量を計算してパブリッシュする。同時にデバッグHUD画面を表示する。

*   **初期設定 (`__init__`)**:
    *   `/camera/image_raw` をサブスクライブし、`/cmd_vel` をパブリッシュ。
    *   `self.state = State.STRAIGHT` を初期ステートとする。
*   **画像コールバック (`image_callback`) とHUD可視化**:
    *   `cv_image.copy()` でデバッグ描画用キャンバス (`debug_img`) を作成。
    *   **① 安全装置 (緑ROI)**:
        *   対象領域: 画面下部30%（Y=450〜640等）。`cv2.rectangle` で赤枠と文字を描画。
        *   処理: 緑面積が15%超過で `State.EMERGENCY` へ。Twist(0,0) を発行し以降をブロック。
    *   **② カーブ予測 (白ROI)**:
        *   対象領域: 画面上部（Y=200〜400等）。青枠と文字を描画。
        *   処理: 白線の傾き/奥の黒路面の偏りからカーブ進入を検知し、`PRE_CURVE`, `TURNING`, `STRAIGHT` を遷移させる。
    *   **③ 軌道追従 (黒ROI) と動的オフセット**:
        *   対象領域: 画面中下部（Y=400〜640等）。黄枠と文字を描画。
        *   処理: 黒の重心 `(Cx, Cy)` を算出。キャンバスに**赤ドット**を描画。
        *   目標X座標 (`TargetX`) の計算: `STRAIGHT`時は中心+アウトオフセット、`CURVE`時は中心+インオフセット。キャンバスに**緑縦線**を描画。
        *   PID制御: `error = TargetX - Cx` より `angular.z` を算出。
    *   **状態描画と出力**:
        *   画面左上に現在の `self.state` の文字列をオーバーレイ描画。
        *   `cv2.imshow("Raphael Racing - Debug View", debug_img)` と `cv2.waitKey(1)` を実行し、リアルタイム表示する。

---

## 4. データ・制御の処理フロー

本システム統合による毎フレーム（`config.SIMULATION_DT` ごと）のデータ循環サイクルは以下の通り。

```text
【Simulation Loop】 (simulation/main.py 内 Panda3D Task)
  │
  ├─ 1. rclpy.spin_once(robot)      ──► /cmd_vel を受信し、robotインスタンス内部の速度変数を更新
  ├─ 2. robot.update_physics(dt)    ──► 更新された速度で自機オドメトリ(x, y, theta)を演算
  ├─ 3. visualizerのモデル座標更新     ──► 3D空間のカメラとロボットモデルの姿勢を同期・再描画
  │
  └─ 4. visualizer.get_camera_image()
        │
        └─► OpenCV BGR画像化 ─(cv_bridge)─► /camera/image_raw トピックとしてPublish


【Racing AI Node】 (course_lap_node.py)
  │
  └─► /camera/image_raw をSubscribe
        │
        ├─► デバッグ用キャンバス作成 (HUD表示用)
        │
        ├─► [赤枠ROI] 下部の緑抽出 ─(Over 15%)─► EMERGENCY移行 (Twist(0,0) Publish)
        │
        ├─► [青枠ROI] 上部の白抽出 ─► カーブ検知によるステート遷移 (STRAIGHT / PRE_CURVE)
        │
        ├─► [黄枠ROI] 路面の黒重心抽出 (Cx) ──► 目標TargetXの決定 ──► PID演算
        │
        ├─► Twist(速度, Z角速度) を /cmd_vel トピックとしてPublish
        │
        └─► HUDオーバーレイ描画 (赤ドット重心, 緑目標ライン, ステート文字列)
              └─► cv2.imshow でデバッグウィンドウにリアルタイム表示
```