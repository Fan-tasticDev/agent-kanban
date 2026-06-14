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
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  const getRiskForTask = (taskIndex: number): Risk | undefined => {
    return risks.find(r => r.step_index === taskIndex);
  };

  const handlePlan = async () => {
    if (!goal.trim()) return;
    setTasks([]);
    setRisks([]);
    setError('');
    setLoading(true);
    setStatus('');

    try {
      const response = await fetch('http://localhost:8000/orchestrate-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });

      if (!response.ok || !response.body) throw new Error('网络错误');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const event = JSON.parse(jsonStr);
              switch (event.type) {
                case 'status':
                  setStatus(event.data);
                  break;
                case 'plan_step':
                  setTasks(prev => [...prev, event.data]);
                  break;
                case 'risk_step':
                  setRisks(prev => [...prev, event.data]);
                  break;
                case 'error':
                  setError(event.data);
                  break;
                case 'done':
                  setStatus('✅ 分析完成');
                  break;
              }
            } catch (e) {}
          }
        }
      }
    } catch (err: any) {
      setError(err.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">🤖 多智能体任务规划看板</h1>

      {/* 输入区 */}
      <div className="flex gap-2 mb-4">
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

      {/* 状态指示器 */}
      {status && (
        <div className={`mb-6 p-3 rounded border ${loading ? 'bg-gray-50 animate-pulse' : 'bg-green-50 border-green-300'}`}>
          <p className="text-sm font-medium">{status}</p>
        </div>
      )}

      {/* 任务卡片 + 风险分析 */}
      <div className="space-y-6">
        {tasks.map((task, idx) => {
          const risk = getRiskForTask(idx);
          return (
            <div key={idx} className="border rounded-lg p-5 shadow-sm bg-white transition-all duration-300">
              <div className="flex items-start gap-3">
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