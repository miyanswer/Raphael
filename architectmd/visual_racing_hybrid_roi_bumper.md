# ARCH_TITLE: visual_racing_hybrid_roi_bumper

## 1. システム概要と決定された採用技術

### システム概要
本設計は、ビジュアルレーシングAIノード（`course_lap_node.py`）において発生している以下の2つの課題を解決するための改修設計である。

1. **イン側の白線踏み越え（芝生突入）**：アウト・イン・アウトの軌道を狙うイン寄せ（`OFFSET_IN = -20`）の際、内側に寄りすぎて左の白線を踏んでしまう。
2. **カーブ出口の蛇行**：カーブ終了時の急激な目標値変化に対してステアリングの制動が効かず、車体が左右に揺れてしまう。

これらの課題に対し、**「ハイブリッドROI（先読み重心と足元重心の分離）」**と**「仮想バンパーロジック」**、および**「微分ゲイン（KD）の強化」**を導入する。これにより、普段は先読み視点でインを攻めつつ、足元が白線を越えそうになった瞬間だけ安全な位置（アウト側）へ強制的に弾き返す、ロバストなレーシング制御を実現する。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| フレームワーク | ROS 2 (rclpy) |
| 画像処理 | OpenCV (`cv2`), `cv_bridge` |
| メッセージ型 | `geometry_msgs/Twist`, `sensor_msgs/Image` |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理的なファイル・フォルダ構成に対する追加・削除は発生しない。既存のノードに対してピンポイントでの修正を実施する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正: ハイブリッドROI、仮想バンパー、KDゲインの調整
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | PIDパラメータ `STEER_KD` の強化。先読みROIの範囲変更および足元ROIの追加。仮想バンパーによる TargetX の補正ロジック追加。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py` (AI制御ノード)

*   **【★修正1】ステアリング微分ゲイン（KD）の強化**
    ファイル上部のレーシング制御パラメータを変更し、ステアリングの戻しに対する制動力（ダンパー）を強め、蛇行を抑制する。
    *   `STEER_KD = 0.001` → **`STEER_KD = 0.004`** に変更。
    *   ※ `OFFSET_IN` は `-20`、`OFFSET_OUT` は `20` のまま維持。

*   **【★修正2】ハイブリッドROI（2つの重心算出）**
    画像処理コールバック内の重心計算ロジックを改修し、黒色路面（`black_mask`）から「先読み用」と「足元用」の2つの重心を個別に算出する。
    ```python
    # 画像の高さと幅を動的に取得
    h, w = cv_image.shape[:2]
    
    # --- 1. 先読みROI（イン攻め用） ---
    lookahead_top = int(h * 0.25)
    lookahead_bottom = int(h * 0.70)  # 65%から70%へ拡張
    lookahead_mask = black_mask.copy()
    lookahead_mask[:lookahead_top, :] = 0
    lookahead_mask[lookahead_bottom:, :] = 0
    
    M_look = cv2.moments(lookahead_mask)
    Lookahead_Cx = int(M_look["m10"] / M_look["m00"]) if M_look["m00"] > 0 else (w / 2.0)

    # --- 2. 足元ROI（安全バンパー用） ---
    foot_top = int(h * 0.70)
    foot_bottom = h
    foot_mask = black_mask.copy()
    foot_mask[:foot_top, :] = 0
    foot_mask[foot_bottom:, :] = 0
    
    M_foot = cv2.moments(foot_mask)
    Foot_Cx = int(M_foot["m10"] / M_foot["m00"]) if M_foot["m00"] > 0 else (w / 2.0)
    ```

*   **【★修正3】仮想バンパー（白線踏み越え防止）ロジックの追加**
    目標座標（`TargetX`）を計算するロジックにおいて、`Lookahead_Cx`を基準にオフセットを加算した後、`Foot_Cx`を用いた安全ガードをかける。
    ```python
    # ベースの目標値算出 (例: カーブ時なら Lookahead_Cx - 20)
    # ※ ステートに応じたOffset加算ロジックは既存のものを流用
    TargetX = Lookahead_Cx + current_offset 
    
    # 仮想バンパーの発動
    # 足元の黒色路面重心が画面中央より右（> w/2.0）ということは、左側の白線が中心に迫っている危険な状態
    if Foot_Cx > (w / 2.0):
        # イン（左側: 座標が小さい方向）に寄りすぎないよう、目標値を右側へ強制補正
        TargetX = max(TargetX, Foot_Cx)
        
    # 誤差の計算（必ず動的な w/2.0 を使用）
    center_x = w / 2.0
    error = center_x - TargetX
    ```

---

## 4. データ・制御の処理フロー

改修適用後の、1フレームあたりの正しいデータ処理と制御フローは以下の通りとなる。

```text
【毎フレームのビジュアルレーシング制御フロー】

1. [Image Callback] 画像取得
   └─ /camera/image_raw を受信し、hとwを動的取得

2. [Safety Check] 芝生検知による緊急停止判定
   └─ 足元の緑色ピクセル割合を監視（既存維持）

3. [Hybrid ROI Processing] 2つの重心の算出
   ├─ 先読みROI (25%〜70%): 遠くのコース重心 Lookahead_Cx を算出
   └─ 足元ROI (70%〜100%): 足元のコース重心 Foot_Cx を算出

4. [State & Target Calculation] 目標座標の決定と仮想バンパー
   ├─ 形状特徴からカーブを検知し、ステート（STRAIGHT / TURNING 等）を決定
   ├─ 先読み重心に対して、ステートに応じたオフセットを加算 (TargetX = Lookahead_Cx + Offset)
   ├─ 【仮想バンパー】 足元重心(Foot_Cx)が中央より右にズレていれば、TargetX = max(TargetX, Foot_Cx) で右に逃がす
   └─ error = (w / 2.0) - TargetX を算出

5. [PID Control & Action] 制御出力
   ├─ error を用いてステアリング角速度(w)をPID演算 (STEER_KD=0.004 を使用し振動を素早く減衰)
   └─ 算出された Twist を /cmd_vel へ Publish (デバッグ描画時は target_x/cx を int キャストして型エラーを防止)
```