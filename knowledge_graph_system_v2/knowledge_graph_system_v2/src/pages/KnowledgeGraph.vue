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
      <!-- 缩放控制按钮 -->
      <div
        style="
          position: absolute;
          right: 16px;
          bottom: 16px;
          z-index: 10;
          display: flex;
          flex-direction: column;
          gap: 8px;
        "
      >
        <a-button size="small" shape="circle" @click="zoomGraph(1.2)">+</a-button>
        <a-button size="small" shape="circle" @click="zoomGraph(0.8)">-</a-button>
      </div>

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
import { fetchRootGraph, persistLayout, type GraphResponse } from "@/api/graph";
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

/* 完整图数据（包含所有单位 / 作者 / 论文） */
const fullGraph = ref<GraphDTO>({ nodes: [], edges: [] });

/* 当前展示的图数据（用于控制显隐） */
const visibleGraph = ref<GraphDTO>({ nodes: [], edges: [] });

/* 展开状态：哪些作者的论文已展开，哪些单位被折叠 */
const expandedAuthors = ref<Set<string>>(new Set());
const hiddenOrgs = ref<Set<string>>(new Set());

/* 图谱实例 */
const chartDom = ref<HTMLDivElement>();
let ins: echarts.ECharts;

const lineStyleMap: Record<string, any> = {
  // 作者-论文边：绿色
  AUTHORED: { width: 2, color: "#52c41a", type: "solid", opacity: 0.9 },
  // 单位-作者边：加粗加深，便于观察
  AFFILIATED_WITH: { width: 3, color: "#303133", type: "solid", opacity: 1 },
  // 引用边：红色虚线
  CITES: { width: 2, color: "#f56c6c", type: "dotted", opacity: 0.9 },
};

/**
 * 图谱缩放（通过 ECharts graphRoam 动作）
 * factor > 1 放大，factor < 1 缩小
 */
function zoomGraph(factor: number) {
  if (!ins) return;
  try {
    const option = ins.getOption() as any;
    const series = option.series?.[0] || {};
    const currentZoom = typeof series.zoom === "number" ? series.zoom : 1;
    const newZoom = Math.max(0.2, Math.min(5, currentZoom * factor));

    ins.setOption({
      series: [
        {
          ...series,
          zoom: newZoom,
        },
      ],
    });
  } catch (e) {
    console.warn("图谱缩放失败:", e);
  }
}

/**
 * 应用筛选并加载数据
 */
async function onFilter() {
  try {
    // 每次筛选重置展开状态
    expandedAuthors.value = new Set();
    hiddenOrgs.value = new Set();

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
    console.log(
      "原始边（AFFILIATED_WITH）:",
      rawData.edges.filter((e: any) => e.type === "AFFILIATED_WITH")
    );

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
      const key = `${edge.source}-${edge.target}-${edge.type}`;
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

    // ===== 在前端补充单位-作者关系边（AFFILIATED_WITH） =====
    // 某些情况下后端未返回 AFFILIATED_WITH 边，但 Author 节点上有 org_id 属性
    const orgIdSet = new Set(
      processedNodes.filter((n) => n.type === "Organization").map((n) => n.id)
    );
    const orgAuthorEdges: Edge[] = [];
    processedNodes
      .filter((n) => n.type === "Author")
      .forEach((author: any) => {
        const orgId = author.org_id as string | undefined;
        if (orgId && orgIdSet.has(orgId)) {
          const key = `${author.id}-${orgId}-AFFILIATED_WITH`;
          if (!edgeMap.has(key)) {
            const e: Edge = {
              source: author.id,
              target: orgId,
              relation: "AFFILIATED_WITH",
            };
            orgAuthorEdges.push(e);
            edgeMap.set(key, e);
          }
        }
      });

    const dto: GraphDTO = {
      nodes: processedNodes,
      edges: [...processedEdges, ...orgAuthorEdges],
    };

    // 保存完整图数据
    fullGraph.value = dto;

    // 初始展示：只显示单位 + 作者，以及它们之间的连线
    const initialNodes = processedNodes.filter(
      (n) => n.type === "Organization" || n.type === "Author"
    );
    // 单位-作者边：关系类型为 AFFILIATED_WITH（包括前端补充的那部分）
    const initialEdges = fullGraph.value.edges.filter((e) => e.relation === "AFFILIATED_WITH");

    visibleGraph.value = {
      nodes: initialNodes,
      edges: initialEdges,
    };

    draw(visibleGraph.value);
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
      const node = params.data as Node;
      handleNodeClick(node);
      selected.value = node;
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
 * 点击节点：单位/作者展开或折叠
 */
function handleNodeClick(node: Node) {
  if (node.type === "Author") {
    toggleAuthorPapers(node.id);
  } else if (node.type === "Organization") {
    toggleOrganizationSubtree(node.id);
  }
}

/**
 * 展开 / 折叠某个作者名下的所有论文
 * - 初始不显示任何论文
 * - 点击作者：显示其全部论文
 * - 再次点击：隐藏其全部论文
 */
function toggleAuthorPapers(authorId: string) {
  // 找到该作者在完整图中的所有 AUTHOR->PAPER 边
  const authoredEdges = fullGraph.value.edges.filter(
    (e) => e.relation === "AUTHORED" && (e.source === authorId || e.target === authorId)
  );

  const paperIds = new Set(authoredEdges.map((e) => (e.source === authorId ? e.target : e.source)));

  if (expandedAuthors.value.has(authorId)) {
    // 已展开 -> 折叠：从可见图中移除这些论文节点和对应边
    const newNodes = visibleGraph.value.nodes.filter(
      (n) => !(n.type === "Paper" && paperIds.has(n.id))
    );
    const newEdges = visibleGraph.value.edges.filter(
      (e) =>
        !(
          e.relation === "AUTHORED" &&
          (paperIds.has(e.source) || paperIds.has(e.target) || e.source === authorId)
        )
    );

    visibleGraph.value = { nodes: newNodes, edges: newEdges };
    expandedAuthors.value.delete(authorId);
  } else {
    // 未展开 -> 展开：向可见图中添加这些论文节点和 AUTHOR->PAPER 边
    const paperNodes = fullGraph.value.nodes.filter(
      (n) => n.type === "Paper" && paperIds.has(n.id)
    );

    const nodeMap = new Map<string, Node>();
    visibleGraph.value.nodes.forEach((n) => nodeMap.set(n.id, n));
    paperNodes.forEach((n) => nodeMap.set(n.id, n));

    const edgeMap = new Map<string, Edge>();
    visibleGraph.value.edges.forEach((e) =>
      edgeMap.set(`${e.source}-${e.target}-${e.relation}`, e)
    );
    authoredEdges.forEach((e) => {
      edgeMap.set(`${e.source}-${e.target}-${e.relation}`, {
        source: e.source,
        target: e.target,
        relation: e.relation as Edge["relation"],
        ...(e as any).properties,
      });
    });

    visibleGraph.value = {
      nodes: Array.from(nodeMap.values()),
      edges: Array.from(edgeMap.values()),
    };
    expandedAuthors.value.add(authorId);
  }

  draw(visibleGraph.value);
}

/**
 * 展开 / 折叠某个单位的整棵子树
 * - 初始：所有单位及其作者可见，但不显示论文
 * - 点击单位：
 *    - 若当前可见：隐藏该单位下的所有作者及其论文
 *    - 若当前已隐藏：只恢复作者和 AFFILIATED_WITH 边，不自动展开论文
 */
function toggleOrganizationSubtree(orgId: string) {
  // 找出该单位下的所有作者
  const orgEdges = fullGraph.value.edges.filter(
    (e) => e.relation === "AFFILIATED_WITH" && (e.source === orgId || e.target === orgId)
  );

  const authorIds = new Set(
    orgEdges.map((e) => (e.source === orgId ? e.target : e.source)).filter(Boolean)
  );

  if (!authorIds.size) {
    return;
  }

  if (hiddenOrgs.value.has(orgId)) {
    // 单位当前是“折叠”状态 -> 展开：恢复作者和单位-作者边
    const nodeMap = new Map<string, Node>();
    visibleGraph.value.nodes.forEach((n) => nodeMap.set(n.id, n));

    const authorNodes = fullGraph.value.nodes.filter(
      (n) => n.type === "Author" && authorIds.has(n.id)
    );
    authorNodes.forEach((n) => nodeMap.set(n.id, n));

    const edgeMap = new Map<string, Edge>();
    visibleGraph.value.edges.forEach((e) =>
      edgeMap.set(`${e.source}-${e.target}-${e.relation}`, e)
    );
    orgEdges.forEach((e) => {
      edgeMap.set(`${e.source}-${e.target}-${e.relation}`, {
        source: e.source,
        target: e.target,
        relation: e.relation as Edge["relation"],
        ...(e as any).properties,
      });
    });

    visibleGraph.value = {
      nodes: Array.from(nodeMap.values()),
      edges: Array.from(edgeMap.values()),
    };
    hiddenOrgs.value.delete(orgId);
  } else {
    // 单位当前是“展开”状态 -> 折叠：隐藏该单位下所有作者及其论文
    // 先找出这些作者对应的所有论文
    const authoredEdges = fullGraph.value.edges.filter(
      (e) => e.relation === "AUTHORED" && authorIds.has(e.source)
    );
    const paperIds = new Set(authoredEdges.map((e) => e.target));

    // 从可见图中删除这些作者和论文以及所有相关边
    const newNodes = visibleGraph.value.nodes.filter(
      (n) => !authorIds.has(n.id) && !paperIds.has(n.id)
    );
    const newEdges = visibleGraph.value.edges.filter(
      (e) =>
        !authorIds.has(e.source) &&
        !authorIds.has(e.target) &&
        !paperIds.has(e.source) &&
        !paperIds.has(e.target)
    );

    visibleGraph.value = { nodes: newNodes, edges: newEdges };

    // 清理这些作者的“已展开论文”状态
    authorIds.forEach((id) => expandedAuthors.value.delete(id));
    hiddenOrgs.value.add(orgId);
  }

  draw(visibleGraph.value);
}

function tagColor(type: string) {
  return type === "Paper" ? "blue" : type === "Author" ? "orange" : "green";
}

onMounted(() => {
  onFilter();
  window.addEventListener("resize", () => ins?.resize());
});
</script>
