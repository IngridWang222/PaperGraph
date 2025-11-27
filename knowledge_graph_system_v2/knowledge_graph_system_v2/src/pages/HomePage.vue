<template>
  <div id="homePage">
    <a-card class="welcome-card" :bordered="false">
      <div class="welcome-content">
        <div class="welcome-icon">📚</div>
        <h1 class="welcome-title">{{ msg }}</h1>
        <p class="welcome-subtitle">探索学术知识，构建智能图谱</p>
        <div class="feature-grid">
          <div class="feature-item">
            <div class="feature-icon">🔍</div>
            <h3>智能检索</h3>
            <p>快速查找论文、作者和机构信息</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">📊</div>
            <h3>数据统计</h3>
            <p>多维度数据分析和可视化展示</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🕸️</div>
            <h3>知识图谱</h3>
            <p>直观展示学术关系网络</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">📥</div>
            <h3>数据导出</h3>
            <p>支持多种格式的数据导出</p>
          </div>
        </div>
        <div class="action-buttons">
          <a-button type="primary" size="large" @click="goToGraph">
            <template #icon><span>🕸️</span></template>
            查看知识图谱
          </a-button>
          <a-button size="large" @click="goToStats">
            <template #icon><span>📊</span></template>
            数据统计
          </a-button>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const msg = "欢迎！导入文献，构建论文知识图谱~";
const router = useRouter();

const goToGraph = () => {
  router.push("/kg");
};

const goToStats = () => {
  router.push("/data-stats");
};
</script>

<style scoped>
#homePage {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 24px;
}

.welcome-card {
  max-width: 1200px;
  width: 100%;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

.welcome-content {
  text-align: center;
  padding: 48px 24px;
}

.welcome-icon {
  font-size: 80px;
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
}

.welcome-title {
  font-size: 36px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.welcome-subtitle {
  font-size: 18px;
  color: #666;
  margin-bottom: 48px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 48px;
}

.feature-item {
  padding: 24px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid rgba(102, 126, 234, 0.1);
}

.feature-item:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.3);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-item h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.feature-item p {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.action-buttons .ant-btn {
  height: 48px;
  padding: 0 32px;
  font-size: 16px;
  border-radius: 24px;
  transition: all 0.3s ease;
}

.action-buttons .ant-btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.action-buttons .ant-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
}

@media (max-width: 768px) {
  .welcome-title {
    font-size: 28px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
