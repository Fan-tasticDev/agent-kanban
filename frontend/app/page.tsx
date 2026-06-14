'use client';
import { useState } from 'react';

interface Task {
  title: string;
  desc: string;
  hours: number;
}

interface Risk {
  step_index: number;
  step_title: string;
  risk: string;
  suggestion: string;
}

export default function Home() {
  const [goal, setGoal] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError('');
    try {
      // 使用编排接口，一次性获取规划和风险分析
      const res = await fetch('http://localhost:8000/orchestrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });
      const data = await res.json();
      if (data.plan) {
        setTasks(data.plan);
        setRisks(data.risks || []);
      } else {
        setError(data.error || '规划失败');
      }
    } catch (err) {
      setError('网络错误，请确认后端已启动');
    } finally {
      setLoading(false);
    }
  };

  // 根据 step_index 匹配风险到对应任务
  const getRiskForTask = (taskIndex: number): Risk | undefined => {
    return risks.find(r => r.step_index === taskIndex);
  };

  return (
    <main className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">🤖 多智能体任务规划看板</h1>

      {/* 输入区 */}
      <div className="flex gap-2 mb-8">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="输入你的目标，例如：组织一场线上技术分享会"
          className="flex-1 border rounded px-3 py-2"
          onKeyDown={(e) => e.key === 'Enter' && handlePlan()}
        />
        <button
          onClick={handlePlan}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Agent 协作中...' : '开始规划'}
        </button>
      </div>

      {error && <div className="text-red-500 mb-4 p-3 bg-red-50 rounded">{error}</div>}

      {loading && (
        <div className="mb-6 p-4 bg-gray-50 rounded border animate-pulse">
          <p className="text-sm text-gray-600">🤖 <strong>规划 Agent</strong> 正在拆解任务... 完成后将自动调用 🛡️ <strong>风控 Agent</strong> 分析风险...</p>
        </div>
      )}

      {/* 任务卡片 + 风险分析 */}
      <div className="space-y-6">
        {tasks.map((task, idx) => {
          const risk = getRiskForTask(idx);
          return (
            <div key={idx} className="border rounded-lg p-5 shadow-sm bg-white">
              <div className="flex items-start gap-3">
                {/* 步骤编号 */}
                <span className="bg-blue-100 text-blue-700 font-bold rounded-full w-8 h-8 flex items-center justify-center text-sm flex-shrink-0">
                  {idx + 1}
                </span>
                <div className="flex-1">
                  <h2 className="font-bold text-lg">{task.title}</h2>
                  <p className="text-gray-600 text-sm mt-1">{task.desc}</p>
                  <span className="inline-block text-xs bg-gray-100 px-2 py-1 rounded mt-2">
                    ⏱ 预估 {task.hours} 小时
                  </span>
                </div>
              </div>

              {/* 风险分析卡片 */}
              {risk && (
                <div className="mt-4 ml-11 border-l-4 border-orange-400 pl-4 py-2 bg-orange-50 rounded-r">
                  <p className="text-sm font-bold text-orange-700 flex items-center gap-1">
                    🛡️ 风险分析
                  </p>
                  <p className="text-sm text-orange-800 mt-1">
                    <strong>风险：</strong>{risk.risk}
                  </p>
                  <p className="text-sm text-green-700 mt-1">
                    <strong>建议：</strong>{risk.suggestion}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {tasks.length === 0 && !loading && (
        <div className="text-center text-gray-400 mt-20">
          输入一个目标，让 AI Agent 为你自动规划与评估风险
        </div>
      )}
    </main>
  );
}