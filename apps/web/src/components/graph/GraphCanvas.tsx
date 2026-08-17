import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphData } from "@/types";

/** 节点配色：中心主色 + 6 组柔和色（对齐效果图2） */
const GROUP_COLORS: Record<string, { bg: string; fg: string; border: string }> = {
  center: { bg: "#8B7CF6", fg: "#FFFFFF", border: "#7C6FF0" },
  g0: { bg: "#FCE7F3", fg: "#9D174D", border: "#F9A8D4" },
  g1: { bg: "#D1FAE5", fg: "#065F46", border: "#6EE7B7" },
  g2: { bg: "#DBEAFE", fg: "#1E40AF", border: "#93C5FD" },
  g3: { bg: "#FEF3C7", fg: "#92400E", border: "#FCD34D" },
  g4: { bg: "#EDE9FE", fg: "#5B21B6", border: "#C4B5FD" },
  g5: { bg: "#CFFAFE", fg: "#155E75", border: "#67E8F9" },
};

function layout(graph: GraphData): { nodes: Node[]; edges: Edge[] } {
  const children = graph.nodes.filter((n) => n.group !== "center");
  const nodes: Node[] = graph.nodes.map((n) => {
    const color = GROUP_COLORS[n.group] ?? GROUP_COLORS.g4;
    let position = { x: 0, y: 0 };
    if (n.group !== "center") {
      const idx = children.findIndex((c) => c.id === n.id);
      const angle = (idx / Math.max(children.length, 1)) * Math.PI * 2 - Math.PI / 2;
      position = { x: Math.cos(angle) * 130, y: Math.sin(angle) * 95 };
    }
    return {
      id: n.id,
      position,
      data: { label: n.label },
      draggable: false,
      style: {
        background: color.bg,
        color: color.fg,
        border: `1.5px solid ${color.border}`,
        borderRadius: n.group === "center" ? 999 : 12,
        padding: n.group === "center" ? "10px 14px" : "5px 9px",
        fontSize: n.group === "center" ? 12 : 10.5,
        fontWeight: n.group === "center" ? 700 : 500,
        width: "auto",
      },
    };
  });
  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    style: { stroke: "#C7D2FE", strokeWidth: 1.5 },
    animated: false,
  }));
  return { nodes, edges };
}

/** 迷你知识图谱画布：随 graph_updated 事件渐增渲染 */
export function GraphCanvas({ graph, height = 220 }: { graph: GraphData; height?: number }) {
  const laidOut = useMemo(() => layout(graph), [graph]);
  const [nodes, setNodes, onNodesChange] = useNodesState(laidOut.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(laidOut.edges);

  useEffect(() => {
    setNodes(laidOut.nodes);
    setEdges(laidOut.edges);
  }, [laidOut, setNodes, setEdges]);

  return (
    <div style={{ height }} className="overflow-hidden rounded-lg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        zoomOnDoubleClick={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={18} size={1} color="#EEF0F6" />
      </ReactFlow>
    </div>
  );
}
