# Multi-Agent Task Planner（多智能体任务规划看板）

AI 全栈项目：规划 Agent + 风控 Agent 协作，支持工具调用（搜索）与流式交互。

## ✅ 功能
- 用户输入目标，自动拆解为任务步骤
- 第二个 Agent 分析风险并给出建议
- 流式展示 Agent 思考过程（SSE）
- 规划 Agent 可自主调用搜索工具获取最新信息

## 🛠 技术栈
- 前端：Next.js (App Router), TypeScript, Tailwind CSS
- 后端：FastAPI, Python, 智谱 GLM-4-Flash
- Agent 框架：原生 Function Calling + 工具集成
- 搜索工具：Tavily Search API（或模拟搜索）

## 📦 本地运行
见项目内文档。