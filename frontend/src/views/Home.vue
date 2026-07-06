<template>
  <div class="home-page">
    <section class="hero-section">
      <div class="hero-content">
        <el-tag type="primary" effect="dark" round class="hero-badge">LangChain Agent</el-tag>
        <h1 class="hero-title">
          天气与出行助手
          <span class="hero-highlight">智能体系统</span>
        </h1>
        <p class="hero-desc">
          基于大语言模型的智能助手，只需输入自然语言，即可获取准确的天气信息与出行建议。
          支持多轮对话、智能任务规划、工具调用，让出行决策更轻松。
        </p>
        <div class="hero-actions">
          <router-link to="/chat">
            <el-button type="primary" size="large" round><el-icon><ChatDotRound /></el-icon>开始对话</el-button>
          </router-link>
          <router-link to="/about">
            <el-button size="large" round><el-icon><InfoFilled /></el-icon>了解更多</el-button>
          </router-link>
        </div>
      </div>
    </section>

    <section class="features-section">
      <h2 class="section-title">核心功能</h2>
      <div class="features-grid">
        <div class="feature-card" v-for="item in features" :key="item.title">
          <div class="feature-icon" :style="{ background: item.bg }">
            <el-icon :size="28"><component :is="item.icon" /></el-icon>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </div>
      </div>
    </section>

    <section class="workflow-section">
      <h2 class="section-title">Agent 工作流程</h2>
      <div class="workflow-steps">
        <div class="workflow-step" v-for="(step, idx) in workflow" :key="idx">
          <div class="step-number">{{ idx + 1 }}</div>
          <div class="step-content">
            <h4>{{ step.title }}</h4>
            <p>{{ step.desc }}</p>
          </div>
          <div v-if="idx < workflow.length - 1" class="step-arrow">
            <el-icon><ArrowDown /></el-icon>
          </div>
        </div>
      </div>
    </section>

    <footer class="home-footer">
      <p>软件工程课程设计 &copy; 2026 | Vue3 + FastAPI + LangChain</p>
    </footer>
  </div>
</template>

<script setup>
import { markRaw } from 'vue'
import { Sunny, MostlyCloudy, ChatDotRound, Cpu, DataAnalysis, Connection } from '@element-plus/icons-vue'

const features = [
  { icon: markRaw(ChatDotRound), title: '自然语言交互', desc: '用日常语言描述需求，无需学习复杂指令', bg: 'linear-gradient(135deg, #3b82f6, #60a5fa)' },
  { icon: markRaw(Cpu), title: '智能任务规划', desc: 'LangChain Agent 自动分解任务，规划执行路径', bg: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
  { icon: markRaw(Sunny), title: '实时天气查询', desc: '调用天气工具获取精准天气数据，支持多城市', bg: 'linear-gradient(135deg, #f59e0b, #fbbf24)' },
  { icon: markRaw(DataAnalysis), title: '出行建议生成', desc: '结合天气与行程，生成贴心的出行建议', bg: 'linear-gradient(135deg, #10b981, #34d399)' },
  { icon: markRaw(MostlyCloudy), title: '多轮对话记忆', desc: '支持上下文记忆，连续问答更自然流畅', bg: 'linear-gradient(135deg, #06b6d4, #22d3ee)' },
  { icon: markRaw(Connection), title: '可视化执行过程', desc: '透明展示 Agent 思考与工具调用全过程', bg: 'linear-gradient(135deg, #ec4899, #f472b6)' }
]

const workflow = [
  { title: '理解用户意图', desc: '解析自然语言输入，识别关键信息（地点、时间、需求）' },
  { title: '任务规划分解', desc: 'Agent 制定执行计划，确定所需工具与调用顺序' },
  { title: '工具调用执行', desc: '依次调用天气、日期解析等工具，获取实时数据' },
  { title: '结果整合回答', desc: '综合工具返回的信息，生成结构化自然语言回复' }
]
</script>

<style scoped>
.home-page { min-height: 100vh; }

.hero-section {
  text-align: center;
  padding: 70px 24px 50px;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
}

.hero-content { max-width: 680px; margin: 0 auto; }

.hero-badge { margin-bottom: 18px; }

.hero-title {
  font-size: 38px;
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: 18px;
  letter-spacing: -1px;
}

.hero-highlight {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: block;
}

.hero-desc {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 32px;
  max-width: 520px;
  margin-left: auto;
  margin-right: auto;
}

.hero-actions { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }

.hero-actions .el-button { padding: 13px 28px; font-size: 15px; font-weight: 600; }

.features-section { padding: 50px 24px; max-width: 1080px; margin: 0 auto; }

.section-title { text-align: center; font-size: 26px; font-weight: 700; margin-bottom: 32px; }

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.feature-card {
  padding: 24px;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
  background: #fff;
  transition: all 0.25s ease;
}

.feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: #bfdbfe; }

.feature-icon {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 14px;
}

.feature-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.feature-card p { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }

.workflow-section { padding: 30px 24px 50px; max-width: 640px; margin: 0 auto; }

.workflow-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 0;
  position: relative;
}

.step-number {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  flex-shrink: 0;
}

.step-content h4 { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.step-content p { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

.step-arrow {
  position: absolute; left: 19px; top: 56px;
  color: #d1d5db; font-size: 18px;
}

.home-footer {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
  font-size: 13px;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 768px) {
  .hero-title { font-size: 26px; }
  .hero-section { padding: 40px 16px 30px; }
  .features-grid { grid-template-columns: 1fr; }
  .hero-actions { flex-direction: column; align-items: center; }
}
</style>
