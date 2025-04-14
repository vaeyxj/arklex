import json
from pyvis.network import Network


def visualize_task_graph(json_path, output_html="task_graph.html"):
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建网络图
    net = Network(height="1000px", width="100%", directed=True, notebook=False)

    # 配置节点颜色方案
    node_colors = {
        'start': '#FF6B6B',
        'default': '#4ECDC4',
        'message': '#45B7D1',
        'search': '#96CEB4'
    }

    # 添加节点
    nodes = {}
    for node_id, node_data in data["nodes"]:
        resource_type = node_data["resource"]["name"]
        task = node_data["attribute"].get("task", "")
        value = node_data["attribute"].get("value", "")

        # 确定节点颜色
        color = node_colors['default']
        if node_data.get("type") == "start":
            color = node_colors['start']
        elif "MessageWorker" in resource_type:
            color = node_colors['message']
        elif "SearchWorker" in resource_type:
            color = node_colors['search']

        # 构建节点提示信息
        tooltip = f"""
            ID: {node_id}
            Resource: {resource_type}
            Task: {task}
            Content: {value}
        """

        nodes[node_id] = node_id
        net.add_node(
            node_id,
            label=f"[{node_id}] {resource_type}",
            title=tooltip,
            color=color,
            shape='box',
            margin=10,
            font={'size': 12}
        )

    # 添加边
    for edge in data["edges"]:
        source, target, edge_data = edge
        intent = edge_data.get("intent", "")
        weight = edge_data["attribute"].get("weight", 1)
        net.add_edge(source, target, title=intent, width=weight, arrows='to')

    # 配置层次化布局参数
    net.set_options("""
    {
        "layout": {
            "hierarchical": {
                "enabled": true,
                "direction": "UD",
                "sortMethod": "directed",
                "levelSeparation": 150,
                "nodeSpacing": 100,
                "treeSpacing": 200
            }
        },
        "physics": {
            "hierarchicalRepulsion": {
                "centralGravity": 0,
                "springLength": 200,
                "springConstant": 0.01,
                "nodeDistance": 150,
                "damping": 0.09
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "hierarchicalRepulsion"
        },
        "nodes": {
            "font": {
                "size": 14,
                "face": "Tahoma"
            }
        }
    }
    """)

    # 生成可视化文件
    net.write_html(output_html)
    return output_html


# 使用示例
visualize_task_graph("taskgraph.json")