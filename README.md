# Multi-Agent Task Planner（多智能体任务规划看板）

AI 全栈项目：规划 Agent + 风控 Agent 协作，支持工具调用（搜索）与流式交互。

## ✨ 核心亮点

- 🧠 **双 Agent 协作**：规划 Agent 拆解任务，风控 Agent 分析风险，自动串联
- 🔧 **工具调用**：规划 Agent 可通过 Function Calling 自主调用搜索工具（Tavily）
- 📡 **流式交互**：SSE 实时推送思考状态、任务卡片和风险卡片
- 📊 **看板可视化**：任务步骤与风险分析动态展示，过程透明

## 🛠 技术栈

| 层级 | 技术选型 |
|------|----------|
| **前端** | Next.js (App Router) · TypeScript · Tailwind CSS |
| **后端** | Python · FastAPI · SSE · Function Calling |
| **大模型** | 智谱 GLM-4-Flash |
| **搜索工具** | Tavily Search API（支持模拟搜索降级） |
| **部署** | Vercel（前端）· Render（后端） |

## 📂 项目结构
```text
agent-kanban/
├── backend/
│ ├── main.py # 核心接口: /plan, /orchestrate, /orchestrate-stream
│ ├── requirements.txt
│ └── .env
├── frontend/
│ ├── app/
│ │ └── page.tsx # 看板界面与流式处理
│ └── package.json
├── .gitignore
└── README.md
```

## 📦 本地运行
```text
```bash
git clone https://github.com/Fan-tasticDev/agent-kanban.git
cd agent-kanban

# 后端
cd backend
python -m venv venv 
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
# 创建 .env，填入 ZHIPU_API_KEY 和 TAVILY_API_KEY（可选）
uvicorn main:app --reload

# 前端
cd ../frontend
npm install
npm run dev
```

## 在线演示
[点击体验](https://agent-kanban-ten.vercel.app/)
[在线演示地址2](https://agent-kanban-d5okaafz.edgeone.cool/)