import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BarChart3,
  Bot,
  BrainCircuit,
  FileCode2,
  GitBranch,
  RadioTower,
  ShieldCheck,
  TrendingUp,
  Workflow,
} from 'lucide-react';

const endpoints = {
  prediction: '/api/prediction/markets?query=inflation&limit=4',
  signals: '/api/signals?limit=4',
  whales: '/api/signals/whales?limit=3',
  agents: '/api/agents/status',
  pixel: '/api/agents/pixel-workspace',
};

const fetchJson = async (url) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};

const statusTone = {
  online: 'bg-emerald-500',
  available: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  offline: 'bg-rose-500',
  unavailable: 'bg-slate-400',
  ready: 'bg-emerald-500',
  standby: 'bg-amber-500',
  missing: 'bg-rose-500',
  unknown: 'bg-slate-400',
};

const compactNumber = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-';
  return new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(value);
};

const formatAge = (seconds) => {
  if (typeof seconds !== 'number' || Number.isNaN(seconds)) return '-';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
};

const shortText = (value, limit = 42) => {
  if (!value) return '-';
  const text = String(value);
  if (text.length <= limit) return text;
  return `${text.slice(0, limit - 3)}...`;
};

const operationLinks = [
  {
    label: 'Agent Gateway',
    href: '/api/agents/status',
    detail: 'Preflight permissions, checkpoint logging, and paper-mode gates.',
    icon: ShieldCheck,
  },
  {
    label: 'Repo Intelligence',
    href: '/api/agents',
    detail: 'Repo maps, module summaries, imports, symbols, and graph context.',
    icon: GitBranch,
  },
  {
    label: 'Prompt + Models',
    href: '/api/aria/models',
    detail: 'Strict prompt rendering and provider catalog status for ARIA.',
    icon: FileCode2,
  },
  {
    label: 'Scenario State',
    href: '/api/signal/scenarios',
    detail: 'Market-state tokens and black-swan run manifests for simulations.',
    icon: Workflow,
  },
  {
    label: 'Quant + RL',
    href: '/docs',
    detail: 'Feature expressions, QUBO portfolio state, rewards, and actions.',
    icon: BrainCircuit,
  },
];

export const ResearchWorkspace = ({ providerHealth }) => {
  const [marketPayload, setMarketPayload] = useState(null);
  const [signalsPayload, setSignalsPayload] = useState(null);
  const [whalesPayload, setWhalesPayload] = useState(null);
  const [agentsPayload, setAgentsPayload] = useState(null);
  const [pixelPayload, setPixelPayload] = useState(null);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    let cancelled = false;

    const load = async (key, url, setter) => {
      try {
        const payload = await fetchJson(url);
        if (!cancelled) setter(payload);
      } catch (error) {
        if (!cancelled) setErrors((prev) => ({ ...prev, [key]: error.message }));
      }
    };

    load('prediction', endpoints.prediction, setMarketPayload);
    load('signals', endpoints.signals, setSignalsPayload);
    load('whales', endpoints.whales, setWhalesPayload);
    load('agents', endpoints.agents, setAgentsPayload);
    load('pixel', endpoints.pixel, setPixelPayload);

    return () => {
      cancelled = true;
    };
  }, []);

  const markets = marketPayload?.markets ?? marketPayload?.items ?? [];
  const signals = signalsPayload?.items ?? [];
  const whales = Array.isArray(whalesPayload) ? whalesPayload : [];
  const agentsStatus = agentsPayload?.available ? 'available' : 'unavailable';
  const providerStatus = providerHealth?.status ?? 'unknown';
  const pixelOffice = pixelPayload?.office ?? {};
  const pixelDesks = pixelOffice.desks ?? [];
  const pixelTeams = pixelPayload?.teams ?? [];
  const pixelSessions = pixelPayload?.claude?.sessions_recent ?? [];
  const pixelRepo = pixelPayload?.pixel_agents_repo ?? {};
  const pixelStatus = errors.pixel ? 'offline' : (pixelPayload?.status ?? 'unknown');

  const workspaceStats = useMemo(
    () => [
      {
        label: 'Providers',
        value: providerHealth?.providers_available ?? '-',
        detail: `${providerHealth?.providers_total ?? '-'} total`,
        icon: RadioTower,
        status: providerStatus,
      },
      {
        label: 'Markets',
        value: markets.length,
        detail: errors.prediction ? 'offline' : 'read-only',
        icon: BarChart3,
        status: errors.prediction ? 'offline' : 'online',
      },
      {
        label: 'Signals',
        value: signals.length,
        detail: errors.signals ? 'not started' : 'feed',
        icon: Activity,
        status: errors.signals ? 'degraded' : 'online',
      },
      {
        label: 'Agents',
        value: agentsPayload?.agents_count ?? '-',
        detail: agentsStatus,
        icon: Bot,
        status: agentsStatus,
      },
      {
        label: 'Ops Desk',
        value: pixelOffice.desks_ready ?? '-',
        detail: `${pixelPayload?.claude?.active_sessions ?? 0} active sessions`,
        icon: GitBranch,
        status: pixelStatus,
      },
    ],
    [
      agentsPayload,
      agentsStatus,
      errors.pixel,
      errors.prediction,
      errors.signals,
      markets.length,
      pixelOffice.desks_ready,
      pixelPayload,
      pixelStatus,
      providerHealth,
      providerStatus,
      signals.length,
    ],
  );

  return (
    <section className="atlas-glass col-span-1 rounded-lg p-6 lg:col-span-12">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            Research Workspace
          </p>
          <h4 className="text-2xl font-semibold tracking-tight">
            Atlas Market Desk
          </h4>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-white/60 bg-white/50 px-3 py-2 text-sm font-semibold text-slate-700">
          <ShieldCheck size={16} />
          Paper / read-only
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
        {workspaceStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="rounded-lg border border-white/70 bg-white/55 p-4">
              <div className="flex items-start justify-between gap-3">
                <Icon size={20} className="text-slate-600" />
                <span className={`mt-1 h-2.5 w-2.5 rounded-full ${statusTone[stat.status] ?? statusTone.unknown}`} />
              </div>
              <p className="mt-5 text-xs uppercase tracking-widest text-slate-500">
                {stat.label}
              </p>
              <p className="mt-1 text-2xl font-semibold">{stat.value}</p>
              <p className="mt-1 text-sm text-slate-600">{stat.detail}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
        {operationLinks.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.label}
              href={item.href}
              className="rounded-lg border border-white/70 bg-white/50 p-4 transition hover:-translate-y-0.5 hover:bg-white"
            >
              <div className="mb-4 flex items-start justify-between gap-3">
                <Icon size={18} className="text-slate-600" />
                <span className="rounded bg-emerald-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-widest text-emerald-700">
                  Atlas
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-950">{item.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</p>
            </a>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.85fr)]">
        <div className="rounded-lg border border-white/70 bg-white/55 p-5">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">
                Pixel Operations
              </p>
              <h5 className="text-xl font-semibold tracking-tight text-slate-950">
                Atlas agent floor
              </h5>
            </div>
            <a
              href="/api/agents/pixel-workspace"
              className="inline-flex items-center justify-center rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-white transition hover:bg-black"
            >
              API
            </a>
          </div>

          {errors.pixel && (
            <p className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {errors.pixel}
            </p>
          )}

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
              <p className="text-xs uppercase tracking-widest text-slate-500">Desks</p>
              <p className="mt-2 text-2xl font-semibold">
                {pixelOffice.desks_ready ?? '-'}/{pixelOffice.desks_total ?? '-'}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
              <p className="text-xs uppercase tracking-widest text-slate-500">Teams</p>
              <p className="mt-2 text-2xl font-semibold">{pixelPayload?.teams_total ?? '-'}</p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
              <p className="text-xs uppercase tracking-widest text-slate-500">Agents</p>
              <p className="mt-2 text-2xl font-semibold">{pixelPayload?.agents_total ?? '-'}</p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
              <p className="text-xs uppercase tracking-widest text-slate-500">Pixel Repo</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">
                {pixelRepo.commit ? `${pixelRepo.branch ?? 'main'} @ ${pixelRepo.commit}` : pixelRepo.status ?? '-'}
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            {pixelDesks.slice(0, 6).map((desk) => (
              <div key={desk.id} className="rounded-lg border border-slate-200/70 bg-white/65 p-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-950">{desk.label}</p>
                  <span className={`mt-1 h-2.5 w-2.5 rounded-full ${statusTone[desk.status] ?? statusTone.unknown}`} />
                </div>
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-500">
                  {desk.paths_ready}/{desk.paths_total} paths
                </p>
                <p className="mt-2 text-sm text-slate-600">
                  {desk.agents.length > 0 ? desk.agents.join(', ') : desk.role}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/70 bg-white/55 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">
                Agent Sessions
              </p>
              <h5 className="text-xl font-semibold tracking-tight text-slate-950">
                Claude workspace watch
              </h5>
            </div>
            <span className={`h-2.5 w-2.5 rounded-full ${statusTone[pixelStatus] ?? statusTone.unknown}`} />
          </div>

          <div className="space-y-3">
            {pixelSessions.length === 0 && (
              <p className="rounded-lg border border-slate-200/70 bg-white/65 p-3 text-sm text-slate-500">
                {errors.pixel ?? 'No local Claude sessions detected for Atlas yet'}
              </p>
            )}
            {pixelSessions.slice(0, 4).map((session) => (
              <div key={session.session_id} className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-950">{session.project}</p>
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs uppercase tracking-widest text-slate-600">
                    {session.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{shortText(session.last_event, 70)}</p>
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-500">
                  {formatAge(session.age_seconds)} ago / {session.size_kb} KB
                </p>
              </div>
            ))}
          </div>

          <div className="mt-4 space-y-2">
            {pixelTeams.slice(0, 4).map((team) => (
              <div key={team.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200/70 bg-white/65 px-3 py-2">
                <div>
                  <p className="text-sm font-semibold text-slate-950">{team.label}</p>
                  <p className="text-xs text-slate-500">{shortText(team.mission, 52)}</p>
                </div>
                <span className="shrink-0 rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
                  {team.members_total}/{team.expected_total}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-lg border border-white/70 bg-white/55 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h5 className="text-sm font-semibold uppercase tracking-widest text-slate-600">
              Prediction Context
            </h5>
            <TrendingUp size={18} className="text-slate-500" />
          </div>
          <div className="space-y-3">
            {markets.length === 0 && (
              <p className="text-sm text-slate-500">{errors.prediction ?? 'No markets loaded'}</p>
            )}
            {markets.slice(0, 4).map((market) => (
              <a
                key={market.id ?? market.condition_id ?? market.slug ?? market.question}
                href={`/api/prediction/resolve?identifier=${encodeURIComponent(
                  market.id ?? market.condition_id ?? market.slug ?? market.question,
                )}`}
                className="block rounded-lg border border-slate-200/70 bg-white/70 p-3 transition hover:-translate-y-0.5 hover:bg-white"
              >
                <p className="line-clamp-2 text-sm font-semibold text-slate-900">
                  {market.question ?? market.title ?? market.slug ?? 'Market'}
                </p>
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-500">
                  {compactNumber(market.yes_price ?? market.probability ?? market.price)}
                </p>
              </a>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/70 bg-white/55 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h5 className="text-sm font-semibold uppercase tracking-widest text-slate-600">
              Signal Feed
            </h5>
            <Activity size={18} className="text-slate-500" />
          </div>
          <div className="space-y-3">
            {signals.length === 0 && (
              <p className="text-sm text-slate-500">{errors.signals ?? 'No signals loaded'}</p>
            )}
            {signals.slice(0, 4).map((signal) => (
              <div key={signal.id} className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {signal.ticker ?? signal.category ?? 'Signal'}
                  </p>
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs uppercase tracking-widest text-slate-600">
                    {signal.sentiment ?? signal.category ?? 'feed'}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-slate-600">
                  {signal.title ?? signal.body ?? signal.summary ?? 'Signal event'}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/70 bg-white/55 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h5 className="text-sm font-semibold uppercase tracking-widest text-slate-600">
              Whale / Agent Watch
            </h5>
            <Bot size={18} className="text-slate-500" />
          </div>
          <div className="space-y-3">
            {whales.length === 0 && (
              <p className="text-sm text-slate-500">{errors.whales ?? 'No whale events loaded'}</p>
            )}
            {whales.slice(0, 3).map((event) => (
              <div key={event.id} className="rounded-lg border border-slate-200/70 bg-white/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {event.ticker ?? 'Event'}
                  </p>
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs uppercase tracking-widest text-slate-600">
                    {event.type ?? event.event_type ?? 'whale'}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600">
                  {event.amount ? `$${compactNumber(event.amount)}` : event.source ?? 'Signal Terminal'}
                </p>
              </div>
            ))}
            <a
              href="/api/agents"
              className="flex items-center justify-between rounded-lg border border-slate-200/70 bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-black"
            >
              Agent registry
              <Bot size={16} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};
