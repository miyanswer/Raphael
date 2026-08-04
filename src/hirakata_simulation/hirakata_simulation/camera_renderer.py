#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3D描画・カメラ画像生成モジュール (Panda3D / Offscreen Buffer)
- 床面サイズ: 幅 31m (X: -15.5〜+15.5), 奥行き 19m (Y: -9.5〜+9.5)
- 白線コース位置: グレー床の真中央 (0, 0) (左右余白 各8.0m, 上下余白 各4.5m)
- 床面メッシュ: 回転・オフセット歪みを完全に排除するため直接頂点定義 (Z=0.0)
- 車載カメラ (FPV): 高さ 40cm (Z=+0.4m), 俯角 0度 (Pitch=0), 解像度 640x480 (30 FPS)
- 鳥瞰図カメラ (Bird's Eye): 直交射影(Orthographic)・上空固定視点 (0, 0, 30), 解像度 640x480 (カラー・追従なし)
- バッファ独立化 (makeTextureBuffer) によりカメラ間の混ざり・映り込みを完全解消
- 両面描画設定 (setTwoSided) により白線メッシュカリング欠落を防護
"""

import math
import numpy as np
import cv2
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, Vec4, Vec3, WindowProperties, LPoint3f,
    Geom, GeomNode, GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles,
    Texture, GraphicsOutput, PerspectiveLens, OrthographicLens, loadPrcFileData
)

from hirakata_simulation import course_generator

class CameraRenderer:
    def __init__(self, width=640, height=480, fov=90.0):
        self.width = width
        self.height = height
        self.fov = fov

        # Panda3D オフスクリーン解像度設定 (640x480)
        loadPrcFileData('', f'win-size {self.width} {self.height}')

        # Panda3D Offscreen / Headless Setup
        self.base = ShowBase(windowType='offscreen')

        # デフォルトのメインカメラを無効化（二重描画・画像混ざり防止）
        self.base.cam.node().setActive(False)

        # クリアカラー (遠景を暗色単色で塗りつぶし)
        self.base.win.setClearColor(Vec4(30 / 255.0, 30 / 255.0, 40 / 255.0, 1.0))

        # -------------------------------------------------------------
        # 1. 車載カメラ (FPV) 用独立バッファ & カメラ
        # -------------------------------------------------------------
        self.buf_fpv = self.base.win.makeTextureBuffer("buf_fpv", self.width, self.height)
        self.cam_fpv = self.base.makeCamera(self.buf_fpv)
        
        lens_fpv = PerspectiveLens()
        lens_fpv.setFov(self.fov)
        lens_fpv.setFilmSize(self.width, self.height)
        lens_fpv.setNearFar(0.05, 100.0)
        self.cam_fpv.node().setLens(lens_fpv)

        self.tex_fpv = Texture()
        self.buf_fpv.addRenderTexture(self.tex_fpv, GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor)

        # -------------------------------------------------------------
        # 2. 全体鳥瞰図カメラ (Bird's Eye) 用独立バッファ & 固定カメラ
        #  - 直交射影 (Orthographic) で歪みゼロの2D全体マップ表示
        # -------------------------------------------------------------
        self.buf_bird = self.base.win.makeTextureBuffer("buf_bird", self.width, self.height)
        self.cam_bird = self.base.makeCamera(self.buf_bird)

        lens_bird = OrthographicLens()
        # 幅 34m x 縦 25.5m (アスペクト比 4:3) で 31m x 19m のグレー床全体を正確に包摂
        self.bird_span_x = 34.0
        self.bird_span_y = 25.5
        lens_bird.setFilmSize(self.bird_span_x, self.bird_span_y)
        lens_bird.setNearFar(0.1, 100.0)
        self.cam_bird.node().setLens(lens_bird)

        # 鳥瞰カメラ設定: グレー床中央 (0, 0) の真上 30m に完全固定配置
        self.cam_bird.setPos(0.0, 0.0, 30.0)
        self.cam_bird.lookAt(LPoint3f(0.0, 0.0, 0.0), Vec3(0, 1, 0))

        self.tex_bird = Texture()
        self.buf_bird.addRenderTexture(self.tex_bird, GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor)

        # 均一環境光 (Unlit相当)
        ambient_light = AmbientLight('ambient_light')
        ambient_light.setColor(Vec4(1.0, 1.0, 1.0, 1.0))
        alnp = self.base.render.attachNewNode(ambient_light)
        self.base.render.setLight(alnp)

        # コースメッシュ構築
        self._build_scene()

    def _build_scene(self):
        """
        回転誤差ゼロの直接頂点定義による床面メッシュおよび白線コースメッシュの構築
        - 床面: 幅 31m (X: -15.5〜+15.5), 奥行き 19m (Y: -9.5〜+9.5), Z=0.0
        - 白線コース: 真中央 (X: -7.5〜+7.5, Y: -5.0〜+5.0), Z=0.005
        """
        # -------------------------------------------------------------
        # 1. 床面メッシュの直接構築 (回転歪み排除)
        # -------------------------------------------------------------
        vformat = GeomVertexFormat.getV3()
        vdata_floor = GeomVertexData('floor_data', vformat, Geom.UHStatic)
        vertex_floor = GeomVertexWriter(vdata_floor, 'vertex')

        # X: -15.5 ~ +15.5, Y: -9.5 ~ +9.5
        vertex_floor.addData3f(-15.5, -9.5, 0.0)
        vertex_floor.addData3f( 15.5, -9.5, 0.0)
        vertex_floor.addData3f( 15.5,  9.5, 0.0)
        vertex_floor.addData3f(-15.5,  9.5, 0.0)

        tris_floor = GeomTriangles(Geom.UHStatic)
        tris_floor.addVertex(0)
        tris_floor.addVertex(1)
        tris_floor.addVertex(2)

        tris_floor.addVertex(0)
        tris_floor.addVertex(2)
        tris_floor.addVertex(3)

        geom_floor = Geom(vdata_floor)
        geom_floor.addPrimitive(tris_floor)
        node_floor = GeomNode('floor_mesh_node')
        node_floor.addGeom(geom_floor)

        floor_node = self.base.render.attachNewNode(node_floor)
        fc = course_generator.FLOOR_COLOR
        floor_node.setColor(Vec4(fc[0], fc[1], fc[2], 1.0))
        floor_node.setTwoSided(True)

        # -------------------------------------------------------------
        # 2. 白線コースメッシュ構築 (幅 5cm, 段差ゼロ Z=0.005)
        # -------------------------------------------------------------
        points, normals = course_generator.generate_course_centerline_points(step_size=0.02)
        line_w = course_generator.LINE_WIDTH

        vdata_line = GeomVertexData('rounded_rect', vformat, Geom.UHStatic)
        vertex_line = GeomVertexWriter(vdata_line, 'vertex')

        num_points = len(points)
        for i in range(num_points):
            px, py = points[i]
            nx, ny = normals[i]

            # 外側頂点
            ox = px + (line_w / 2.0) * nx
            oy = py + (line_w / 2.0) * ny
            vertex_line.addData3f(ox, oy, 0.0)

            # 内側頂点
            ix = px - (line_w / 2.0) * nx
            iy = py - (line_w / 2.0) * ny
            vertex_line.addData3f(ix, iy, 0.0)

        tris_line = GeomTriangles(Geom.UHStatic)
        for i in range(num_points):
            next_i = (i + 1) % num_points
            o1, i1 = i * 2, i * 2 + 1
            o2, i2 = next_i * 2, next_i * 2 + 1

            # 反時計回り (CCW) 頂点指定 + 両面描画
            tris_line.addVertex(o1)
            tris_line.addVertex(i1)
            tris_line.addVertex(o2)

            tris_line.addVertex(i1)
            tris_line.addVertex(i2)
            tris_line.addVertex(o2)

        geom_line = Geom(vdata_line)
        geom_line.addPrimitive(tris_line)
        node_line = GeomNode('white_line_node')
        node_line.addGeom(geom_line)

        line_node = self.base.render.attachNewNode(node_line)
        line_node.setPos(0.0, 0.0, 0.005)  # グレー床の真中央 (0, 0)
        line_node.setColor(Vec4(1.0, 1.0, 1.0, 1.0))
        line_node.setTwoSided(True)

    def _extract_image_from_texture(self, texture):
        """
        Panda3D Texture から BGR (640x480) 画像を安全に抽出
        """
        data = texture.getRamImage()
        if data is None:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        tex_w = texture.getXSize()
        tex_h = texture.getYSize()
        num_components = texture.getNumComponents()

        image = np.frombuffer(data, dtype=np.uint8)
        if len(image) == tex_w * tex_h * num_components:
            image = image.reshape((tex_h, tex_w, num_components))
        else:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        bgr_img = image[:, :, :3]
        bgr_img = np.flipud(bgr_img)

        if (tex_w, tex_h) != (self.width, self.height):
            bgr_img = cv2.resize(bgr_img, (self.width, self.height))

        return bgr_img.copy()

    def render_frame(self, robot_x, robot_y, robot_yaw):
        """
        一人称カメラ: ロボット位置 (x, y, yaw) から高さ 40cm (Z=+0.4m), Pitch=0 でカメラ画像を生成
        :return: (480, 640, 3) BGR numpy array
        """
        cam_x = robot_x
        cam_y = robot_y
        cam_z = 0.4

        self.cam_fpv.setPos(cam_x, cam_y, cam_z)

        # Yaw角調整 (Panda3D +Y軸正面)
        h_deg = np.degrees(robot_yaw) - 90.0
        self.cam_fpv.setHpr(h_deg, 0.0, 0.0)

        # レンダリング実行
        self.base.graphicsEngine.renderFrame()

        return self._extract_image_from_texture(self.tex_fpv)

    def render_birdseye_frame(self, robot_x, robot_y, robot_yaw):
        """
        全体鳥瞰図カメラ: 上空固定視点 (0, 0, 30) から直交射影でコース全体とグレー床をレンダリング
        AGVの現在位置・進行方向をマーカーオーバーレイ表示
        :return: (480, 640, 3) BGR numpy array
        """
        img = self._extract_image_from_texture(self.tex_bird)

        # 直交射影マッピング: (0, 0) が画像正中央 (320, 240)
        # フィルムサイズ: span_x = 34.0m, span_y = 25.5m
        px = int((robot_x - (-self.bird_span_x / 2.0)) / self.bird_span_x * self.width)
        py = int(self.height - (robot_y - (-self.bird_span_y / 2.0)) / self.bird_span_y * self.height)

        # ロボットマーカー描画 (赤丸車体 + 緑の進行方向矢印)
        if 0 <= px < self.width and 0 <= py < self.height:
            cv2.circle(img, (px, py), 9, (0, 0, 255), -1)      # 赤丸車体
            cv2.circle(img, (px, py), 10, (255, 255, 255), 2)  # 外枠白

            # 進行方向矢印
            arrow_len = 22
            ax = int(px + arrow_len * np.cos(robot_yaw))
            ay = int(py - arrow_len * np.sin(robot_yaw))
            cv2.arrowedLine(img, (px, py), (ax, ay), (0, 255, 0), 3, tipLength=0.3)

        return img
