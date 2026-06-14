'use client';
import { useState } from 'react';

interface Task { title: string; desc: string; hours: number; }
interface Risk { step_index: number; step_title: string; risk: string; suggestion: string; }

export default function Home() {
  const [goal, setGoal] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [error, setError] = useState('');

  const getRiskForTask = (idx: number) => risks.find(r => r.step_index === idx);

  const handlePlan = async () => {
    if (!goal.trim()) return;
    setTasks([]); setRisks([]); setError(''); setLoading(true); setStatus(''); setSearchResults([]);
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${API_BASE_URL}/orchestrate-stream`, {
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
            try {
              const event = JSON.parse(line.slice(6));
              switch (event.type) {
                case 'status':
                  setStatus(event.data);
                  break;
                case 'search_result':
                  setSearchResults(prev => [...prev, event.data]);
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
      <h1 className="text-2xl font-bold mb-6">🤖 多智能体任务规划看板（带工具调用）</h1>

      <div className="flex gap-2 mb-4">
        <input value={goal} onChange={e => setGoal(e.target.value)} onKeyDown={e => e.key === 'Enter' && handlePlan()} placeholder="输入目标，如：组织一场线上技术分享会" className="flex-1 border rounded px-3 py-2" />
        <button onClick={handlePlan} disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50">{loading ? 'Agent 协作中...' : '开始规划'}</button>
      </div>

      {error && <div className="text-red-500 mb-4 p-3 bg-red-50 rounded">{error}</div>}

      {status && (
        <div className={`mb-4 p-3 rounded border ${loading ? 'bg-gray-50 animate-pulse' : 'bg-green-50 border-green-300'}`}>
          <p className="text-sm font-medium whitespace-pre-wrap">{status}</p>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded">
          <h3 className="text-sm font-bold text-blue-700 mb-2">🔍 搜索工具返回的结果：</h3>
          {searchResults.map((res, i) => (
            <pre key={i} className="text-xs text-blue-800 whitespace-pre-wrap mb-2">{res}</pre>
          ))}
        </div>
      )}

      <div className="space-y-6">
        {tasks.map((task, idx) => {
          const risk = getRiskForTask(idx);
          return (
            <div key={idx} className="border rounded-lg p-5 shadow-sm bg-white">
              <div className="flex items-start gap-3">
                <span className="bg-blue-100 text-blue-700 font-bold rounded-full w-8 h-8 flex items-center justify-center text-sm flex-shrink-0">{idx + 1}</span>
                <div className="flex-1">
                  <h2 className="font-bold text-lg">{task.title}</h2>
                  <p className="text-gray-600 text-sm mt-1">{task.desc}</p>
                  <span className="inline-block text-xs bg-gray-100 px-2 py-1 rounded mt-2">⏱ 预估 {task.hours} 小时</span>
                </div>
              </div>
              {risk && (
                <div className="mt-4 ml-11 border-l-4 border-orange-400 pl-4 py-2 bg-orange-50 rounded-r">
                  <p className="text-sm font-bold text-orange-700">🛡️ 风险分析</p>
                  <p className="text-sm text-orange-800 mt-1"><strong>风险：</strong>{risk.risk}</p>
                  <p className="text-sm text-green-700 mt-1"><strong>建议：</strong>{risk.suggestion}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}