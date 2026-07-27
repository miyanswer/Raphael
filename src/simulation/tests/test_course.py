import pytest
import numpy as np
from simulation.course import CourseGenerator
from simulation import config

def test_course_is_closed():
    cg = CourseGenerator(config.SEGMENTS)
    points = cg.generate_course_points()
    assert len(points) > 0
    assert points.shape[1] == 2

    start = points[0]
    end = points[-1]
    distance = np.linalg.norm(end - start)

    assert distance < config.COURSE_CLOSE_TOLERANCE, (
        f"コースが閉じていません: 始点-終点間距離 = {distance:.4f}m "
        f"(許容値: {config.COURSE_CLOSE_TOLERANCE}m)\n"
        f"始点: {start}, 終点: {end}"
    )

def test_node_count():
    cg = CourseGenerator(config.SEGMENTS)
    node_positions = cg.generate_node_positions()
    assert len(node_positions) == 16
    for i in range(1, 17):
        node_id = f"N{i:02d}"
        assert node_id in node_positions
