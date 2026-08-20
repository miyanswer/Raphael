import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET

# XMLの読み込み
tree = ET.parse("aiformula_topomap.osm")  # ファイル名を指定
root = tree.getroot()

# ノードの座標を取得
nodes = {}
for node in root.findall("node"):
    node_id = node.attrib["id"]
    # local_x, local_y の取得
    x = float(node.find("./tag[@k='local_x']").attrib["v"])
    y = float(node.find("./tag[@k='local_y']").attrib["v"])
    nodes[node_id] = (x, y)

# ウェイ（エッジ）の描画
plt.figure(figsize=(8, 8))
for way in root.findall("way"):
    nd_refs = [nd.attrib["ref"] for nd in way.findall("nd")]
    xs = [nodes[ref][0] for ref in nd_refs if ref in nodes]
    ys = [nodes[ref][1] for ref in nd_refs if ref in nodes]
    plt.plot(xs, ys, marker="o", label=f"Way {way.attrib['id']}")

# ノードのプロットとラベル表示
for node_id, (x, y) in nodes.items():
    plt.text(x, y, f" {node_id[-4:]}", fontsize=8)  # 下4桁表示

plt.xlabel("local_x [m]")
plt.ylabel("local_y [m]")
plt.title("Topological Map Visualization")
plt.grid(True)
plt.axis("equal")
plt.axhline(0, color='black', linestyle='--', linewidth=0.8)#y=0の線
plt.axvline(0, color='black', linestyle='--', linewidth=0.8)#x=0の線
plt.plot(0, 0, marker='*', markersize=15, color='red', label='OSM Origin (0,0)')
plt.legend()
plt.show()