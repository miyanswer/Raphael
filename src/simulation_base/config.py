import os

# 【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 14.79},
    {"id": "C1", "type": "arc",      "radius": 15.0, "angle_deg":  60, "direction": "left"},
    {"id": "L2", "type": "straight", "length": 40.41},
    {"id": "C2", "type": "arc",      "radius": 15.0, "angle_deg": 120, "direction": "left"},
    {"id": "L3", "type": "straight", "length": 35.0},
    {"id": "C3", "type": "arc",      "radius": 15.0, "angle_deg":  90, "direction": "left"},
    {"id": "L4", "type": "straight", "length": 35.0},
    {"id": "C4", "type": "arc",      "radius": 15.0, "angle_deg":  90, "direction": "left"},
]

# 【ロボットパラメータ】
ROBOT_WHEEL_BASE = 0.8         # 左右輪間距離 [m]
ROBOT_SPEED = 0.5              # 走行速度 [m/s]
SIMULATION_DT = 0.05           # 時間刻み [s]（=20Hz相当）

# 【コース幅パラメータ】
COURSE_WIDTH = 7.0             # コース全幅 [m]（中心線から左右3.5mずつ）

# 【描画パラメータ】
FPS = 30                       # アニメーションフレームレート
COURSE_LINE_COLOR = "black"
COURSE_LINE_WIDTH = 2
ROBOT_COLOR = "royalblue"
ROBOT_ARROW_COLOR = "red"
NODE_MARKER_COLOR = "orange"
NODE_FONT_SIZE = 8

# 路面テクスチャ色定数（今バージョン追加）
ROAD_COLOR         = "black"      # 黒路面の塗り色
ROAD_LINE_COLOR    = "white"      # 白線3本の色（外側・中心・内側）
ROAD_LINE_WIDTH    = 2            # 白線の線幅 [pt]
CENTER_LINE_STYLE  = "--"         # 中心白線は破線
GRASS_COLOR        = "green"      # コース外の芝（背景色）

# 境界線スムージングパラメータ（今バージョン追加）
BOUNDARY_SMOOTH_WINDOW = 50   # 法線移動平均の窓幅 [点数]

# 【ノード認識パラメータ】
NODE_TRIGGER_DISTANCE = 0.5    # ノードとみなす距離閾値 [m]
COURSE_CLOSE_TOLERANCE = 1.0   # コース閉じ判定許容距離 [m]

# 【カメラシミュレータパラメータ】
NOISE_STD = 0.05               # ガウスノイズ標準偏差

# 【ログパラメータ】
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILENAME = "run_log.csv"

