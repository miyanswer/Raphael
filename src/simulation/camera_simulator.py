import numpy as np
from simulation import config

class CameraSimulator:
    def __init__(self, seed=42):
        if seed is not None:
            np.random.seed(seed)

    def get_features(self, current_segment_id, course_generator):
        """
        現在の区間IDとCourseGeneratorから仮想カメラ特徴量を生成する。
        ガウスノイズを加算。
        """
        base_curvature = course_generator.get_segment_curvature(current_segment_id)

        if base_curvature == 0.0:
            asymmetry = 0.0
            convergence = 1.0
        else:
            asymmetry = float(np.clip(base_curvature * 0.5, 0.0, 1.0))
            convergence = float(np.clip(1.0 - base_curvature * 0.5, 0.0, 1.0))

        noise_std = config.NOISE_STD
        curvature_noise = np.random.normal(0, noise_std)
        asymmetry_noise = np.random.normal(0, noise_std)
        convergence_noise = np.random.normal(0, noise_std)

        curvature_estimate = float(base_curvature + curvature_noise)
        line_asymmetry = float(np.clip(asymmetry + asymmetry_noise, -1.0, 1.0))
        line_convergence = float(np.clip(convergence + convergence_noise, 0.0, 1.0))

        return {
            "curvature": curvature_estimate,
            "asymmetry": line_asymmetry,
            "convergence": line_convergence
        }
