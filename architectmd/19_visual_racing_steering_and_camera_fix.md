# ARCH_TITLE: visual_racing_steering_and_camera_fix

## 1. システム概要と決定された採用技術

### システム概要
本設計は、画像ベースで自律走行を行うビジュアルレーシングAIにおいて発生している「開始直後に左旋回し、芝生を検知して緊急停止する不具合」を解消するための修正設計書である。
ステアリングの極性（左右）が逆転している問題を解決するため、制御の基準（誤差計算）を「画面中心」に統一し、直感的な相対座標系へと修正する。同時に、シミュレータのカメラ視点を機体中心からバンパー先端（前方0.4m）へオフセットし、旋回時の不要な視点ブレや芝生検知を防止する。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| 3Dシミュレータ | Panda3D |
| 行列演算・三角関数 | `numpy`, `math` |
| ROS 2通信・画像変換 | `rclpy`, `geometry_msgs/Twist`, `sensor_msgs/Image`, `cv_bridge` |
| 画像処理 | `OpenCV` (`cv2`) |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理的なファイル・フォルダ構成に追加・削除は発生しない。AI制御ノードとシミュレータ描画クラスの内部ロジックを以下の通りピンポイントで修正する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正: ステアリング誤差(error)の算出ロジック変更
  📁 simulation/
    📄 visualizer.py              # ★修正: カメラ位置の機体前方オフセット処理追加
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | 誤差(`error`)の算出式を `(画像中心) - TargetX` に変更し、ステアリング制御の極性をROS 2の仕様（マイナス＝右旋回）に適合させる。 |
| `visualizer.py` | `update_camera` 内でカメラのXY座標を、ロボットの中心から向いている角度(`theta`)へ0.4m前方に移動させる。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py` (AI制御側)
ステアリング制御量を計算する処理において、目標座標（`TargetX`）から誤差（`error`）を算出するロジックを修正する。

*   **【★修正】画面中心を基準としたPID誤差（`error`）の計算**:
    *   画面の横幅（`IMAGE_WIDTH`）を 640px と想定し、機体の真正面（画像中心）を 320px に設定する。
    *   誤差算出式を以下のように引き算の順序を修正する。
        ```python
        # 画像の中心座標 (機体の正面)
        center_x = 320.0  # IMAGE_WIDTH / 2.0
        
        # 正面座標と目標座標のズレを誤差とする
        error = center_x - TargetX
        ```
    *   **仕様の意図**: 
        目標(`TargetX`)が画面中心より右側にある場合（例：TargetX = 400）、`320.0 - 400.0 = -80.0`（負の値）となる。ROS 2の `Twist.angular.z` において「マイナス」は**右旋回**を意味するため、機体が正しく目標へ向かってステアリングを切るようになる。

### 3-2. `visualizer.py` (シミュレータ側)
シミュレータのカメラ視点を更新する `update_camera(self, robot_x, robot_y, robot_theta)` メソッドにおいて、カメラ位置の計算ロジックを修正する。

*   **【★修正】カメラ位置（X, Y）の前方オフセット計算**:
    *   引数で渡される `robot_x`, `robot_y` をそのままカメラ位置にするのではなく、ロボットの向いている角度 `robot_theta` を利用して `0.4` メートル前方（バンパー先端位置）へズラす。
    *   `math`（または `numpy`）を用いて以下のように計算を実装する。
        ```python
        import math
        
        cam_offset = 0.4
        cam_x = robot_x + (cam_offset * math.cos(robot_theta))
        cam_y = robot_y + (cam_offset * math.sin(robot_theta))
        ```
    *   算出された `cam_x`, `cam_y` と、既存のカメラ高さ（Z座標）を用いて、Panda3Dのカメラノード（`self.camera.setPos` または `base.camera.setPos`）を更新する。

---

## 4. データ・制御の処理フロー

本修正により、物理世界（シミュレータ視点）と認識世界（AI制御）の整合性が取れ、コースに沿った安定走行が実現する。

```text
【毎フレームのシミュレーション＆制御サイクル】

1. [Simulator: visualizer.py] 機体の状態更新とカメラ視点配置
   ├─ ロボットの中心(x, y)と角度(theta)を取得
   └─ theta方向に0.4m進めたバンパー先端(cam_x, cam_y)にカメラをセット

2. [Simulator: main.py] FPV画像の配信
   └─ 前方にオフセットされたブレの少ない画像を /camera/image_raw に Publish

3. [AI Node: course_lap_node.py] 画像受信と目標決定
   ├─ 画像を受信し、黒路面の重心(Cx)を特定
   └─ ステートに応じたオフセットを加味し、目標ピクセル(TargetX)を決定

4. [AI Node: course_lap_node.py] 画面中心基準のステアリング演算（極性修正）
   ├─ TargetX が右側 (例: 400px) の場合
   │  └─ error = 320 - 400 = -80 (負の値) ──► angular.z = 負の値 (右旋回)
   │
   ├─ TargetX が左側 (例: 240px) の場合
   │  └─ error = 320 - 240 = +80 (正の値) ──► angular.z = 正の値 (左旋回)
   │
   └─ 算出された /cmd_vel を Publish して機体を正しく制御
```