import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronRight, Library, MessageSquare, Wallet, X } from 'lucide-react';
import { MMORender } from './MMORender';

const walletStats = [
  { label: 'Cash', value: '$1.2M' },
  { label: 'Debt', value: '$400K' },
  { label: 'Invested', value: '$1.6M' },
];

export const Dashboard = () => {
  const [selectedApp, setSelectedApp] = useState(null);

  return (
    <div className="min-h-screen bg-[#fcfcfc] p-6 text-slate-950 md:p-12">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">
            System Active
          </p>
          <h2 className="text-4xl font-light tracking-tight">
            Bienvenido, <span className="font-normal italic">Mauricio</span>
          </h2>
        </div>
        <div className="atlas-glass flex h-14 w-14 items-center justify-center rounded-2xl">
          <div className="h-9 w-9 rounded-xl bg-slate-200" />
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
          <p className="text-sm uppercase tracking-widest text-slate-500">
            Total Net Worth
          </p>
          <h3 className="mt-2 text-5xl font-semibold tracking-tight">
            $2,450,890.00 <span className="text-lg font-light text-slate-500">MXN</span>
          </h3>
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

        <section className="atlas-glass relative col-span-1 h-[420px] overflow-hidden rounded-2xl p-4 lg:col-span-12">
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
        whileHover={{ scale: 1.06 }}
        whileTap={{ scale: 0.96 }}
        className="atlas-glass-dark fixed bottom-8 right-8 z-50 flex h-16 w-16 items-center justify-center rounded-2xl shadow-2xl"
        aria-label="Open ARIA"
      >
        <MessageSquare size={28} className="text-blue-300" />
      </motion.button>

      <AnimatePresence>
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
                    Detailed capital, debt, and investment breakdown. Replace
                    these placeholder values with Atlas finance endpoints.
                  </p>
                  <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                    {walletStats.map((stat) => (
                      <div key={stat.label} className="atlas-glass rounded-2xl p-8">
                        <p className="text-xs uppercase tracking-widest text-slate-500">
                          {stat.label}
                        </p>
                        <p className="mt-4 text-3xl font-semibold">{stat.value}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {selectedApp === 'library' && (
                <section>
                  <h2 className="mb-4 text-6xl font-semibold tracking-tight">
                    La Biblioteca
                  </h2>
                  <p className="max-w-2xl text-xl italic text-slate-600">
                    Future module launcher for Market Finance, Real Estate,
                    ARIA, MMO, RL Lab, Signals, Agents, and Viz Lab.
                  </p>
                </section>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
