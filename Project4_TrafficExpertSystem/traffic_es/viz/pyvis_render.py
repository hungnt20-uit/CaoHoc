"""Render GraphData → HTML tương tác (pyvis / vis.js)."""

from __future__ import annotations

from typing import Optional

from traffic_es.viz.graph_data import GraphData


def render_pyvis_html(
    graph: GraphData,
    *,
    height: str = "560px",
    width: str = "100%",
    physics: bool = True,
) -> str:
    """Trả về HTML đầy đủ để nhúng bằng ``st.components.v1.html``."""
    try:
        from pyvis.network import Network
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Cần cài pyvis: pip install pyvis networkx"
        ) from exc

    net = Network(
        height=height,
        width=width,
        bgcolor="#FFFFFF",
        font_color="#222222",
        directed=True,
    )
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.25,
        spring_length=120,
        spring_strength=0.015,
        damping=0.5,
    )
    if not physics:
        net.toggle_physics(False)

    for n in graph.nodes:
        border = "#111111" if n.highlight else "#666666"
        border_w = 3 if n.highlight else 1
        net.add_node(
            n.id,
            label=n.label,
            title=n.title or n.label,
            color={
                "background": n.color,
                "border": border,
                "highlight": {"background": n.color, "border": "#000000"},
            },
            size=n.size,
            borderWidth=border_w,
            group=n.group,
            font={"size": 12 if n.group == "keyphrase" else 14, "face": "arial"},
        )

    for e in graph.edges:
        net.add_edge(
            e.source,
            e.target,
            title=e.title or e.label,
            label=e.label,
            color=e.color,
            width=e.width,
            arrows="to",
            font={"size": 9, "color": "#555555", "strokeWidth": 0},
        )

    options = """
    var options = {
      "interaction": {
        "hover": true,
        "tooltipDelay": 120,
        "navigationButtons": true,
        "keyboard": false
      },
      "edges": {
        "smooth": {"type": "continuous", "roundness": 0.2}
      },
      "physics": {
        "stabilization": {"iterations": 120}
      }
    }
    """
    net.set_options(options)
    return net.generate_html(notebook=False)


def try_render_html(graph: GraphData, **kwargs) -> Optional[str]:
    """Giống ``render_pyvis_html`` nhưng trả ``None`` nếu thiếu pyvis."""
    try:
        return render_pyvis_html(graph, **kwargs)
    except ImportError:
        return None
