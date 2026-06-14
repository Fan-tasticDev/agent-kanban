'use client';
import { useState } from 'react';

interface Task {
  title: string;
  desc: string;
  hours: number;
}

export default function Home() {
  const [goal, setGoal] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePlan = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://localhost:8000/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });
      const data = await res.json();
      if (data.plan) {
        setTasks(data.plan);
      } else {
        setError(data.error || '规划失败');
      }
    } catch (err) {
      setError('网络错误，请确认后端已启动');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">🤖 任务规划 Agent</h1>
      
      {/* 输入区 */}
      <div className="flex gap-2 mb-6">
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
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? '规划中...' : '开始规划'}
        </button>
      </div>

      {error && <div className="text-red-500 mb-4">{error}</div>}

      {/* 任务卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tasks.map((task, idx) => (
          <div key={idx} className="border rounded-lg p-4 shadow-sm bg-white">
            <h2 className="font-bold text-lg mb-2">{task.title}</h2>
            <p className="text-gray-700 text-sm mb-3">{task.desc}</p>
            <span className="text-xs bg-gray-100 px-2 py-1 rounded">
              ⏱ 预估 {task.hours} 小时
            </span>
          </div>
        ))}
      </div>
    </main>
  );
}