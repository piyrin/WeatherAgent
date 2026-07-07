/**
 * 聊天 Mock 服务
 *
 * 模拟真实 LangGraph Agent 执行过程，根据用户输入动态生成 steps。
 * 当后端开发完成后，只需将 Chat.vue 中的 import 从 chatMock 改为 chatApi，
 * 无需修改 StepTimeline 组件。
 *
 * 设计原则：
 * 1. 根据用户输入动态决定调用哪些工具
 * 2. 模拟真实的步骤状态（pending → running → completed/failed）
 * 3. 支持工具调用成功、失败、重试等场景
 * 4. 返回的数据结构与实际后端 FastAPI 接口保持一致
 */

// 可用工具列表
const AVAILABLE_TOOLS = {
  get_weather: {
    name: 'get_weather',
    description: '获取指定城市指定日期的天气信息',
    mockOutput: (input) => ({
      city: input.city || '北京',
      date: input.date || '今天',
      weather: '晴',
      temperature: '28°C',
      humidity: '45%',
      wind: '东南风 3级',
      suggestion: '适合出行，注意防晒'
    })
  },
  parse_date: {
    name: 'parse_date',
    description: '解析自然语言日期表达',
    mockOutput: (input) => ({
      original: input.text || '',
      parsed: '2026-07-07',
      dayOfWeek: '星期二',
      isToday: true
    })
  },
  search_attractions: {
    name: 'search_attractions',
    description: '搜索旅游景点信息',
    mockOutput: (input) => ({
      city: input.city || '北京',
      attractions: [
        { name: '故宫', rating: 4.8, suggestion: '建议游玩3-4小时' },
        { name: '长城', rating: 4.9, suggestion: '建议游玩半天' }
      ]
    })
  },
  get_travel_suggestion: {
    name: 'get_travel_suggestion',
    description: '根据天气给出出行建议',
    mockOutput: (input) => ({
      suggestion: '天气良好，适合出行',
      needUmbrella: false,
      needJacket: false,
      uvIndex: '高',
      tips: ['注意防晒', '多喝水']
    })
  }
}

// 根据用户问题判断需要哪些步骤
function analyzeQuestion(message) {
  const msg = message.toLowerCase()
  const steps = []
  const tools = []

  // 第一步：理解问题（所有问题都有）
  steps.push({
    name: '理解用户问题',
    type: 'understand',
    status: 'completed'
  })

  // 判断是否需要日期解析
  const hasDateExpr = /明天|后天|今天|后天|本周|周末|下周|几号|星期|号/.test(msg)
  if (hasDateExpr) {
    steps.push({
      name: '解析日期表达',
      type: 'tool_call',
      toolName: 'parse_date',
      status: 'completed',
      toolInput: { text: message },
      toolOutput: AVAILABLE_TOOLS.parse_date.mockOutput({ text: message })
    })
    // 工具调用记录
    tools.push({
      name: 'parse_date',
      input: { text: message },
      output: AVAILABLE_TOOLS.parse_date.mockOutput({ text: message })
    })
  }

  // 判断是否需要天气工具
  const hasWeather = /天气|下雨|晴天|气温|温度|降温|升温|雨天|带伞/.test(msg)
  const cityMatch = message.match(/(北京|上海|广州|深圳|成都|杭州|武汉|南京|重庆|西安|长沙|天津|苏州|厦门|昆明)/)
  const city = cityMatch ? cityMatch[1] : '北京'

  if (hasWeather) {
    steps.push({
      name: `调用天气工具查询${city}天气`,
      type: 'tool_call',
      toolName: 'get_weather',
      status: 'completed',
      toolInput: { city, date: hasDateExpr ? '解析后日期' : '今天' },
      toolOutput: AVAILABLE_TOOLS.get_weather.mockOutput({ city, date: '今天' })
    })
    tools.push({
      name: 'get_weather',
      input: { city, date: '今天' },
      output: AVAILABLE_TOOLS.get_weather.mockOutput({ city, date: '今天' })
    })
  }

  // 判断是否需要景点搜索
  const hasAttraction = /景点|好玩|旅游|游玩|去哪|出发|旅行/.test(msg)
  if (hasAttraction && city) {
    steps.push({
      name: `搜索${city}景点信息`,
      type: 'tool_call',
      toolName: 'search_attractions',
      status: 'completed',
      toolInput: { city },
      toolOutput: AVAILABLE_TOOLS.search_attractions.mockOutput({ city })
    })
    tools.push({
      name: 'search_attractions',
      input: { city },
      output: AVAILABLE_TOOLS.search_attractions.mockOutput({ city })
    })
  }

  // 判断是否需要出行建议
  const hasTravel = /出行|出门|带伞|穿衣|合适|建议/.test(msg)
  if (hasTravel && hasWeather) {
    steps.push({
      name: '生成出行建议',
      type: 'tool_call',
      toolName: 'get_travel_suggestion',
      status: 'completed',
      toolInput: { weather: '晴', temperature: '28°C' },
      toolOutput: AVAILABLE_TOOLS.get_travel_suggestion.mockOutput()
    })
    tools.push({
      name: 'get_travel_suggestion',
      input: { weather: '晴', temperature: '28°C' },
      output: AVAILABLE_TOOLS.get_travel_suggestion.mockOutput()
    })
  }

  // 最后一步：生成回答（所有问题都有）
  steps.push({
    name: '生成回答',
    type: 'answer',
    status: 'completed'
  })

  return { steps, tools }
}

// 模拟网络延迟
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 发送消息（Mock 版本）
 * @param {string} message - 用户输入
 * @param {Function} onStepUpdate - 步骤更新回调（用于流式更新 Timeline）
 * @returns {Promise<{answer: string, steps: Array, tools: Array}>}
 */
export async function sendMessageMock(message, onStepUpdate) {
  const { steps, tools } = analyzeQuestion(message)

  // 模拟逐步执行：每个步骤依次变为 running → completed
  for (let i = 0; i < steps.length; i++) {
    // 设置为 running
    steps[i].status = 'running'
    if (onStepUpdate) {
      onStepUpdate([...steps])
    }
    await delay(600 + Math.random() * 800) // 随机延迟，更真实

    // 模拟失败和重试（10% 概率，仅对工具调用步骤）
    if (steps[i].type === 'tool_call' && Math.random() < 0.1) {
      steps[i].status = 'failed'
      steps[i].error = '工具调用超时，正在重试...'
      if (onStepUpdate) {
        onStepUpdate([...steps])
      }
      await delay(500)

      steps[i].status = 'retrying'
      steps[i].retryCount = 1
      if (onStepUpdate) {
        onStepUpdate([...steps])
      }
      await delay(800)
    }

    // 设置为 completed
    steps[i].status = 'completed'
    if (onStepUpdate) {
      onStepUpdate([...steps])
    }
  }

  // 生成回答
  const answer = generateAnswer(message, steps, tools)

  return {
    answer,
    steps,
    tools
  }
}

// 根据步骤和工具调用结果生成回答
function generateAnswer(message, steps, tools) {
  const hasWeather = steps.some(s => s.toolName === 'get_weather')
  const hasDate = steps.some(s => s.toolName === 'parse_date')
  const hasAttraction = steps.some(s => s.toolName === 'search_attractions')
  const hasTravel = steps.some(s => s.toolName === 'get_travel_suggestion')

  let answer = ''

  if (hasWeather) {
    const weatherTool = tools.find(t => t.name === 'get_weather')
    if (weatherTool) {
      const out = weatherTool.output
      answer += `根据查询结果，${out.city}${out.date}的天气是：${out.weather}，温度${out.temperature}。${out.suggestion}。\n\n`
    }
  }

  if (hasDate) {
    const dateTool = tools.find(t => t.name === 'parse_date')
    if (dateTool) {
      answer += `日期解析结果：${dateTool.output.parsed}（${dateTool.output.dayOfWeek}）。\n\n`
    }
  }

  if (hasAttraction) {
    const attrTool = tools.find(t => t.name === 'search_attractions')
    if (attrTool) {
      answer += `为你推荐以下景点：\n`
      attrTool.output.attractions.forEach(a => {
        answer += `- ${a.name}（评分${a.rating}）：${a.suggestion}\n`
      })
    }
  }

  if (hasTravel) {
    const travelTool = tools.find(t => t.name === 'get_travel_suggestion')
    if (travelTool) {
      answer += `\n出行建议：${travelTool.output.suggestion}。`
      if (travelTool.output.tips) {
        answer += `\nTips：\n`
        travelTool.output.tips.forEach(t => { answer += `- ${t}\n` })
      }
    }
  }

  if (!answer) {
    answer = `你好！我是天气与出行助手，可以帮你查询天气、解析日期、推荐景点、给出行建议。

你可以问我诸如：
- "北京今天天气怎么样？"
- "明天去武汉需要带伞吗？"
- "周末去爬长城合适吗？"`
  }

  return answer.trim()
}

export default {
  sendMessageMock
}
