import numpy as np
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    CardMaker,
    LineSegs,
    NodePath,
    GeomNode,
    Geom,
    GeomVertexFormat,
    GeomVertexData,
    GeomVertexWriter,
    GeomTriangles,
    Vec4
)
from simulation import config

class Visualizer(ShowBase):
    def __init__(self, course_points, node_positions, left_boundary, right_boundary):
        ShowBase.__init__(self)
        self.course_points = course_points
        self.node_positions = node_positions
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary

        # 背景色（空）を「水色（スカイブルー）」に設定
        self.setBackgroundColor(0.53, 0.81, 0.92, 1.0)

        # 3Dオブジェクトの構築
        self._build_ground_polygon()
        self._build_road_polygon()
        self._build_road_lines()
        self._build_robot_model()
        self._build_node_markers()

        # コース全景のBounding Box (AABB) から中心座標 (cx, cy) を算出
        pts = np.array(self.course_points)
        min_x, max_x = np.min(pts[:, 0]), np.max(pts[:, 0])
        min_y, max_y = np.min(pts[:, 1]), np.max(pts[:, 1])
        self.map_center_x = (min_x + max_x) / 2.0
        self.map_center_y = (min_y + max_y) / 2.0

        # マルチウィンドウ（監視マップ固定カメラ用サブウィンドウ）の構築
        self.sub_win = self.openWindow(name="Top View Window", requireWindow=True)
        self.sub_cam = self.makeCamera(self.sub_win)
        self.sub_cam.reparentTo(self.render)
        # コース全体の中央上空 (Z=150.0m) に固定配置
        self.sub_cam.setPos(self.map_center_x, self.map_center_y, 150.0)
        self.sub_cam.setHpr(0, -90, 0)

    def _build_ground_polygon(self):
        """茶色の広大な大地 (Z=-0.02) と、コース沿い4mの緑の芝生 (Z=-0.01) を生成"""
        
        # 1. 茶色の広大な大地（ベース）
        cm = CardMaker('ground_plane')
        cm.setFrame(-500, 500, -500, 500)
        ground = self.render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0)
        ground.setPos(0, 0, -0.02)
        ground.setColor(0.55, 0.27, 0.07, 1.0)  # 大地色（サドルブラウン）

        # 2. 道路の両端+4mの範囲を緑の芝生ポリゴンとして構築
        vdata = GeomVertexData('grass_vertices', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')

        # 延長率 = (現在の道幅の半分 + 芝生の幅4.0m) / 道幅の半分
        half_width = config.COURSE_WIDTH / 2.0
        ratio = (half_width + 4.0) / half_width

        n = len(self.course_points)
        for i in range(n):
            cx, cy = self.course_points[i]
            lx, ly = self.left_boundary[i]
            rx, ry = self.right_boundary[i]

            # 中心座標と境界座標からベクトルを延長して芝生の外縁座標を計算
            gl_x = cx + (lx - cx) * ratio
            gl_y = cy + (ly - cy) * ratio
            gr_x = cx + (rx - cx) * ratio
            gr_y = cy + (ry - cy) * ratio

            vertex.addData3(gl_x, gl_y, -0.01)
            color.addData4(0.0, 0.5, 0.0, 1.0)  # 緑
            vertex.addData3(gr_x, gr_y, -0.01)
            color.addData4(0.0, 0.5, 0.0, 1.0)

        # 三角形を構成してポリゴンを生成
        tris = GeomTriangles(Geom.UHStatic)
        for i in range(n - 1):
            v1, v2, v3, v4 = i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 3
            tris.addVertices(v1, v2, v3)
            tris.addVertices(v2, v4, v3)

        # コースの始点と終点を閉じる
        if n > 0:
            last_idx = (n - 1) * 2
            tris.addVertices(last_idx, last_idx + 1, 0)
            tris.addVertices(last_idx + 1, 1, 0)

        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('grass_node')
        node.addGeom(geom)
        self.render.attachNewNode(node)

    def _build_road_polygon(self):
        """黒路面ポリゴン (Z=0.0) を GeomTriangles で構築"""
        vdata = GeomVertexData('road_vertices', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')

        n = len(self.left_boundary)
        for i in range(n):
            lx, ly = self.left_boundary[i]
            rx, ry = self.right_boundary[i]
            vertex.addData3(lx, ly, 0.0)
            color.addData4(0.1, 0.1, 0.1, 1.0)  # 黒系路面
            vertex.addData3(rx, ry, 0.0)
            color.addData4(0.1, 0.1, 0.1, 1.0)

        tris = GeomTriangles(Geom.UHStatic)
        for i in range(n - 1):
            l0 = 2 * i
            r0 = 2 * i + 1
            l1 = 2 * (i + 1)
            r1 = 2 * (i + 1) + 1

            tris.addVertices(l0, r0, l1)
            tris.addVertices(r0, r1, l1)

        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('road_geom')
        node.addGeom(geom)
        self.render.attachNewNode(node)

    def _build_road_lines(self):
        """外側・内側・中心の白線を LineSegs で描画 (Z=0.01)"""
        lines = LineSegs('road_lines')
        lines.setColor(1.0, 1.0, 1.0, 1.0)
        lines.setThickness(2.0)

        # 外側白線
        lines.moveTo(self.left_boundary[0][0], self.left_boundary[0][1], 0.01)
        for pt in self.left_boundary[1:]:
            lines.drawTo(pt[0], pt[1], 0.01)

        # 内側白線
        lines.moveTo(self.right_boundary[0][0], self.right_boundary[0][1], 0.01)
        for pt in self.right_boundary[1:]:
            lines.drawTo(pt[0], pt[1], 0.01)

        # 中心線（白線）
        lines.moveTo(self.course_points[0][0], self.course_points[0][1], 0.01)
        for pt in self.course_points[1:]:
            lines.drawTo(pt[0], pt[1], 0.01)

        line_node = lines.create()
        self.render.attachNewNode(line_node)

    def _build_robot_model(self):
        """仮のロボットモデル (Z=0.1) として直方体 (Cube) を配置"""
        self.robot_node = self.loader.loadModel("models/box")
        self.robot_node.reparentTo(self.render)
        self.robot_node.setScale(0.8, 1.0, 0.4)
        self.robot_node.setColor(0.2, 0.4, 0.8, 1.0)  # 青色

    def _build_node_markers(self):
        """16箇所のノードマーカー (Z=0.02) を配置"""
        lines = LineSegs('node_markers')
        lines.setColor(1.0, 0.5, 0.0, 1.0)  # オレンジ
        lines.setThickness(4.0)

        for pos in self.node_positions.values():
            nx, ny = pos[0], pos[1]
            lines.moveTo(nx - 0.3, ny, 0.02)
            lines.drawTo(nx + 0.3, ny, 0.02)
            lines.moveTo(nx, ny - 0.3, 0.02)
            lines.drawTo(nx, ny + 0.3, 0.02)

        node = lines.create()
        self.render.attachNewNode(node)

    def update_camera(self, robot_x, robot_y, robot_theta):
        """メインカメラ (FPV視点) の位置・姿態をロボット位置に追従更新"""
        cam_offset = 0.4
        cam_x = robot_x + (cam_offset * np.cos(robot_theta))
        cam_y = robot_y + (cam_offset * np.sin(robot_theta))
        self.camera.setPos(cam_x, cam_y, 0.4)
        heading = np.degrees(robot_theta) - 90.0
        self.camera.setHpr(heading, 0, 0)

    def get_camera_image(self):
        """メインウィンドウ (FPV専用) の描画バッファのみを取得して OpenCV BGR 配列として返却"""
        tex = self.win.getDisplayRegion(0).getScreenshot()
        if tex is None:
            return None
        data = tex.getRamImage()
        w = tex.getXSize()
        h = tex.getYSize()

        if data is None or len(data) == 0 or w == 0 or h == 0:
            return None

        # Panda3Dのテクスチャイメージ (RGBA または RGB)
        img = np.frombuffer(data, dtype=np.uint8)
        num_channels = len(img) // (w * h)
        img = img.reshape((h, w, num_channels))
        
        # 上下反転（Panda3Dの原点は左下）
        img = np.flipud(img)

        # BGRカラーチャンネルに変換
        if num_channels == 4:
            bgr = img[:, :, [2, 1, 0]]
        else:
            bgr = img[:, :, [2, 1, 0]]

        return bgr
