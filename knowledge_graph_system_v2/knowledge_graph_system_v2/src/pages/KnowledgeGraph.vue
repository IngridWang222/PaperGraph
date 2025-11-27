<template>
  <a-layout
    style="
      height: calc(100vh - 120px);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    "
  >
    <!-- 左侧筛选器 -->
    <a-layout-sider
      width="280"
      style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px)"
    >
      <div style="padding: 20px">
        <h3
          style="
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 12px;
          "
        >
          筛选器
        </h3>
        <a-form layout="vertical">
          <a-form-item label="年份">
            <a-slider range :min="2000" :max="2025" v-model:value="filter.year" />
          </a-form-item>
          <a-form-item label="机构">
            <a-select
              v-model:value="filter.orgs"
              mode="multiple"
              placeholder="选择机构"
              :options="orgOptions"
            />
          </a-form-item>
          <a-form-item label="作者">
            <a-input v-model:value="filter.author" placeholder="模糊搜索" />
          </a-form-item>
          <a-form-item>
            <a-button
              type="primary"
              block
              @click="onFilter"
              size="large"
              style="
                height: 40px;
                border-radius: 8px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
              "
            >
              应用筛选
            </a-button>
          </a-form-item>
        </a-form>
      </div>
    </a-layout-sider>

    <!-- 中间图谱 -->
    <a-layout-content
      style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); position: relative"
    >
      <div ref="chartDom" style="width: 100%; height: 100%"></div>
    </a-layout-content>

    <!-- 右侧详情 -->
    <a-layout-sider
      width="320"
      style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px)"
    >
      <div style="padding: 20px">
        <h3
          style="
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 12px;
          "
        >
          详细信息
        </h3>
        <div v-if="!selected">请单击节点/边</div>
        <a-form v-else layout="vertical" size="small">
          <a-form-item label="名称">
            <a-input :value="selected.label" readonly />
          </a-form-item>
          <a-form-item label="类型">
            <a-tag :color="tagColor(selected.type)">
              {{ selected.type }}
            </a-tag>
          </a-form-item>
          <!-- Paper 字段 -->
          <template v-if="selected.type === 'Paper'">
            <a-form-item label="标题">
              <a-input :value="selected.title" readonly />
            </a-form-item>
            <a-form-item label="年份">
              <a-input :value="selected.year" readonly />
            </a-form-item>
            <a-form-item label="发表地">
              <a-input :value="selected.venue" readonly />
            </a-form-item>
            <a-form-item label="DOI">
              <a-input :value="selected.doi" readonly />
            </a-form-item>
          </template>
          <!-- Author 字段 -->
          <template v-if="selected.type === 'Author'">
            <a-form-item label="h-index">
              <a-input :value="selected.hIndex" readonly />
            </a-form-item>
            <a-form-item label="ORCID">
              <a-input :value="selected.orcid" readonly />
            </a-form-item>
          </template>
          <!-- Organization 字段 -->
          <template v-if="selected.type === 'Organization'">
            <a-form-item label="国家">
              <a-input :value="selected.country" readonly />
            </a-form-item>
            <a-form-item label="排名">
              <a-input :value="selected.rank" readonly />
            </a-form-item>
          </template>
        </a-form>
      </div>
    </a-layout-sider>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import * as echarts from "echarts";
import type { GraphDTO, Node, Edge } from "@/types/graph";
import { message } from "ant-design-vue";
import { fetchRootGraph, fetchChildrenGraph, persistLayout, type GraphResponse } from "@/api/graph";
/* 筛选状态 */
const filter = ref({
  year: [2020, 2025],
  orgs: [] as string[],
  author: "",
});

// 机构下拉选项，后端返回后动态填充
const orgOptions = ref<{ label: string; value: string }[]>([]);

/* 选中项 */
const selected = ref<Node | null>(null);

/* 当前图数据和展开状态（用于子树显隐） */
const graphData = ref<GraphDTO>({ nodes: [], edges: [] });
const expandedNodes = ref<Set<string>>(new Set());

/* 图谱实例 */
const chartDom = ref<HTMLDivElement>();
let ins: echarts.ECharts;

const lineStyleMap: Record<string, any> = {
  AUTHORED: { width: 1.5, color: "#67c23a", type: "solid" },
  AFFILIATED_WITH: { width: 1.5, color: "#909399", type: "dashed" },
  CITES: { width: 2, color: "#f56c6c", type: "dotted" },
};

/**
 * 应用筛选并加载数据
 */
async function onFilter() {
  try {
    // 每次筛选重置展开状态
    expandedNodes.value = new Set();

    const params = {
      limit: 1000,
      yearStart: filter.value.year[0],
      yearEnd: filter.value.year[1],
      orgs: filter.value.orgs,
      author: filter.value.author,
    };

    const rawData = await fetchRootGraph(params);

    console.log("原始节点:", rawData.nodes);
    console.log("原始边:", rawData.edges);

    // 将后端通用节点结构映射为前端 Node 结构，并补充不同类型的字段
    const processedNodes: Node[] = rawData.nodes.map((node) => {
      const props = node.properties || {};
      const type = node.label as "Paper" | "Author" | "Organization";

      const base: Node = {
        id: props.id || node.id,
        type,
        label: props.name || props.title || node.label,
        // 通用属性直接铺开
        ...props,
      };

      // 针对不同类型做字段映射，让右侧详情可以正确显示
      if (type === "Author") {
        base.hIndex = props.h_index ?? props.hIndex;
        base.orcid = props.orcid;
      } else if (type === "Organization") {
        base.country = props.country;
        // rank_score -> rank
        const rankScore = props.rank_score ?? props.rank;
        base.rank = typeof rankScore === "number" ? rankScore : Number(rankScore || 0);
      } else if (type === "Paper") {
        base.title = props.title;
        base.year = props.year;
        base.venue = props.venue;
        base.doi = props.doi;
      }

      return base;
    });

    // 根据组织节点动态生成筛选下拉选项，保持前后端一致
    const orgNames = Array.from(
      new Set(processedNodes.filter((n) => n.type === "Organization").map((n) => n.label))
    );
    orgOptions.value = orgNames.map((name) => ({ label: name, value: name }));

    const edgeMap = new Map<string, Edge>();
    rawData.edges.forEach((edge) => {
      const key = `${edge.source}-${edge.target}`;
      if (!edgeMap.has(key)) {
        edgeMap.set(key, {
          source: edge.source,
          target: edge.target,
          relation: edge.type,
          ...edge.properties,
        });
      }
    });
    const processedEdges = Array.from(edgeMap.values());

    const dto: GraphDTO = {
      nodes: processedNodes,
      edges: processedEdges,
    };

    graphData.value = dto;
    draw(graphData.value);
  } catch (error) {
    console.error("筛选失败:", error);
    message.error(`加载图谱失败: ${error instanceof Error ? error.message : "未知错误"}`);
  }
}

/**
 * 绘制/重绘图谱
 */
function draw(dto: GraphDTO) {
  if (!chartDom.value) return;
  if (!ins) ins = echarts.init(chartDom.value);

  const color: Record<string, string> = {
    Paper: "#409eff",
    Author: "#f2d545",
    Organization: "#67c23a",
  };
  console.log("【边数据】links 长度:", dto.edges.length, dto.edges);
  console.log(
    "【节点类型检查】",
    dto.nodes.map((n) => ({ id: n.id, label: n.label, type: n.type }))
  );
  const option: echarts.EChartsOption = {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === "edge") {
          const rel = params.data.relation;
          const cit = rel === "CITES" ? "（引用）" : "";
          return `${params.data.source} → ${params.data.target}<br/>关系：${rel}${cit}`;
        }
        return params.data.label || params.data.name || params.data.title;
      },
    },
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        data: dto.nodes.map((n) => ({
          id: n.id,
          name: n.label,
          symbolSize: n.type === "Organization" ? 28 : n.type === "Paper" ? 30 : 20,
          itemStyle: {
            color: n.type === "Organization" ? "#e60000" : color[n.type],
          },
          ...n,
        })),
        links: dto.edges.map((e) => ({
          source: e.source,
          target: e.target,
          relation: e.relation,
          lineStyle: lineStyleMap[e.relation] || { width: 1.5, color: "#999" },
        })),
        categories: Object.keys(color).map((name) => ({ name })),
        force: { repulsion: 800, edgeLength: 120, gravity: 0.05 },
        emphasis: { focus: "adjacency", lineStyle: { width: 3 } },
      },
    ],
  };

  ins.setOption(option);

  ins.off("click");
  ins.on("click", (params) => {
    if (params.dataType === "node") {
      handleNodeClick(params.data.id);
      selected.value = params.data as Node;
    }
  });
  ins.off("graphdragend"); // 防止重复绑定
  ins.on("graphdragend", (params) => {
    // params.data 是被拖动的节点
    const updateList = ins.getOption().series[0].data.map((n: any) => ({
      node_id: n.id,
      x: n.x ?? 0, // 拖拽后 ECharts 会给每个节点加上 x/y
      y: n.y ?? 0,
    }));

    // 可选：批量保存
    persistLayout(updateList)
      .then(() => message.success("位置已保存"))
      .catch(() => message.error("保存失败"));
  });
  console.log("【节点 id 集合】", new Set(dto.nodes.map((n) => n.id)));
  console.log(
    "【link 源-目标】",
    dto.edges.map((l) => `${l.source}->${l.target}`)
  );
  console.log("【最终】option.series[0].links", JSON.stringify(option.series[0].links));
}

/**
 * 点击节点：展开 / 折叠其子树
 */
function handleNodeClick(nodeId: string) {
  if (expandedNodes.value.has(nodeId)) {
    // 已展开 -> 折叠子树
    collapseSubtree(nodeId);
    expandedNodes.value.delete(nodeId);
  } else {
    // 未展开 -> 加载子图并合并
    loadAndMergeSubgraph(nodeId);
    expandedNodes.value.add(nodeId);
  }
}

/**
 * 绘制/重绘图谱
 */

/**
 * 加载子图并合并到当前图谱
 */
async function loadAndMergeSubgraph(nodeId: string) {
  try {
    console.log("【调试】请求子图，节点 ID:", nodeId);

    const sub = await fetchChildrenGraph(nodeId);

    // 同样需要转换数据格式
    const processedSubNodes: Node[] = sub.nodes.map((node) => {
      const props = node.properties || {};
      const type = node.label as "Paper" | "Author" | "Organization";

      const base: Node = {
        id: props.id || node.id,
        type,
        label: props.name || props.title || node.label,
        ...props,
      };

      if (type === "Author") {
        base.hIndex = props.h_index ?? props.hIndex;
        base.orcid = props.orcid;
      } else if (type === "Organization") {
        base.country = props.country;
        const rankScore = props.rank_score ?? props.rank;
        base.rank = typeof rankScore === "number" ? rankScore : Number(rankScore || 0);
      } else if (type === "Paper") {
        base.title = props.title;
        base.year = props.year;
        base.venue = props.venue;
        base.doi = props.doi;
      }

      return base;
    });

    // 边去重
    const edgeMap = new Map<string, Edge>();
    [...graphData.value.edges, ...sub.edges].forEach((edge: any) => {
      const key = `${edge.source}-${edge.target}-${edge.type}`;
      if (!edgeMap.has(key)) {
        edgeMap.set(key, {
          source: edge.source,
          target: edge.target,
          relation: edge.type,
          ...(edge.properties || {}),
        });
      }
    });
    const mergedEdges = Array.from(edgeMap.values());

    // 节点去重合并
    const nodeMap = new Map<string, Node>();
    graphData.value.nodes.forEach((n) => nodeMap.set(n.id, n));
    processedSubNodes.forEach((n) => {
      if (!nodeMap.has(n.id)) {
        nodeMap.set(n.id, n);
      }
    });

    graphData.value = {
      nodes: Array.from(nodeMap.values()),
      edges: mergedEdges,
    };

    draw(graphData.value);
  } catch (error) {
    console.error("加载子图失败:", error);
    message.error(`加载子节点失败: ${error instanceof Error ? error.message : "未知错误"}`);
  }
}

/**
 * 折叠某个节点的整棵子树（单位-作者-论文关系）
 * 规则：从该节点沿 AUTHORED / AFFILIATED_WITH 关系做 BFS，删除除根节点外的所有可达节点
 */
function collapseSubtree(rootId: string) {
  const removable = new Set<string>();
  const visited = new Set<string>([rootId]);
  const queue: string[] = [rootId];

  const edges = graphData.value.edges.filter(
    (e) => e.relation === "AUTHORED" || e.relation === "AFFILIATED_WITH"
  );

  // 建邻接表（无向），方便沿树状结构遍历
  const adj = new Map<string, string[]>();
  edges.forEach((e) => {
    if (!adj.has(e.source)) adj.set(e.source, []);
    if (!adj.has(e.target)) adj.set(e.target, []);
    adj.get(e.source)!.push(e.target);
    adj.get(e.target)!.push(e.source);
  });

  while (queue.length) {
    const current = queue.shift()!;
    const neighbors = adj.get(current) || [];
    neighbors.forEach((n) => {
      if (!visited.has(n)) {
        visited.add(n);
        removable.add(n); // 根节点本身不加入 removable
        queue.push(n);
      }
    });
  }

  if (removable.size === 0) return;

  const newNodes = graphData.value.nodes.filter((n) => !removable.has(n.id));
  const newEdges = graphData.value.edges.filter(
    (e) => !removable.has(e.source) && !removable.has(e.target)
  );

  graphData.value = {
    nodes: newNodes,
    edges: newEdges,
  };

  draw(graphData.value);
}

function tagColor(type: string) {
  return type === "Paper" ? "blue" : type === "Author" ? "orange" : "green";
}

onMounted(() => {
  onFilter();
  window.addEventListener("resize", () => ins?.resize());
});
</script>
