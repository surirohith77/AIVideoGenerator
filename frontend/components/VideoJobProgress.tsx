import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { jobApi, VideoJob } from "../lib/api";
import { Cpu, CheckCircle2, AlertCircle, Loader2, Sparkles } from "lucide-react";

interface VideoJobProgressProps {
  jobId: string;
  onCompleted?: () => void;
}

export const VideoJobProgress: React.FC<VideoJobProgressProps> = ({ jobId, onCompleted }) => {
  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => jobApi.get(jobId),
    refetchInterval: (query) => {
      const j = query.state.data;
      if (j && (j.status === "COMPLETED" || j.status === "FAILED" || j.status === "CANCELLED")) {
        return false;
      }
      return 1500; // poll every 1.5s while active
    },
  });

  useEffect(() => {
    if (job?.status === "COMPLETED" && onCompleted) {
      onCompleted();
    }
  }, [job?.status, onCompleted]);

  if (!job) return null;

  const stages = [
    { id: "QUEUED", label: "Queued Job" },
    { id: "ANALYZING_PROJECT", label: "Analyzing Script & Assets" },
    { id: "GENERATING_NARRATION", label: "Generating Audio / TTS" },
    { id: "CREATING_SCENES", label: "Applying Ken Burns & Motion" },
    { id: "RENDERING_FINAL_MP4", label: "Rendering Final FFmpeg MP4" },
    { id: "COMPLETED", label: "Final Video Complete" },
  ];

  const isFailed = job.status === "FAILED";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Cpu className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              Video Rendering Job Engine
              <span className="text-[10px] font-mono bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">
                {job.status}
              </span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5 font-mono">{job.current_stage}</p>
          </div>
        </div>
        <div className="text-right font-mono font-bold text-lg text-indigo-400">{job.progress}%</div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden p-0.5 border border-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isFailed
              ? "bg-red-500"
              : job.status === "COMPLETED"
              ? "bg-emerald-500"
              : "bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 animate-pulse"
          }`}
          style={{ width: `${job.progress}%` }}
        />
      </div>

      {/* Error display if failed */}
      {isFailed && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 flex items-start gap-3 text-red-400 text-xs font-mono">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">Rendering Error</span>
            {job.error_message || "An error occurred during video rendering."}
          </div>
        </div>
      )}

      {/* Stage indicators */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2">
        {stages.map((stg) => {
          const isCurrent = job.current_stage.includes(stg.id);
          const isDone = job.status === "COMPLETED" || job.progress >= 100;
          return (
            <div
              key={stg.id}
              className={`p-2 rounded-xl text-[11px] flex items-center gap-2 border ${
                isDone
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : isCurrent
                  ? "bg-indigo-500/10 border-indigo-500/40 text-indigo-300 font-semibold"
                  : "bg-slate-950/40 border-slate-800/40 text-slate-600"
              }`}
            >
              {isDone ? (
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              ) : isCurrent ? (
                <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" />
              ) : (
                <div className="w-3.5 h-3.5 rounded-full border border-slate-700 shrink-0" />
              )}
              <span className="truncate">{stg.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
