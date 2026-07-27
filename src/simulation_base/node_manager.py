import os
import csv
import numpy as np
from simulation import config

NODE_SEQUENCE = [
    "N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08",
    "N09", "N10", "N11", "N12", "N13", "N14", "N15", "N16"
]

class NodeManager:
    def __init__(self, node_positions):
        self.node_positions = node_positions
        self.current_node_index = 1  # N02 (スタート地点)
        self.visit_count = {node_id: 0 for node_id in NODE_SEQUENCE}
        self.visit_count["N02"] = 1
        self.history = ["N02"]

    def update(self, robot_x, robot_y):
        """
        ロボットの現在位置から次のノードへの遷移を判定する（順序制約付き）。
        """
        next_index = (self.current_node_index + 1) % len(NODE_SEQUENCE)
        next_node_id = NODE_SEQUENCE[next_index]
        next_node_pos = self.node_positions[next_node_id]

        dist = np.sqrt((robot_x - next_node_pos[0])**2 + (robot_y - next_node_pos[1])**2)

        transitioned = False
        if dist < config.NODE_TRIGGER_DISTANCE:
            self.current_node_index = next_index
            self.visit_count[next_node_id] += 1
            self.history.append(next_node_id)
            transitioned = True

        current_id = NODE_SEQUENCE[self.current_node_index]
        return {
            "transitioned": transitioned,
            "current_node": current_id,
            "visit_count": self.visit_count[current_id]
        }

    def get_current_node_id(self):
        return NODE_SEQUENCE[self.current_node_index]

    def get_current_segment_id(self):
        """
        現在ノードIDから対応する区間ID (L1〜C4) を返す。
        N01,N02,N03 -> L1
        N03,N04,N05 -> C1
        N05,N06,N07 -> L2
        N07,N08,N09 -> C2
        N09,N10,N11 -> L3
        N11,N12,N13 -> C3
        N13,N14,N15 -> L4
        N15,N16,N01 -> C4
        """
        curr = self.get_current_node_id()
        mapping = {
            "N01": "L1", "N02": "L1",
            "N03": "C1", "N04": "C1",
            "N05": "L2", "N06": "L2",
            "N07": "C2", "N08": "C2",
            "N09": "L3", "N10": "L3",
            "N11": "C3", "N12": "C3",
            "N13": "L4", "N14": "L4",
            "N15": "C4", "N16": "C4"
        }
        return mapping.get(curr, "L1")

    def is_lap_completed(self):
        """
        N01（またはスタート地点の再通過）により周回が完了したか判定する。
        visit_count["N01"] >= 2、あるいは N02 の2回目通過などで判定。
        一般的には N01 通過時、または 16ノード全通過後の N01/N02 到着。
        """
        return self.visit_count["N01"] >= 2 or (self.visit_count["N01"] >= 1 and self.visit_count["N02"] >= 2)

    def export_log(self, filepath):
        """
        ログファイルに通過履歴を出力する。
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "node_id", "visit_count"])
            for idx, node_id in enumerate(self.history):
                writer.writerow([idx, node_id, self.visit_count[node_id]])
