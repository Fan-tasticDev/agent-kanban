from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 允许所有跨域请求（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 智谱 AI 客户端
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# 请求模型
class PlanRequest(BaseModel):
    goal: str

@app.post("/plan")
async def plan(req: PlanRequest):
    """规划 Agent：将目标拆解为任务步骤"""
    prompt = f"""你是一个专业的任务规划师。请将以下目标拆解为 3-7 个具体的执行步骤，每个步骤包含：
- title: 步骤标题
- desc: 详细描述
- hours: 预估耗时（数字，单位小时）

严格按照 JSON 数组格式返回，不要包含其他文字。示例：
[{{"title":"确定分享主题","desc":"根据受众兴趣和自身专业确定分享内容方向","hours":2}}, {{"title":"邀请嘉宾","desc":"联系潜在嘉宾并确认时间","hours":3}}]

目标：{req.goal}
"""
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000
        )
        content = response.choices[0].message.content
        # 清理可能的 Markdown 代码块标记
        if "```" in content:
            start = content.find("[")
            end = content.rfind("]") + 1
            content = content[start:end]
        plan = json.loads(content)
        return {"plan": plan}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}", "raw": content}
    except Exception as e:
        return {"error": str(e)}