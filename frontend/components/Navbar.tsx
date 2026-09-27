import React from "react";
import Link from "next/link";
import { Film, Layers, Sparkles, Zap, ShieldCheck } from "lucide-react";

export const Navbar: React.FC = () => {
  return (
    <nav className="sticky top-0 z-50 glass-card border-b border-slate-800/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 group-hover:shadow-indigo-500/40 transition-all duration-300">
              <Film className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-lg text-white tracking-tight block gradient-text">
                AI Video Studio
              </span>
              <span className="text-[11px] text-indigo-400 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-purple-400 animate-pulse" /> 100% Local-First Engine
              </span>
            </div>
          </Link>
        </div>

        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white transition-all px-3.5 py-2 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-800/80"
          >
            <Layers className="w-4 h-4 text-indigo-400" />
            Projects Dashboard
          </Link>

          <div className="h-4 w-px bg-slate-800" />
          
          <div className="flex items-center gap-2 bg-indigo-950/40 border border-indigo-500/20 px-3 py-1.5 rounded-full shadow-inner">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400" />
            <span className="text-[11px] font-mono text-slate-300 font-medium flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-400" /> Offline Capable
            </span>
          </div>
        </div>
      </div>
    </nav>
  );
};

