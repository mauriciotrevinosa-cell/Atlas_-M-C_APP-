import { useEffect, useState } from 'react';
import { Activity, Play, RefreshCw, Save } from 'lucide-react';

const readJson = async (response) => {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail?.join?.('; ') ?? payload.detail ?? `HTTP ${response.status}`);
  return payload;
};

export const OperationsWorkspace = () => {
  const [workflows, setWorkflows] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [symbol, setSymbol] = useState('SPY');
  const [timeframe, setTimeframe] = useState('3mo');
  const [run, setRun] = useState(null);
  const [state, setState] = useState('loading');
  const [error, setError] = useState(null);

  const load = async () => {
    setState('loading');
    try {
      const payload = await readJson(await fetch('/api/operations/workflows'));
      setWorkflows(payload.items ?? []);
      setSelectedId((current) => current || payload.items?.[0]?.workflow_id || '');
      setError(null);
      setState('ready');
    } catch (loadError) {
      setError(loadError.message);
      setState('unavailable');
    }
  };

  useEffect(() => { load(); }, []);

  const selected = workflows.find((item) => item.workflow_id === selectedId);

  const toggleStep = (stepId) => {
    setWorkflows((items) => items.map((workflow) => workflow.workflow_id !== selectedId
      ? workflow
      : {
          ...workflow,
          steps: workflow.steps.map((step) => step.step_id === stepId
            ? { ...step, enabled: !step.enabled }
            : step),
        }));
  };

  const save = async () => {
    if (!selected) return;
    setState('saving');
    try {
      const saved = await readJson(await fetch(`/api/operations/workflows/${selected.workflow_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selected.name, description: selected.description, steps: selected.steps }),
      }));
      setWorkflows((items) => items.map((item) => item.workflow_id === saved.workflow_id ? saved : item));
      setError(null);
      setState('ready');
    } catch (saveError) {
      setError(saveError.message);
      setState('unavailable');
    }
  };

  const execute = async () => {
    if (!selected) return;
    setState('running');
    setRun(null);
    try {
      const payload = await readJson(await fetch(`/api/operations/workflows/${selected.workflow_id}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputs: { symbol, timeframe } }),
      }));
      setRun(payload);
      setError(null);
      setState('ready');
    } catch (runError) {
      setError(runError.message);
      setState('unavailable');
    }
  };

  return (
    <section className="atlas-glass col-span-1 rounded-lg p-6 lg:col-span-12">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-slate-500">
            <Activity size={15} /> Atlas Operations Workspace
          </div>
          <h4 className="mt-2 text-2xl font-semibold">Manual workflow</h4>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            The same persisted workflow contract will be used by ARIA. Every result exposes its source,
            mode, timestamp, and error instead of silently substituting demo values.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={load} className="rounded-lg border border-slate-300 bg-white px-3 py-2" title="Reload">
            <RefreshCw size={17} />
          </button>
          <button type="button" onClick={save} disabled={!selected || state === 'saving'} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 font-semibold disabled:opacity-50">
            <Save size={17} /> Save
          </button>
          <button type="button" onClick={execute} disabled={!selected || state === 'running'} className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 font-semibold text-white disabled:opacity-50">
            <Play size={17} /> {state === 'running' ? 'Running…' : 'Run'}
          </button>
        </div>
      </div>

      {error && <div className="mt-4 rounded-lg bg-rose-100 p-3 text-sm text-rose-800">UNAVAILABLE: {error}</div>}

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div>
          <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Workflow</label>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 bg-white p-3">
            {workflows.map((workflow) => <option key={workflow.workflow_id} value={workflow.workflow_id}>{workflow.name} · v{workflow.version}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Symbol</label>
          <input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} className="mt-2 w-full rounded-lg border border-slate-300 bg-white p-3" />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-widest text-slate-500">Timeframe</label>
          <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-300 bg-white p-3">
            {['1mo', '3mo', '6mo', '1y', '2y'].map((value) => <option key={value}>{value}</option>)}
          </select>
        </div>
      </div>

      <div className="mt-6 grid gap-3">
        {(selected?.steps ?? []).map((step, index) => (
          <label key={step.step_id} className="flex items-center justify-between rounded-lg border border-white/70 bg-white/55 p-4">
            <div>
              <p className="font-semibold">{index + 1}. {step.name}</p>
              <p className="mt-1 text-xs uppercase tracking-widest text-slate-500">{step.handler}</p>
            </div>
            <input type="checkbox" checked={step.enabled} onChange={() => toggleStep(step.step_id)} className="h-5 w-5" />
          </label>
        ))}
      </div>

      {run && (
        <div className="mt-6 rounded-lg bg-slate-950 p-5 text-white">
          <div className="flex flex-wrap justify-between gap-2">
            <p className="font-semibold">Run {run.status}</p>
            <p className="text-xs text-slate-400">{run.run_id}</p>
          </div>
          <div className="mt-4 grid gap-3">
            {run.steps.map((step) => (
              <details key={step.step_id} className="rounded-lg bg-white/10 p-4" open>
                <summary className="cursor-pointer font-semibold">{step.name} · {step.status}</summary>
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-400">{step.source} · {step.mode} · {step.updated_at}</p>
                {step.error && <p className="mt-3 text-rose-300">{step.error}</p>}
                {step.data && <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-200">{JSON.stringify(step.data, null, 2)}</pre>}
              </details>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
