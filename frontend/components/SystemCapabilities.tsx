import React from "react";
import { useQuery } from "@tanstack/react-query";
import { systemApi } from "../lib/api";
import { Cpu, Zap, CheckCircle2, Shield, HardDrive, CpuIcon } from "lucide-react";

export const SystemCapabilities: React.FC = () => {
  const { data: caps, isLoading } = useQuery({
    queryKey: ["systemCapabilities"],
    queryFn: systemApi.getCapabilities,
  });

  if (isLoading) {
    return (
      <div className="glass-card rounded-2xl p-6 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
        <span className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
        Detecting local GPU/Accelerator & Hardware capabilities...
      </div>
    );
  }

  if (!caps) return null;

  return (
    <div className="glass-card rounded-3xl p-6 space-y-5 border border-slate-800/80 shadow-2xl relative overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3.5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Zap className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white tracking-wide">
              Local AI Acceleration Engine
            </h4>
            <p className="text-[11px] text-slate-400 font-mono">
              Hardware Profile: <span className="gradient-accent-text font-bold">{caps.estimated_performance}</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-semibold text-emerald-400">
          <CheckCircle2 className="w-3.5 h-3.5" /> 100% Offline Active
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80 space-y-1 hover:border-indigo-500/30 transition-all">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">CPU Workstation</span>
          <span className="text-sm font-bold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" /> {caps.cpu_count} CPU Threads
          </span>
        </div>

        <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80 space-y-1 hover:border-purple-500/30 transition-all">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">GPU / Neural Engine</span>
          <span className="text-sm font-bold text-white flex items-center gap-2 truncate">
            <Zap className="w-4 h-4 text-purple-400" /> {caps.gpu_name || "MPS Acceleration"}
          </span>
        </div>

        <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80 space-y-1 hover:border-emerald-500/30 transition-all">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Local Script Analysis</span>
          <span className="text-sm font-bold text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Ready
          </span>
        </div>

        <div className="bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80 space-y-1 hover:border-pink-500/30 transition-all">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Presenter Synthesizer</span>
          <span className="text-sm font-bold text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Ready
          </span>
        </div>
      </div>
    </div>
  );
};

