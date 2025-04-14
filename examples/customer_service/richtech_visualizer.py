import json
from pyvis.network import Network

def visualize_task_graph(json_path, output_html="task_graph.html"):
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建网络图
    net = Network(height="800px", width="100%", directed=True, notebook=False)
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=100)

    # 添加节点
    node_colors = {
        'start': '#FF6B6B',
        'default': '#4ECDC4',
        'message': '#45B7D1',
        'search': '#96CEB4'
    }

    nodes = {}
    for node_id, node_data in data["nodes"]:
        resource_type = node_data["resource"]["name"]
        task = node_data["attribute"].get("task", "")
        value = node_data["attribute"].get("value", "")

        # 设置节点颜色
        if node_data.get("type") == "start":
            color = node_colors['start']
        elif "MessageWorker" in resource_type:
            color = node_colors['message']
        elif "SearchWorker" in resource_type:
            color = node_colors['search']
        else:
            color = node_colors['default']

        # 创建节点标签
        label = f"[{node_id}] {resource_type}"
        title = f"<b>ID:</b> {node_id}<br>"
        title += f"<b>Resource:</b> {resource_type}<br>"
        title += f"<b>Task:</b> {task}<br>"
        title += f"<b>Content:</b> {value}"

        nodes[node_id] = node_id
        net.add_node(node_id,
                     label=label,
                     title=title,
                     color=color,
                     shape='box')

    # 添加边
    for edge in data["edges"]:
        source, target, edge_data = edge
        intent = edge_data.get("intent", "")
        weight = edge_data["attribute"].get("weight", 1)

        net.add_edge(source, target,
                     title=intent,
                     width=weight,
                     arrows='to')

    # 设置布局选项
    net.set_options("""
    {
      "physics": {
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        },
        "hierarchicalRepulsion": {
          "centralGravity": 0,
          "springLength": 200,
          "springConstant": 0.01,
          "nodeDistance": 200,
          "damping": 0.09
        },
        "maxVelocity": 50,
        "minVelocity": 0.1
      }
    }
    """)

    # 生成HTML文件
    net.write_html(output_html)
    return output_html

# 使用示例
visualize_task_graph("taskgraph.json")