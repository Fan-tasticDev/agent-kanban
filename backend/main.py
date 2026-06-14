from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import asyncio
from tavily import TavilyClient
import re

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
    async def generate():
        # 阶段1：规划 Agent
        yield f"data: {json.dumps({'type': 'status', 'data': '🤖 规划 Agent 正在拆解任务...'})}\n\n"
        await asyncio.sleep(0.1)

        plan_prompt = f"""你是一个专业的任务规划师。请将以下目标拆解为 3-7 个具体的执行步骤，每个步骤包含：
- title: 步骤标题（简洁，不超过15字）
- desc: 详细描述（说明具体做什么）
- hours: 预估耗时（数字，单位小时）

严格按照 JSON 数组格式返回，不要包含其他文字。直接输出 JSON 数组，不要用 Markdown 代码块包裹。

示例：[{{"title":"确定分享主题","desc":"根据受众兴趣和自身专业确定分享内容方向","hours":2}},{{"title":"邀请嘉宾","desc":"联系潜在嘉宾并确认时间","hours":3}}]

目标：{req.goal}
"""
        try:
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            plan_content = response.choices[0].message.content
            if not plan_content:
                raise Exception("规划 Agent 未返回内容")
            
            # 提取 JSON 数组
            import re
            json_match = re.search(r'\[.*\]', plan_content, re.DOTALL)
            if json_match:
                plan_content = json_match.group(0)
            else:
                raise Exception("未找到 JSON 数组")
            
            plan = json.loads(plan_content)

            # 规范化每个步骤，确保有 title, desc, hours
            clean_plan = []
            for i, item in enumerate(plan):
                if isinstance(item, dict):
                    step = {
                        "title": item.get("title", f"步骤{i+1}"),
                        "desc": item.get("desc", item.get("description", str(item))),
                        "hours": item.get("hours", 2)
                    }
                else:
                    step = {"title": f"步骤{i+1}", "desc": str(item), "hours": 2}
                clean_plan.append(step)
            plan = clean_plan

            # 逐条发送规划步骤
            for i, step in enumerate(plan):
                yield f"data: {json.dumps({'type': 'plan_step', 'data': step, 'index': i})}\n\n"
                await asyncio.sleep(0.05)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': f'规划失败: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

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

格式：[{{"step_index":0, "step_title":"步骤标题", "risk":"风险描述", "suggestion":"应对建议"}}]
"""
        try:
            risk_response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": risk_prompt}],
                temperature=0.2,
                max_tokens=1500
            )
            risk_content = risk_response.choices[0].message.content
            
            json_match = re.search(r'\[.*\]', risk_content, re.DOTALL)
            if json_match:
                risk_content = json_match.group(0)
            risks = json.loads(risk_content)
            
            for risk in risks:
                if isinstance(risk, dict):
                    yield f"data: {json.dumps({'type': 'risk_step', 'data': risk})}\n\n"
                    await asyncio.sleep(0.05)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': f'风险分析失败: {str(e)}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
    async def generate():
        # 阶段1：规划 Agent（带搜索工具）
        yield f"data: {json.dumps({'type': 'status', 'data': '🤖 规划 Agent 正在思考（可调用搜索工具）...'})}\n\n"
        await asyncio.sleep(0.1)

        # 定义工具
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "当需要获取最新信息或验证事实时，使用此工具搜索互联网",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": "你是一个专业的任务规划师。你可以使用搜索工具获取最新信息来辅助规划。最终只输出任务的 JSON 数组，不要包含其他内容。"},
            {"role": "user", "content": f"目标：{req.goal}。请先决定是否需要搜索以获取更多信息，如果需要则调用搜索工具，最后输出完整的任务规划 JSON 数组。"}
        ]

        try:
            # 第一次调用，可能触发工具调用
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=1000
            )
            msg = response.choices[0].message

            # 如果模型要求调用工具
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    if func_name == "search":
                        query = func_args.get("query", "")
                        yield f"data: {json.dumps({'type': 'status', 'data': f'🔍 正在搜索：{query}'})}\n\n"
                        await asyncio.sleep(0.1)
                        search_result = search_tool(query)
                        yield f"data: {json.dumps({'type': 'search_result', 'data': search_result})}\n\n"
                        # 追加搜索结果到对话
                        messages.append(msg)
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": search_result})
                        # 二次调用获取最终规划
                        final_response = client.chat.completions.create(
                            model="glm-4-flash",
                            messages=messages,
                            temperature=0.2,
                            max_tokens=1000
                        )
                        plan_content = final_response.choices[0].message.content
            else:
                plan_content = msg.content

            if not plan_content:
                raise Exception("规划 Agent 未返回有效内容")

            # 提取 JSON 数组（支持 Markdown 代码块）
            json_match = re.search(r'\[.*\]', plan_content, re.DOTALL)
            if not json_match:
                raise Exception("未找到 JSON 数组")
            plan_str = json_match.group(0)

            # 解析 JSON，处理单引号等格式问题
            try:
                plan = json.loads(plan_str)
            except json.JSONDecodeError:
                plan_str = plan_str.replace("'", '"')
            try:
                plan = json.loads(plan_str)
            except Exception:
                raise Exception("JSON 解析失败")

            # 规范化计划列表：确保每个元素都是字典
            clean_plan = []
            for i, item in enumerate(plan):
                if isinstance(item, dict):
                    clean_plan.append(item)
                elif isinstance(item, str):
                    # 尝试再次解析字符串为 JSON
                    try:
                        sub_item = json.loads(item)
                        if isinstance(sub_item, dict):
                            clean_plan.append(sub_item)
                        else:
                            clean_plan.append({"title": f"任务{i+1}", "desc": item, "hours": 1})
                    except:
                        clean_plan.append({"title": f"任务{i+1}", "desc": item, "hours": 1})
                else:
                    # 其他类型强制转换
                    clean_plan.append({"title": f"任务{i+1}", "desc": str(item), "hours": 1})

                if not clean_plan:
                    raise Exception("规划步骤为空")
            plan = clean_plan

            # 逐条发送规划步骤
            for i, step in enumerate(plan):
                yield f"data: {json.dumps({'type': 'plan_step', 'data': step, 'index': i})}\n\n"
                await asyncio.sleep(0.05)

            # 阶段2：风控 Agent（与之前一致）
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

            for risk in risks:
                yield f"data: {json.dumps({'type': 'risk_step', 'data': risk})}\n\n"
                await asyncio.sleep(0.05)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': f'规划失败: {str(e)}'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ---------- 搜索工具 ----------
def search_tool(query: str) -> str:
    """使用 Tavily 搜索网络，返回结果摘要"""
    try:
        tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = tavily.search(query=query, max_results=3)
        results = response.get("results", [])
        if not results:
            return "未找到相关结果。"
        summary = "\n".join([f"- {r['title']}: {r['content'][:200]}" for r in results])
        return summary
    except Exception as e:
        return f"搜索失败: {str(e)}"