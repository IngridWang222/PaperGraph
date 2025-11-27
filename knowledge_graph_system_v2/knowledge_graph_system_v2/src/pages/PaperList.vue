<template>
  <a-card
    title="文献列表"
    :bordered="false"
    style="
      margin: 16px;
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(10px);
    "
  >
    <!-- 搜索条 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="18">
        <a-input
          v-model:value="searchKey"
          placeholder="输入标题、作者或机构"
          allow-clear
          @pressEnter="onSearch"
        />
      </a-col>
      <a-col :span="6">
        <a-button type="primary" block @click="onSearch">搜索</a-button>
      </a-col>
    </a-row>

    <!-- 表格 -->
    <a-table
      :columns="columns"
      :data-source="data"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <!-- 标题 + 外部链接 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.dataIndex === 'title'">
          <a :href="record.url" target="_blank" rel="noopener noreferrer">
            {{ record.title }}
          </a>
        </template>
        <template v-else-if="column.dataIndex === 'authors'">
          <span>{{ record.authors.join(";") }}</span>
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { get } from "@/api/http"; // 你的 axios 封装

/* 表格列定义 */
const columns = [
  { title: "标题", dataIndex: "title", width: 280 },
  { title: "作者", dataIndex: "authors", width: 200 },
  { title: "机构", dataIndex: "orgs", width: 160 },
  { title: "年份", dataIndex: "year", width: 80, align: "center" },
];

/* 状态 */
const loading = ref(false);
const searchKey = ref("");
const data = ref<Paper[]>([]);
const pagination = ref({ current: 1, pageSize: 10, total: 0 });

/* 类型 */
interface Paper {
  id: string;
  title: string;
  authors: string[];
  orgs: string[];
  year: number;
  url: string; // 外部原文链接
}

/* 首次加载全部 */
onMounted(() => loadData());

/* 搜索 / 分页 */
function onSearch() {
  pagination.value.current = 1;
  loadData();
}
function handleTableChange(pager: any) {
  pagination.value = pager;
  loadData();
}

async function loadData() {
  loading.value = true;
  try {
    /* 后端返回格式：{nodes: [{id, label, properties: {...}}], edges: [...]} */
    const res = await get("/graph/root", {
      limit: 200, // 先拉 200 条，前端再分页
      author: searchKey.value.trim(), // 使用author参数进行搜索
    });

    /* 把图节点转成 Paper 类型 */
    // 后端返回格式：nodes = [{id, label, properties: {title, year, ...}}]
    const papers: Paper[] = res.nodes
      .filter((n: any) => n.label === "Paper" || n.type === "Paper")
      .map((n: any) => {
        const props = n.properties || {};
        // 如果搜索关键词不为空，进行前端过滤
        const searchLower = searchKey.value.toLowerCase().trim();
        const matchesSearch =
          !searchLower ||
          (props.title || "").toLowerCase().includes(searchLower) ||
          (props.name || "").toLowerCase().includes(searchLower);

        if (!matchesSearch) return null;

        return {
          id: n.id,
          title: props.title || props.name || "未知标题",
          authors: props.authors || [],
          orgs: props.orgs || [],
          year: props.year || 0,
          url: props.url || (props.doi ? `https://doi.org/${props.doi}` : "#"),
        };
      })
      .filter((p: Paper | null) => p !== null) as Paper[];

    const { current = 1, pageSize = 10 } = pagination.value;
    const start = (current - 1) * pageSize;
    data.value = papers.slice(start, start + pageSize);
    pagination.value.total = papers.length;
  } catch (error) {
    console.error("加载论文列表失败:", error);
  } finally {
    loading.value = false;
  }
}
</script>
