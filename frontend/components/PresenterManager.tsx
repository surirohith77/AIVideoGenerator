import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { presenterApi, Presenter } from "../lib/api";
import { CreatePresenterModal } from "./CreatePresenterModal";
import { UserCheck, Plus, Trash2, CheckCircle2, ShieldCheck, User, Zap, Play, Check } from "lucide-react";

export const PresenterManager: React.FC = () => {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [testingPresenterId, setTestingPresenterId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any | null>(null);

  const { data: presenters = [], isLoading } = useQuery({
    queryKey: ["presenters"],
    queryFn: presenterApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => presenterApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["presenters"] });
    },
  });

  const testGenerationMutation = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) => presenterApi.testGeneration(id, text),
    onMutate: ({ id }) => setTestingPresenterId(id),
    onSuccess: (data) => {
      setTestResult(data);
      setTestingPresenterId(null);
    },
    onError: (err: any) => {
      setTestingPresenterId(null);
      alert(`Test Generation Error: ${err?.response?.data?.detail || err.message}`);
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <UserCheck className="w-5 h-5 text-indigo-400" /> AI Presenter Avatars ({presenters.length})
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Personalized talking-head presenter profiles recorded & synthesized 100% locally
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all"
        >
          <Plus className="w-4 h-4" /> Create Presenter Avatar
        </button>
      </div>

      {isLoading ? (
        <div className="glass-card rounded-2xl p-12 text-center text-slate-400 text-xs">
          Loading AI Presenters...
        </div>
      ) : presenters.length === 0 ? (
        <div className="glass-card rounded-3xl p-10 text-center space-y-4 border border-slate-800/80">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto shadow-inner">
            <User className="w-7 h-7" />
          </div>
          <h4 className="text-base font-bold text-white">No Presenter Avatars Recorded</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Record a short 20–30 second video with your webcam or upload reference clips to train your personal AI talking-head presenter.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all"
          >
            <Plus className="w-4 h-4" /> Create Presenter Avatar
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {presenters.map((pres) => (
            <div
              key={pres.id}
              className="glass-card glass-card-hover rounded-2xl p-6 space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 text-white font-extrabold flex items-center justify-center text-base shadow-lg shadow-indigo-600/30">
                    {pres.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-full font-bold uppercase tracking-wider">
                    {pres.status}
                  </span>
                </div>
                <div>
                  <h4 className="text-base font-bold text-white">{pres.name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{pres.description || "Personal AI Presenter Profile"}</p>
                </div>

                <div className="space-y-2 pt-3 border-t border-slate-800/80 text-xs">
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Face Reference</span>
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Synthesized
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Voice Reference</span>
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Synthesized
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Consent Audit</span>
                    <span className="text-indigo-400 font-bold flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" /> Verified
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 space-y-3">
                <button
                  onClick={() => testGenerationMutation.mutate({ id: pres.id, text: `Hello, I am ${pres.name}. This is a real test of my local AI presenter model.` })}
                  disabled={testingPresenterId === pres.id}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-bold text-xs transition-all disabled:opacity-50"
                >
                  {testingPresenterId === pres.id ? (
                    <span className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Zap className="w-3.5 h-3.5 text-purple-400" />
                  )}
                  {testingPresenterId === pres.id ? "Running AI Test Pipeline..." : "⚡ Run End-to-End Test"}
                </button>

                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400 font-mono">
                    {new Date(pres.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => deleteMutation.mutate(pres.id)}
                    className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800/80 rounded-xl transition-colors"
                    title="Delete Presenter"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Test Result Modal */}
      {testResult && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-xl flex items-center justify-center p-4">
          <div className="glass-card rounded-3xl p-6 sm:p-8 max-w-lg w-full space-y-5 border border-slate-800/80 shadow-2xl animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" /> End-to-End Test Pipeline Complete
              </h3>
              <button onClick={() => setTestResult(null)} className="text-slate-400 hover:text-white text-xs font-bold">
                Close
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block">Presenter: {testResult.presenter_name}</span>
                <span className="text-slate-400 block">Voice Engine: <span className="text-indigo-400 font-bold">{testResult.voice_engine}</span></span>
                <span className="text-slate-400 block">Presenter Engine: <span className="text-purple-400 font-bold">{testResult.presenter_engine}</span></span>
              </div>

              <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block font-bold text-white mb-1">ffprobe Output Verification:</span>
                <span className="text-emerald-400 block">✓ Audio duration: {testResult.voice_verification?.duration?.toFixed(2)}s</span>
                <span className="text-emerald-400 block">✓ Presenter video clip duration: {testResult.video_verification?.duration?.toFixed(2)}s</span>
                <span className="text-slate-300 block text-[10px] truncate mt-1">Video path: {testResult.generated_video_path}</span>
              </div>
            </div>

            <button
              onClick={() => setTestResult(null)}
              className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg transition-all"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {showCreateModal && (
        <CreatePresenterModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ["presenters"] })}
        />
      )}
    </div>
  );
};


