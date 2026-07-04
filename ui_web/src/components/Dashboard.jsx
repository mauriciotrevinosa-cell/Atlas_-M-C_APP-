import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ChevronRight,
  Database,
  ExternalLink,
  Frame,
  Library,
  LogOut,
  MessageSquare,
  Monitor,
  Wallet,
  X,
} from 'lucide-react';
import { MMORender } from './MMORender.jsx';
import { OperationsWorkspace } from './OperationsWorkspace.jsx';
import { ResearchWorkspace } from './ResearchWorkspace.jsx';

const modules = [
  {
    label: 'Market Finance',
    legacyView: 'brain',
    detail: 'Unified synthesis, analytics, factors, risk, and strategy surface.',
  },
  {
    label: 'ARIA',
    legacyView: 'chat',
    detail: 'Local assistant, model routing, prompt rendering, and audit state.',
  },
  {
    label: 'MMO',
    legacyView: 'mmo',
    detail: 'Mau Market Ontology state plus quantum portfolio tooling.',
  },
  {
    label: 'Signals',
    legacyView: 'signal-terminal',
    detail: 'Whales, microstructure events, sentiment, and market intelligence.',
  },
  {
    label: 'RL Lab',
    legacyView: 'rl',
    detail: 'Feature expressions, reward schemes, and paper-mode policies.',
  },
  {
    label: 'Agents',
    legacyView: 'agents',
    detail: 'Agent gateway, permissions, checkpoints, and task audit trail.',
  },
  {
    label: 'Info',
    legacyView: 'info',
    detail: 'Live Atlas runtime catalog, APIs, providers, agents, docs, and web context.',
  },
  {
    label: 'Scenario Lab',
    legacyView: 'practice',
    detail: 'Black-swan manifests and market-state simulation context.',
  },
  {
    label: 'Viz Lab',
    legacyView: 'vizlab',
    detail: '3D system views, regime maps, and market graph endpoints.',
  },
];

const legacyModules = [
  { label: 'ARIA', view: 'chat', group: 'Core' },
  { label: 'Market Brain', view: 'brain', group: 'Core' },
  { label: 'MMO', view: 'mmo', group: 'Core' },
  { label: 'Info', view: 'info', group: 'Core' },
  { label: 'Agents', view: 'agents', group: 'Agents' },
  { label: 'Signals', view: 'signal-terminal', group: 'Signals' },
  { label: 'Trader', view: 'trader', group: 'Markets' },
  { label: 'Finance', view: 'finance', group: 'Markets' },
  { label: 'Derivatives', view: 'derivatives', group: 'Markets' },
  { label: 'Decision', view: 'decision', group: 'Markets' },
  { label: 'Indicators', view: 'indicators', group: 'Markets' },
  { label: 'Paper', view: 'paper', group: 'Markets' },
  { label: 'Viz Lab', view: 'vizlab', group: 'Visualization' },
  { label: 'Thought Map', view: 'thought', group: 'Visualization' },
  { label: 'RL Lab', view: 'rl', group: 'Labs' },
  { label: 'Playroom', view: 'playroom', group: 'Labs' },
  { label: 'Real Estate', view: 'realestate', group: 'Assets' },
];

const legacyUrl = (view) => `/desktop/index.html#view-${view}`;

const intakeApis = [
  {
    label: 'Macro',
    href: '/api/macro/series/GDP_REAL_GROWTH?start=2024-01-01&end=2024-12-31',
    detail: 'Atlas macro provider registry',
  },
  {
    label: 'Weather',
    href: '/api/context/weather?latitude=25.76&longitude=-80.19',
    detail: 'Environmental context layer',
  },
  {
    label: 'Prediction',
    href: '/api/prediction/markets?query=CPI&limit=5',
    detail: 'Read-only probability context',
  },
  {
    label: 'MMO Quantum',
    href: '/docs#/default/mmo_quantum_portfolio_api_mmo_quantum_portfolio_post',
    detail: 'Mau Market Ontology portfolio state',
  },
];

export const Dashboard = ({ onLogout }) => {
  const [selectedApp, setSelectedApp] = useState(null);
  const [legacyView, setLegacyView] = useState('chat');
  const [legacyOpen, setLegacyOpen] = useState(false);
  const [health, setHealth] = useState('checking');
  const [providerHealth, setProviderHealth] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [portfolioError, setPortfolioError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const loadHealth = async () => {
      try {
        const healthResponse = await fetch('/api/health');
        if (!healthResponse.ok) throw new Error(`HTTP ${healthResponse.status}`);
        await healthResponse.json();
        if (!cancelled) setHealth('online');
      } catch (error) {
        if (!cancelled) setHealth('offline');
      }
    };

    const loadProviders = async () => {
      try {
        const providerResponse = await fetch('/api/providers/health?limit=5');
        if (!providerResponse.ok) throw new Error(`HTTP ${providerResponse.status}`);
        const providerPayload = await providerResponse.json();
        if (!cancelled) setProviderHealth(providerPayload);
      } catch (error) {
        if (!cancelled) setProviderHealth(null);
      }
    };

    const loadPortfolio = async () => {
      try {
        const [activeResponse, uploadedResponse] = await Promise.all([
          fetch('/api/portfolio'),
          fetch('/api/portfolio/uploaded'),
        ]);
        if (!activeResponse.ok) throw new Error(`Portfolio HTTP ${activeResponse.status}`);
        const active = await activeResponse.json();
        let selected = active;
        if (!active.has_active_session && uploadedResponse.ok) {
          const uploaded = await uploadedResponse.json();
          if (uploaded.has_uploaded_portfolio) {
            selected = {
              ...uploaded,
              status: 'cached',
              mode: 'LIVE',
              updated_at: uploaded.as_of ?? null,
              error: null,
              capital: null,
              total_equity: uploaded.total_equity ?? null,
            };
          }
        }
        if (!cancelled) {
          setPortfolio(selected);
          setPortfolioError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setPortfolio(null);
          setPortfolioError(error.message);
        }
      }
    };

    loadHealth();
    loadProviders();
    loadPortfolio();
    return () => {
      cancelled = true;
    };
  }, []);

  const providerStatus = providerHealth?.status ?? 'unknown';
  const portfolioStatus = portfolioError ? 'unavailable' : (portfolio?.status ?? 'unavailable');
  const hasNumericValue = (value) => value !== null && value !== undefined && value !== ''
    && Number.isFinite(Number(value));
  const portfolioTotal = hasNumericValue(portfolio?.total_equity)
    ? Number(portfolio.total_equity)
    : null;
  const portfolioPositions = Array.isArray(portfolio?.positions) ? portfolio.positions : [];
  const formatMoney = (value) => new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
  const providerStatusClass = {
    online: 'bg-emerald-500',
    degraded: 'bg-amber-500',
    critical: 'bg-rose-500',
    unknown: 'bg-slate-400',
  }[providerStatus] ?? 'bg-slate-400';

  const openLegacyView = (view) => {
    setLegacyView(view);
    setLegacyOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#fcfcfc] p-6 text-slate-950 md:p-12">
      <header className="mb-10 flex items-center justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            System {health}
          </p>
          <h2 className="text-4xl font-light tracking-tight">
            Bienvenido, <span className="font-normal italic">Mauricio</span>
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => openLegacyView('dashboard')}
            className="atlas-glass flex h-12 w-12 items-center justify-center rounded-2xl text-slate-700"
            title="Open desktop modules"
          >
            <Monitor size={22} />
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="atlas-glass flex h-12 w-12 items-center justify-center rounded-2xl text-slate-700"
            title="Lock"
          >
            <LogOut size={22} />
          </button>
        </div>
      </header>

      <main className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <motion.button
          type="button"
          layoutId="wallet"
          onClick={() => setSelectedApp('wallet')}
          className="atlas-glass atlas-zoom-card col-span-1 rounded-2xl p-8 text-left lg:col-span-8"
        >
          <div className="mb-10 flex items-start justify-between">
            <span className="rounded-xl bg-blue-600 p-4 text-white shadow-lg shadow-blue-200">
              <Wallet size={28} />
            </span>
            <ChevronRight className="text-slate-400" />
          </div>
          <div className="flex items-center gap-2 text-sm uppercase tracking-widest text-slate-500">
            <span>Portfolio equity</span>
            <span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] font-semibold">
              {portfolioStatus} · {portfolio?.source ?? 'none'}
            </span>
          </div>
          <h3 className="mt-2 text-5xl font-semibold tracking-tight">
            {portfolioTotal === null || portfolioStatus === 'unavailable'
              ? 'No portfolio data'
              : formatMoney(portfolioTotal)}
          </h3>
          <p className="mt-3 text-sm text-slate-500">
            {portfolioError
              ? `UNAVAILABLE: ${portfolioError}`
              : `${portfolio?.mode ?? 'LIVE'} · ${portfolioPositions.length} positions · ${portfolio?.updated_at ?? 'no timestamp'}`}
          </p>
        </motion.button>

        <motion.button
          type="button"
          layoutId="library"
          onClick={() => setSelectedApp('library')}
          className="atlas-glass-dark atlas-zoom-card col-span-1 flex min-h-64 flex-col justify-between rounded-2xl p-8 text-left lg:col-span-4"
        >
          <Library size={32} className="text-blue-300" />
          <div>
            <h4 className="text-2xl font-light italic text-white">La Biblioteca</h4>
            <p className="mt-1 text-xs uppercase tracking-widest text-slate-400">
              Explore Modules
            </p>
          </div>
        </motion.button>

        <section className="atlas-glass col-span-1 rounded-lg p-6 lg:col-span-12">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
                <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-950 text-white">
                <Database size={22} />
              </span>
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  Provider Registry
                </p>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${providerStatusClass}`} />
                  <h4 className="text-2xl font-semibold capitalize tracking-tight">
                    {providerStatus}
                  </h4>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-right">
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">Channels</p>
                <p className="text-2xl font-semibold">{providerHealth?.channels_total ?? '-'}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">Available</p>
                <p className="text-2xl font-semibold">{providerHealth?.providers_available ?? '-'}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-widest text-slate-500">Total</p>
                <p className="text-2xl font-semibold">{providerHealth?.providers_total ?? '-'}</p>
              </div>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-5">
            {(providerHealth?.channels ?? []).map((channel) => (
              <div key={channel.name} className="rounded-lg border border-white/60 bg-white/45 p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500">
                  {channel.name.replace('_', ' ')}
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {channel.providers_available}/{channel.providers_total}
                </p>
              </div>
            ))}
          </div>
        </section>

        <ResearchWorkspace providerHealth={providerHealth} />

        <OperationsWorkspace />

        <section className="atlas-glass col-span-1 rounded-lg p-6 lg:col-span-12">
          <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">
                Unified Interface
              </p>
              <h4 className="text-2xl font-semibold tracking-tight">
                Desktop modules inside Atlas Web
              </h4>
            </div>
            <button
              type="button"
              onClick={() => openLegacyView(legacyView)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-black"
            >
              <Frame size={17} />
              Open Active Module
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
            {legacyModules.map((module) => {
              const active = module.view === legacyView;
              return (
                <button
                  key={module.view}
                  type="button"
                  onClick={() => openLegacyView(module.view)}
                  className={`rounded-lg border p-3 text-left transition ${
                    active
                      ? 'border-slate-950 bg-slate-950 text-white'
                      : 'border-white/70 bg-white/55 text-slate-800 hover:-translate-y-0.5 hover:bg-white'
                  }`}
                >
                  <p className="text-sm font-semibold">{module.label}</p>
                  <p className={`mt-1 text-xs uppercase tracking-widest ${active ? 'text-slate-300' : 'text-slate-500'}`}>
                    {module.group}
                  </p>
                </button>
              );
            })}
          </div>
        </section>

        <section className="atlas-glass col-span-1 rounded-lg p-6 lg:col-span-12">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-500">
                Atlas Data Intake
              </p>
              <h4 className="text-2xl font-semibold tracking-tight">
                Provider-backed context
              </h4>
            </div>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-emerald-700">
              Read-only
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            {intakeApis.map((api) => (
              <a
                key={api.label}
                href={api.href}
                className="rounded-lg border border-white/60 bg-white/45 p-4 transition hover:-translate-y-0.5 hover:bg-white/70"
              >
                <p className="text-lg font-semibold text-slate-950">{api.label}</p>
                <p className="mt-1 text-sm text-slate-600">{api.detail}</p>
              </a>
            ))}
          </div>
        </section>

        <section className="atlas-glass relative col-span-1 h-[420px] overflow-hidden rounded-lg p-4 lg:col-span-12">
          <div className="pointer-events-none absolute left-8 top-8 z-10">
            <h4 className="text-xl font-light tracking-widest text-white">
              MAUS MARKET ONTOLOGY
            </h4>
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-300">
              Quantum Engine Preview
            </span>
          </div>
          <MMORender />
        </section>
      </main>

      <motion.button
        type="button"
        onClick={() => openLegacyView('chat')}
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.96 }}
        className="atlas-glass-dark fixed bottom-8 right-8 z-50 flex h-16 w-16 items-center justify-center rounded-2xl shadow-2xl"
        aria-label="Open ARIA"
      >
        <MessageSquare size={28} className="text-blue-300" />
      </motion.button>

      <AnimatePresence>
        {legacyOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[120] flex flex-col bg-slate-950 text-white"
          >
            <div className="flex flex-col gap-3 border-b border-white/10 bg-slate-950/95 px-4 py-3 md:flex-row md:items-center md:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/20 text-blue-200">
                  <Frame size={20} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-widest text-slate-400">
                    Unified Atlas Surface
                  </p>
                  <h3 className="truncate text-lg font-semibold">
                    {legacyModules.find((module) => module.view === legacyView)?.label ?? 'Desktop Module'}
                  </h3>
                </div>
              </div>

              <div className="flex items-center gap-2 overflow-x-auto">
                {legacyModules.map((module) => (
                  <button
                    key={module.view}
                    type="button"
                    onClick={() => setLegacyView(module.view)}
                    className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-widest transition ${
                      module.view === legacyView
                        ? 'bg-white text-slate-950'
                        : 'bg-white/10 text-slate-300 hover:bg-white/20'
                    }`}
                  >
                    {module.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={legacyUrl(legacyView)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-slate-200 transition hover:bg-white/20"
                  title="Open in a new tab"
                >
                  <ExternalLink size={18} />
                </a>
                <button
                  type="button"
                  onClick={() => setLegacyOpen(false)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white text-slate-950 transition hover:bg-slate-200"
                  aria-label="Close desktop module"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <iframe
              key={legacyView}
              title={`Atlas desktop ${legacyView}`}
              src={legacyUrl(legacyView)}
              className="min-h-0 flex-1 border-0 bg-slate-950"
            />
          </motion.div>
        )}

        {selectedApp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="atlas-glass fixed inset-0 z-[100] overflow-auto p-8 backdrop-blur-3xl"
          >
            <button
              type="button"
              onClick={() => setSelectedApp(null)}
              className="absolute right-8 top-8 rounded-2xl bg-slate-950 p-4 text-white transition hover:bg-black"
              aria-label="Close"
            >
              <X size={24} />
            </button>

            <div className="mx-auto flex min-h-full max-w-6xl flex-col justify-center">
              {selectedApp === 'wallet' && (
                <section>
                  <h2 className="mb-4 text-6xl font-semibold tracking-tight">
                    Mi Cartera
                  </h2>
                  <p className="mb-10 max-w-2xl text-xl italic text-slate-600">
                    Atlas only displays portfolio values returned by the local API.
                    Missing cash, debt, or positions remain unavailable instead of being estimated.
                  </p>
                  <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                    <div className="atlas-glass rounded-2xl p-8">
                      <p className="text-xs uppercase tracking-widest text-slate-500">Equity</p>
                      <p className="mt-4 text-3xl font-semibold">
                        {portfolioTotal === null || portfolioStatus === 'unavailable'
                          ? 'UNAVAILABLE'
                          : formatMoney(portfolioTotal)}
                      </p>
                    </div>
                    <div className="atlas-glass rounded-2xl p-8">
                      <p className="text-xs uppercase tracking-widest text-slate-500">Cash / capital</p>
                      <p className="mt-4 text-3xl font-semibold">
                        {hasNumericValue(portfolio?.capital) && portfolioStatus !== 'unavailable'
                          ? formatMoney(Number(portfolio.capital))
                          : 'UNAVAILABLE'}
                      </p>
                    </div>
                    <div className="atlas-glass rounded-2xl p-8">
                      <p className="text-xs uppercase tracking-widest text-slate-500">Debt</p>
                      <p className="mt-4 text-3xl font-semibold">UNAVAILABLE</p>
                    </div>
                  </div>
                  <div className="mt-6 atlas-glass rounded-2xl p-8">
                    <p className="text-xs uppercase tracking-widest text-slate-500">Positions</p>
                    {portfolioPositions.length === 0 ? (
                      <p className="mt-4 text-slate-600">No positions were returned by Atlas.</p>
                    ) : (
                      <div className="mt-4 grid gap-3">
                        {portfolioPositions.map((position, index) => (
                          <div key={`${position.symbol ?? 'position'}-${index}`} className="flex justify-between border-b border-slate-200 pb-3">
                            <span className="font-semibold">{position.symbol ?? 'Unknown'}</span>
                            <span>{Number.isFinite(Number(position.market_value)) ? formatMoney(Number(position.market_value)) : 'UNAVAILABLE'}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              )}

              {selectedApp === 'library' && (
                <section>
                  <h2 className="mb-8 text-6xl font-semibold tracking-tight">
                    La Biblioteca
                  </h2>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                    {modules.map((module) => (
                      <button
                        key={module.label}
                        type="button"
                        onClick={() => {
                          if (module.legacyView) {
                            setSelectedApp(null);
                            openLegacyView(module.legacyView);
                          }
                        }}
                        className="atlas-glass rounded-lg p-5 text-left text-slate-800 transition hover:-translate-y-0.5"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-lg font-semibold">{module.label}</p>
                          <ExternalLink size={16} className="mt-1 text-slate-500" />
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-600">
                          {module.detail}
                        </p>
                      </button>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
