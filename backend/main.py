from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import asyncio

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
    
    # ---------- 新增：风控 Agent ----------

class RiskAnalysisRequest(BaseModel):
    steps: list  # 接收规划Agent输出的任务列表

class RiskItem(BaseModel):
    step_index: int
    step_title: str = ""
    risk: str
    suggestion: str

@app.post("/analyze-risks")
async def analyze_risks(req: RiskAnalysisRequest):
    """风控 Agent：分析每个步骤的风险并给出建议"""
    # 将步骤格式化为文本
    steps_text = ""
    for i, step in enumerate(req.steps):
        title = step.get("title", f"步骤{i+1}")
        desc = step.get("desc", "")
        steps_text += f"步骤{i+1}：{title} - {desc}\n"

    prompt = f"""你是一个项目风险分析师。以下是某个项目的任务步骤，请分析每个步骤可能存在的风险，并给出具体的应对建议。

{steps_text}

严格按照 JSON 数组格式返回，不要包含其他文字。格式示例：
[{{"step_index":0, "step_title":"确定分享主题", "risk":"主题与受众不匹配，导致参与度低", "suggestion":"提前调研受众兴趣，准备2-3个备选主题并投票决定"}}]
"""
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500
        )
        content = response.choices[0].message.content
        # 清理可能的 Markdown 代码块标记
        if "```" in content:
            start = content.find("[")
            end = content.rfind("]") + 1
            content = content[start:end]
        risks = json.loads(content)
        return {"risks": risks}
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}", "raw": content}
    except Exception as e:
        return {"error": str(e)}
    
    # ---------- 新增：编排接口（串联规划 + 风控） ----------

@app.post("/orchestrate")
async def orchestrate(req: PlanRequest):
    """一键执行：规划 → 风险分析"""
    # 1. 调用规划 Agent（直接复用内部逻辑）
    plan_prompt = f"""你是一个专业的任务规划师。请将以下目标拆解为 3-7 个具体的执行步骤，每个步骤包含：
- title: 步骤标题
- desc: 详细描述
- hours: 预估耗时（数字，单位小时）

严格按照 JSON 数组格式返回，不要包含其他文字。示例：
[{{"title":"确定分享主题","desc":"根据受众兴趣和自身专业确定分享内容方向","hours":2}}]

目标：{req.goal}
"""
    try:
        plan_response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": plan_prompt}],
            temperature=0.2,
            max_tokens=1000
        )
        plan_content = plan_response.choices[0].message.content
        if "```" in plan_content:
            start = plan_content.find("[")
            end = plan_content.rfind("]") + 1
            plan_content = plan_content[start:end]
        plan = json.loads(plan_content)
    except Exception as e:
        return {"error": f"规划失败: {str(e)}"}

    # 2. 调用风控 Agent（直接复用内部逻辑）
    steps_text = ""
    for i, step in enumerate(plan):
        title = step.get("title", f"步骤{i+1}")
        desc = step.get("desc", "")
        steps_text += f"步骤{i+1}：{title} - {desc}\n"

    risk_prompt = f"""你是一个项目风险分析师。请分析以下任务步骤的风险并给出建议，返回 JSON 数组。

{steps_text}

格式：[{{"step_index":0, "step_title":"确定分享主题", "risk":"...", "suggestion":"..."}}]
"""
    try:
        risk_response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": risk_prompt}],
            temperature=0.2,
            max_tokens=1500
        )
        risk_content = risk_response.choices[0].message.content
        if "```" in risk_content:
            start = risk_content.find("[")
            end = risk_content.rfind("]") + 1
            risk_content = risk_content[start:end]
        risks = json.loads(risk_content)
    except Exception as e:
        risks = [{"step_index": i, "step_title": step.get("title", ""), "risk": "分析失败", "suggestion": str(e)} for i, step in enumerate(plan)]

    return {"plan": plan, "risks": risks}


# ---------- 流式编排接口 ----------
@app.post("/orchestrate-stream")
async def orchestrate_stream(req: PlanRequest):
    """流式编排：逐步发送规划步骤和风险分析"""
    async def generate():
        # 阶段1：规划 Agent
        yield f"data: {json.dumps({'type': 'status', 'data': '🤖 规划 Agent 正在拆解任务...'})}\n\n"
        await asyncio.sleep(0.1)  # 微小延迟确保前端能捕获

        plan_prompt = f"""你是一个专业的任务规划师。请将以下目标拆解为 3-7 个具体的执行步骤，每个步骤包含：
- title: 步骤标题
- desc: 详细描述
- hours: 预估耗时（数字，单位小时）

严格按照 JSON 数组格式返回，不要包含其他文字。示例：
[{{"title":"确定分享主题","desc":"根据受众兴趣和自身专业确定分享内容方向","hours":2}}]

目标：{req.goal}
"""
        try:
            plan_response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.2,
                max_tokens=1000,
                stream=True   # 使用流式
            )
            plan_content = ""
            for chunk in plan_response:
                if chunk.choices[0].delta.content:
                    plan_content += chunk.choices[0].delta.content
            if "```" in plan_content:
                start = plan_content.find("[")
                end = plan_content.rfind("]") + 1
                plan_content = plan_content[start:end]
            plan = json.loads(plan_content)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': f'规划失败: {str(e)}'})}\n\n"
            return

        # 逐条发送规划步骤
        for i, step in enumerate(plan):
            yield f"data: {json.dumps({'type': 'plan_step', 'data': step, 'index': i})}\n\n"
            await asyncio.sleep(0.05)

        # 阶段2：风控 Agent
        yield f"data: {json.dumps({'type': 'status', 'data': '🛡️ 风控 Agent 正在分析风险...'})}\n\n"
        await asyncio.sleep(0.1)

        steps_text = ""
        for i, step in enumerate(plan):
            title = step.get("title", f"步骤{i+1}")
            desc = step.get("desc", "")
            steps_text += f"步骤{i+1}：{title} - {desc}\n"

        risk_prompt = f"""你是一个项目风险分析师。请分析以下任务步骤的风险并给出建议，返回 JSON 数组。

{steps_text}

格式：[{{"step_index":0, "step_title":"确定分享主题", "risk":"...", "suggestion":"..."}}]
"""
        try:
            risk_response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": risk_prompt}],
                temperature=0.2,
                max_tokens=1500,
                stream=True
            )
            risk_content = ""
            for chunk in risk_response:
                if chunk.choices[0].delta.content:
                    risk_content += chunk.choices[0].delta.content
            if "```" in risk_content:
                start = risk_content.find("[")
                end = risk_content.rfind("]") + 1
                risk_content = risk_content[start:end]
            risks = json.loads(risk_content)
        except Exception as e:
            risks = [{"step_index": i, "step_title": step.get("title", ""), "risk": "分析失败", "suggestion": str(e)} for i, step in enumerate(plan)]

        # 逐条发送风险分析
        for risk in risks:
            yield f"data: {json.dumps({'type': 'risk_step', 'data': risk})}\n\n"
            await asyncio.sleep(0.05)

        # 完成
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")