<template>
  <div class="about-page">
    <h2 class="page-title">
      <el-icon><InfoFilled /></el-icon>
      关于项目
    </h2>

    <!-- 项目介绍 -->
    <el-card shadow="never" class="about-card">
      <template #header>
        <span class="card-title">项目简介</span>
      </template>
      <p class="card-text">
        本项目是一个基于大语言模型（LangChain）的<strong>天气与出行助手智能体系统</strong>。
        用户通过自然语言描述需求，后端 LangChain Agent 自动完成意图理解、
        任务规划、工具调用（天气查询、日期解析），并生成结构化的出行建议回答。
        前端采用 Vue3 技术栈，实现了聊天交互界面、Agent 执行过程可视化、工具调用记录展示等功能。
      </p>
    </el-card>

    <!-- 技术栈 -->
    <el-card shadow="never" class="about-card">
      <template #header>
        <span class="card-title">技术栈</span>
      </template>
      <div class="tech-grid">
        <div class="tech-col">
          <h4>前端</h4>
          <div class="tech-tags">
            <el-tag>Vue 3</el-tag>
            <el-tag>Vite</el-tag>
            <el-tag>Element Plus</el-tag>
            <el-tag>Vue Router</el-tag>
            <el-tag>Axios</el-tag>
            <el-tag>Pinia</el-tag>
            <el-tag>ECharts</el-tag>
          </div>
        </div>
        <div class="tech-col">
          <h4>后端</h4>
          <div class="tech-tags">
            <el-tag type="success">FastAPI</el-tag>
            <el-tag type="success">Python</el-tag>
            <el-tag type="success">LangChain</el-tag>
            <el-tag type="success">LLM</el-tag>
            <el-tag type="success">RESTful API</el-tag>
          </div>
        </div>
        <div class="tech-col">
          <h4>开发工具</h4>
          <div class="tech-tags">
            <el-tag type="warning">Git</el-tag>
            <el-tag type="warning">VS Code</el-tag>
            <el-tag type="warning">npm</el-tag>
            <el-tag type="warning">ESLint</el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.about-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}

.about-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  margin-bottom: 20px;
}

.about-card :deep(.el-card__header) {
  background: #fafafa;
  padding: 12px 18px;
}

.about-card :deep(.el-card__body) {
  padding: 18px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
}

.card-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
}

/* 技术栈 */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
}

.tech-col h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
