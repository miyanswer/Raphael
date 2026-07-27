# ARCH_TITLE: visual_racing_polyfit_4point_curve_offset

## 1. システム概要と決定された採用技術

### システム概要
本設計は、自動運転AI（ビジュアルレーシングAI）の安定性と高速走行時のレスポンスを極限まで高めるための改修である。
軌道追従（Pure Pursuit）において、足元から遠方までの4点を用いた2次関数近似（Polyfit）を導入し、急なブレのない実車に近い滑らかなステアリング制御を実現する。また、白線の状態に依存しない「路面重心のズレ」を用いたカーブ検知ロジックを採用することで、計算負荷を抑えつつ高速走行時でもタイムラグのない減速ステート切り替えを可能とする。

### 決定された採用技術
| 項目 | 採用技術・手法 |
|------|--------------|
| スキャンライン設定（計5本） | カーブ検知用(0.55) 1本、軌道追従用(0.90, 0.75, 0.65, 0.57) 4本 |
| カーブ検知・状態遷移 | 0.55ラインの路面重心が画面中央から「画面幅の15%」以上ズレた場合に `PRE_CURVE`（減速）へ状態遷移させる高速判定ロジック（案B） |
| 曲線フィッティング (4点) | 足元(0.90)から先読み(0.57)までの4点を用い `numpy.polyfit(Y, X, 2)` で2次関数（$X = aY^2 + bY + c$）を算出 |
| 目標軌道算出・制御 | 算出した2次関数から追従目標点 `target_x` を逆算し、PID制御によりステアリング角速度を決定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ファイルの新規追加・削除・配置変更は発生しない。既存ノードのロジックのみを更新する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正: 定数変更、ズレ判定カーブ検知、4点Polyfit軌道追従の実装
```

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py`
ビジュアルサーボ制御における定数を更新し、カーブ検知ロジックおよびステアリング算出ロジックを刷新する。

*   **制御パラメータ・定数の変更・追加**
    *   **カーブ検知用**
        *   `SCAN_Y_CURVE_RATIO = 0.55` （既存の 0.50 から変更）
        *   `CURVE_OFFSET_THRESHOLD_RATIO = 0.15` （新規追加: 画面幅の15%）
    *   **軌道追従（Polyfit 4ライン）用**
        *   `SCAN_Y_FAR_STEER_RATIO = 0.57` （最遠方: 旧 0.60 から変更）
        *   `SCAN_Y_MID_STEER_RATIO = 0.65` （中間: 維持）
        *   `SCAN_Y_NEAR_STEER_RATIO = 0.75` （近景: 維持）
        *   `SCAN_Y_BOTTOM_STEER_RATIO = 0.90` （新規追加: 足元）
    *   **追従基準Y位置**
        *   `TRACKING_TARGET_Y_RATIO = 0.625` （維持）

*   **カーブ検知と状態遷移ロジック（Image Callback内）**
    1.  `Y = height * 0.55` のライン上で黒色（路面）ピクセルを抽出し、重心X座標 `curve_center_x` を算出する。
    2.  画面中央と重心の差分（ズレ）を計算: `offset = abs(curve_center_x - (width / 2.0))`
    3.  `offset > (width * CURVE_OFFSET_THRESHOLD_RATIO)` の場合、カーブが迫っていると判定しステートを `PRE_CURVE`（減速）へ切り替える。
    4.  閾値を下回る（ズレが収まる）場合は、直線と判定しステートを `STRAIGHT`（高速）へ切り替える（緊急停止状態 `EMERGENCY` を除く）。

*   **2次関数近似（4点 Polyfit）による `target_x` の算出**
    1.  `0.90`, `0.75`, `0.65`, `0.57` の4つのY座標ラインについて、それぞれ黒色路面の重心X座標を抽出する。
    2.  抽出した4点の画像上のY座標（ピクセル値）と、算出された重心X座標を配列化する。
        *   `Y_array = np.array([height * 0.90, height * 0.75, height * 0.65, height * 0.57])`
        *   `X_array = np.array([center_bottom_x, center_near_x, center_mid_x, center_far_x])`
    3.  `np.polyfit(Y_array, X_array, 2)` を実行し、2次関数の係数 `(a, b, c)` を取得する。
    4.  追従の基準となるY座標（`y_ref = height * TRACKING_TARGET_Y_RATIO`）を定義する。
    5.  取得した係数を用いて、滑らかな軌道上の目標点 `target_x` を逆算する。
        *   `target_x = a * (y_ref**2) + b * y_ref + c`

*   **速度およびステアリング出力（PID制御）**
    *   状態遷移の結果に基づき、目標速度（`SPEED_FAST` または `SPEED_SLOW`）を設定。
    *   目標点とのズレ `error = (width / 2.0) - target_x` を計算。
    *   既存のPID計算を用いて `error` を角速度 `cmd_vel.angular.z` へ変換し Publish する。

---

## 4. データ・制御の処理フロー

```text
【Polyfit 4点曲線軌道 ＆ 高速カーブ検知 フロー（毎フレーム）】

1. [Image Acquisition]
   └─ カメラ画像取得およびHSV空間変換、黒色（路面）抽出用2値化マスクの生成。

2. [Curve Detection & Speed Control] 高速レスポンス・カーブ検知
   ├─ Y = height * 0.55 のスキャンラインから路面重心(curve_center_x)を算出。
   ├─ ズレ計算: offset = abs(curve_center_x - (width / 2.0))
   ├─ offset > (width * 0.15) ならばステートを [PRE_CURVE] へ遷移 (目標速度: SPEED_SLOW)
   └─ 閾値以下ならばステートを [STRAIGHT] へ遷移 (目標速度: SPEED_FAST)

3. [Steering Trajectory Calculation] 4点2次関数近似
   ├─ Y = height * 0.90 (足元) の路面重心Xを算出。
   ├─ Y = height * 0.75 (近景) の路面重心Xを算出。
   ├─ Y = height * 0.65 (中間) の路面重心Xを算出。
   ├─ Y = height * 0.57 (遠方) の路面重心Xを算出。
   ├─ Y座標4点とX座標4点を元に np.polyfit(Y_array, X_array, 2) を実行し、係数(a,b,c)を取得。
   └─ 基準Y(height * 0.625)を2次関数に代入し、滑らかな軌道上の target_x を逆算。

4. [Error Calculation & PID]
   ├─ ステアリング誤差: error = (width / 2.0) - target_x
   └─ PID制御により error を角速度コマンド (cmd_vel.angular.z) へ変換。

5. [Command Publish]
   └─ 最新の速度・角速度コマンドをシミュレータのロボットへ送信。
```