import React from 'react';
import { motion } from 'framer-motion';

export const Login = ({ onLogin }) => (
  <div className="atlas-bg-gradient flex min-h-screen items-center justify-center px-6">
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      className="atlas-glass w-full max-w-md rounded-2xl p-10 text-center"
    >
      <h1 className="mb-2 text-5xl font-light text-slate-950">ATLAS</h1>
      <p className="mb-10 text-xs uppercase tracking-widest text-slate-500">
        M&C Operating System
      </p>

      <div className="space-y-4">
        <input
          type="text"
          placeholder="Identity"
          className="w-full rounded-xl border border-slate-200 bg-white/70 p-4 outline-none transition focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
        />
        <input
          type="password"
          placeholder="Passkey"
          className="w-full rounded-xl border border-slate-200 bg-white/70 p-4 outline-none transition focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="button"
          onClick={onLogin}
          className="w-full rounded-xl bg-slate-950 p-4 text-sm font-medium uppercase tracking-widest text-white shadow-lg transition hover:bg-black active:scale-[0.99]"
        >
          Start Session
        </button>
      </div>
    </motion.div>
  </div>
);
