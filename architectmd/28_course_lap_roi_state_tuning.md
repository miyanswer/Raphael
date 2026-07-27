# ARCH_TITLE: course_lap_roi_state_tuning

## 1. システム概要と決定された採用技術

### システム概要
本設計は、ビジュアルレーシングナビゲーションノード（`course_lap_node.py`）において「カーブを誤検知し、直線区間でも常に減速（TURNING状態）してしまう」という不具合を解消するための改修設計である。
画像処理における「先読み（カーブ検知）用ROI」と「ビジュアルサーボ（ステアリング制御）用ROI」の参照範囲（見る幅）を高さ方向に分割・最適化し、遠景のノイズを排除する。
さらに、状態遷移（STRAIGHT ↔ TURNING）の判定閾値を緩和することで、確実なカーブ進入時のみスローインし、直線の立ち上がりで速やかにファストアウト（加速）するスムーズな自律走行を実現する。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| フレームワーク | ROS 2 (rclpy) |
| 画像処理 | OpenCV (`cv2`), Numpy, `cv_bridge` |
| メッセージ型 | `sensor_msgs/Image`, `geometry_msgs/Twist` |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

物理的なフォルダ構造の追加・削除は発生しない。AIノードのロジックファイル1点を修正する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py   # ★修正: ROIの分割・最適化、状態遷移の閾値緩和
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | 画像のクロップ範囲（ROI）を先読み用とサーボ用で明確に分割。白線の左右バランスに基づく状態遷移（STRAIGHT ↔ TURNING）の閾値を調整・緩和。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `raphael_enterprise/course_lap_node.py` (AI自律走行ノード)

画像コールバック内で画像をクロップする処理、および状態遷移を判定するロジックを以下のように改修する。

*   **【★修正1】画像クロップ範囲（ROI）の最適化**
    取得したカメラ画像（高さ `h`, 幅 `w`）に対して、目的別にクロップ領域を分割する。
    1.  **先読み（カーブ検知）用ROI:**
        遠景やノイズを排除するため、画像中段のみを抽出する。
        *   `y_start = int(h * 0.40)`
        *   `y_end = int(h * 0.60)`
    2.  **ビジュアルサーボ（重心算出）用ROI:**
        ステアリング操作のための黒路面抽出。最下部の芝生（緊急停止用）とは分離する。
        *   `y_start = int(h * 0.50)`
        *   `y_end = int(h * 0.85)`
    3.  **緊急停止（芝生検知）用ROI:** （既存機能の調整・維持）
        *   `y_start = int(h * 0.85)`
        *   `y_end = h`

*   **【★修正2】状態遷移の閾値緩和（STRAIGHT ↔ TURNING）**
    先読み用ROIにおける白線（`WHITE_V_MIN`以上）の分布を用いてカーブを判定する際、閾値を調整する。
    *   **左右バランスの計算:**
        先読みROIを左右に2分割（`w/2` を境界）し、左側の白線ピクセル数 `white_left` と右側の白線ピクセル数 `white_right` をカウント。
    *   **TURNINGへの遷移条件（厳格化）:**
        現在の状態が `STRAIGHT` または `PRE_CURVE` の時、`white_left` と `white_right` の差分（あるいは比率）が**「極めて大きい（明確に曲がっている）」**場合のみ `TURNING` へ遷移させる。
        *(例: `abs(white_left - white_right) > 閾値_大`)*
    *   **STRAIGHTへの復帰条件（緩和）:**
        現在の状態が `TURNING` の時、左右の白線バランスの差分が**「ある程度（許容マージン大）収まった」**時点で、速やかに `STRAIGHT` へ復帰させる。
        *(例: `abs(white_left - white_right) < 閾値_小`)*

*   **【★修正3】速度と目標オフセットの適用**
    状態に応じた走行制御パラメーター（既存定義の定数）を確実に適用する。
    *   `STRAIGHT`: `speed = SPEED_FAST (0.6)`, `offset = OFFSET_OUT`
    *   `TURNING`: `speed = SPEED_SLOW (0.25)`, `offset = OFFSET_IN`
    *   サーボ用ROIから算出した黒路面の重心X座標に対して上記 `offset` を加味し、画面中央（`w/2`）との誤差から `P-D制御` でステアリング角速度（`angular.z`）を決定する。

---

## 4. データ・制御の処理フロー

本改修を適用した後の、AIノード内の毎フレームの画像処理と制御フローは以下の通りとなる。

```text
1. [Image Receive] /camera/image_raw トピックから画像を受信。
   └─ CvBridgeでNumpy配列(BGR)に変換し、HSV色空間へ変換。

2. [ROI Splitting] 画像を高さ方向(y)で3つの領域に分割。
   ├─ 先読みROI (40% 〜 60%)
   ├─ サーボROI (50% 〜 85%)
   └─ 緊急停止ROI (85% 〜 100%)

3. [Emergency Check]
   └─ 緊急停止ROI内で緑色(芝生)ピクセル割合を計算。閾値超過なら即時 EMERGENCY 状態へ遷移＆停止。

4. [Curve Detection & State Update] 先読みROIの評価
   ├─ 先読みROI内で白色ピクセルを抽出し、画面左半分と右半分のピクセル数を比較。
   ├─ 差分が「大」なら TURNING へ遷移 (スローイン)。
   └─ 差分が「小」なら STRAIGHT へ復帰 (ファストアウト)。

5. [Visual Servo] サーボROIの評価
   ├─ サーボROI内で黒色ピクセルを抽出し、重心座標 (cx, cy) を算出。
   ├─ 現在のStateに応じた OFFSET (OFFSET_OUT または OFFSET_IN) を cx に加算し、目標座標を決定。
   └─ 画面中心(w/2)と目標座標の誤差に PD制御 を適用し、角速度(cmd_w)を算出。

6. [Command Publish]
   └─ 決定された cmd_v (SPEED_FAST or SPEED_SLOW) と cmd_w を Twist メッセージとして /cmd_vel にパブリッシュ。
```