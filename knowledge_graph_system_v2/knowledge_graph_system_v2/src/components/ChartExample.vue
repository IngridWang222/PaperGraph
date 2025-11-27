<template>
  <div class="p-6 space-y-8">
    <!-- 一、领域概况 -->
    <section class="section">
      <h2 class="section-title">领域概况</h2>
      <p class="section-text">
        本研究领域主要关注自然语言处理、深度学习以及知识图谱等方向，
        涉及文本理解、机器翻译、问答系统等多个子领域。近年来，论文数量持续增长，
        学术交流频繁，研究机构间的合作趋势明显。
      </p>
    </section>

    <!-- 二、核心指标 + 柱状图组合 -->
    <div class="outer-container">
      <!-- 核心指标：正方形布局，四角放数据 -->
      <section class="section core-metrics-section">
        <h2 class="section-title">核心指标</h2>
        <div class="core-metrics-square">
          <!-- 四角数据卡片 -->
          <div class="card card-top-left">
            <div class="card-number text-blue-600">{{ paperTotal }}</div>
            <div class="card-label">论文总数</div>
          </div>
          <div class="card card-top-right">
            <div class="card-number text-green-600">{{ authorTotal }}</div>
            <div class="card-label">作者总数</div>
          </div>
          <div class="card card-bottom-left">
            <div class="card-number text-purple-600">{{ orgTotal }}</div>
            <div class="card-label">研究机构总数</div>
          </div>
          <div class="card card-bottom-right">
            <div class="card-number text-orange-600">{{ venueTotal }}</div>
            <div class="card-label">期刊/会议总数</div>
          </div>
        </div>
      </section>

      <!-- 柱状图容器：垂直排列柱状图1和柱状图2 -->
      <div class="charts-container">
        <!-- 三、作者柱状图（柱状图1） -->
        <section class="section">
          <h2 class="section-title">作者统计</h2>
          <div ref="authorChart" class="chart"></div>
        </section>

        <!-- 四、机构柱状图（柱状图2） -->
        <section class="section">
          <h2 class="section-title">机构统计</h2>
          <div ref="institutionChart" class="chart"></div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import * as echarts from "echarts";
import { post } from "@/api/http";

const authorChart = ref<HTMLDivElement | null>(null);
const institutionChart = ref<HTMLDivElement | null>(null);

// 核心指标数据
const paperTotal = ref(0);
const authorTotal = ref(0);
const orgTotal = ref(0);
const venueTotal = ref(0);

onMounted(async () => {
  try {
    const author = echarts.init(authorChart.value);
    const institution = echarts.init(institutionChart.value);

    /* 1. 获取核心指标 - 通过多个查询获取 */
    try {
      // 获取论文总数 - 通过年份统计计算
      const paperRes = await post("/statistics/query", {
        metric: "paper_count_by_year",
        limit: 1000,
      });
      // 计算所有年份的论文总数
      paperTotal.value =
        paperRes.data?.reduce((sum: number, item: any) => sum + (item.value || 0), 0) || 0;

      // 获取作者总数
      const authorRes = await post("/statistics/query", {
        metric: "top_authors",
        limit: 1000,
      });
      authorTotal.value = authorRes.total || authorRes.data?.length || 0;

      // 获取机构总数
      const orgRes = await post("/statistics/query", {
        metric: "top_organizations",
        limit: 1000,
      });
      orgTotal.value = orgRes.total || orgRes.data?.length || 0;

      // 期刊/会议总数暂时使用默认值
      venueTotal.value = 85;
    } catch (e) {
      console.warn("获取核心指标失败，使用默认值", e);
      paperTotal.value = 1280;
      authorTotal.value = 950;
      orgTotal.value = 240;
      venueTotal.value = 85;
    }

    /* 2. 作者 Top10 */
    const authorRes = await post("/statistics/query", {
      metric: "top_authors",
      limit: 10,
    });
    // 后端返回格式：{label: name, value: count}
    const authorNames = authorRes.data.map((i: any) => i.label || i.name || "");
    const authorCounts = authorRes.data.map((i: any) => i.value || i.count || 0);

    /* 3. 机构 Top10 */
    const orgRes = await post("/statistics/query", {
      metric: "top_organizations",
      limit: 10,
    });
    // 后端返回格式：{label: name, value: count}
    const orgNames = orgRes.data.map((i: any) => i.label || i.name || "");
    const orgCounts = orgRes.data.map((i: any) => i.value || i.count || 0);

    /* 4. 用真实数据 setOption */
    const authorOpt = {
      title: { text: "发表论文最多的前10个作者", left: "center" },
      tooltip: {},
      xAxis: { type: "category", data: authorNames, axisLabel: { rotate: 30 } },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: authorCounts, itemStyle: { color: "#60a5fa" } }],
    };
    const instOpt = {
      title: { text: "发表论文最多的前10个机构", left: "center" },
      tooltip: {},
      xAxis: { type: "category", data: orgNames, axisLabel: { rotate: 30 } },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: orgCounts, itemStyle: { color: "#34d399" } }],
    };
    author.setOption(authorOpt);
    institution.setOption(instOpt);

    // 窗口大小变化时自适应
    window.addEventListener("resize", () => {
      author.resize();
      institution.resize();
    });
  } catch (error) {
    console.error("加载统计数据失败:", error);
  }
});
</script>

<style scoped>
/* 外层容器样式 */
.outer-container {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

/* 核心指标区域占比 */
.core-metrics-section {
  flex: 1;
  min-width: 300px;
  height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

/* 柱状图容器占比 */
.charts-container {
  flex: 2;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 正方形容器 */
.core-metrics-square {
  width: 100%;
  max-width: 350px;
  height: 350px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.05);
  padding: 24px;
  position: relative;
  box-sizing: border-box;
}

/* 通用样式 */
.section {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.1);
  transition: all 0.3s ease;
}

.section:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 16px;
  border-bottom: 3px solid;
  border-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%) 1;
  padding-bottom: 8px;
  width: 100%;
  box-sizing: border-box;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.section-text {
  color: #4b5563;
  line-height: 1.6;
}

/* 核心指标卡片样式 */
.card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 140px;
  text-align: center;
  position: absolute;
  transition: all 0.3s ease;
  border: 1px solid rgba(102, 126, 234, 0.1);
}

.card:hover {
  transform: translateY(-4px) scale(1.05);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
}

/* 卡片定位 */
.card-top-left {
  top: 24px;
  left: 24px;
}

.card-top-right {
  top: 24px;
  right: 24px;
}

.card-bottom-left {
  bottom: 24px;
  left: 24px;
}

.card-bottom-right {
  bottom: 24px;
  right: 24px;
}

.card-number {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
  transition: all 0.3s ease;
}

.card:hover .card-number {
  transform: scale(1.1);
}

.card-label {
  margin-top: 4px;
  color: #6b7280;
  font-size: 14px;
}

/* 图表样式 */
.chart {
  width: 100%;
  height: 300px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  box-sizing: border-box;
  padding: 12px;
  transition: all 0.3s ease;
}

.chart:hover {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

/* 颜色定义 */
.text-blue-600 {
  color: #2563eb;
}

.text-green-600 {
  color: #16a34a;
}

.text-purple-600 {
  color: #7c3aed;
}

.text-orange-600 {
  color: #ea580c;
}

/* 响应式调整 */
@media (max-width: 1023px) {
  .chart {
    height: 350px;
  }

  .core-metrics-square {
    max-width: 300px;
    height: 300px;
  }
}

/* 基础间距样式 */
.p-6 {
  padding: 24px;
}

.space-y-8 {
  margin-top: 0;
  margin-bottom: 0;
}

.space-y-8 > * + * {
  margin-top: 32px;
}
</style>
