import pytest
from simulation.course import CourseGenerator
from simulation.node_manager import NodeManager
from simulation import config

def test_sequential_transition():
    cg = CourseGenerator(config.SEGMENTS)
    node_positions = cg.generate_node_positions()
    nm = NodeManager(node_positions)

    # 初期ノードは N02
    assert nm.get_current_node_id() == "N02"

    # 次の N03 の座標にロボットを移動
    pos_n03 = node_positions["N03"]
    res = nm.update(pos_n03[0], pos_n03[1])

    assert res["transitioned"] is True
    assert nm.get_current_node_id() == "N03"

def test_no_skip_transition():
    cg = CourseGenerator(config.SEGMENTS)
    node_positions = cg.generate_node_positions()
    nm = NodeManager(node_positions)

    assert nm.get_current_node_id() == "N02"

    # N02 の次である N03 を飛ばして N04 に移動しても遷移しない
    pos_n04 = node_positions["N04"]
    res = nm.update(pos_n04[0], pos_n04[1])

    assert res["transitioned"] is False
    assert nm.get_current_node_id() == "N02"

def test_lap_completion():
    cg = CourseGenerator(config.SEGMENTS)
    node_positions = cg.generate_node_positions()
    nm = NodeManager(node_positions)

    # N02 スタートから全ノードを順に移動
    sequence = ["N03", "N04", "N05", "N06", "N07", "N08", "N09", "N10", "N11", "N12", "N13", "N14", "N15", "N16", "N01", "N02"]
    for node_id in sequence:
        pos = node_positions[node_id]
        nm.update(pos[0], pos[1])

    assert nm.is_lap_completed() is True
