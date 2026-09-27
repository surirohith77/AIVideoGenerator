import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { scriptApi, Scene, Asset } from "../lib/api";
import { Film, Image as ImageIcon, Play, Layers, Clock, Sliders, RefreshCw, Video } from "lucide-react";

interface SceneTimelineEditorProps {
  scriptId: string;
  scenes: Scene[];
  assets?: Asset[];
  onGenerateVideo: () => void;
  isGeneratingVideo?: boolean;
}

export const SceneTimelineEditor: React.FC<SceneTimelineEditorProps> = ({
  scriptId,
  scenes,
  assets = [],
  onGenerateVideo,
  isGeneratingVideo = false,
}) => {
  const queryClient = useQueryClient();

  const updateSceneMutation = useMutation({
    mutationFn: ({ sceneId, data }: { sceneId: string; data: Partial<Scene> }) =>
      scriptApi.updateScene(sceneId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scripts"] });
    },
  });

  const totalDuration = scenes.reduce((acc, s) => acc + (s.duration || 6.0), 0);

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card border border-slate-800/80 rounded-3xl p-6 shadow-2xl">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-indigo-400" /> Interactive Scene Timeline ({scenes.length} Scenes)
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Total Timeline Duration: <span className="text-indigo-300 font-mono font-bold text-sm">{totalDuration.toFixed(1)}s</span>
          </p>
        </div>

        <button
          onClick={onGenerateVideo}
          disabled={isGeneratingVideo || scenes.length === 0}
          className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-xl shadow-emerald-600/30 transition-all disabled:opacity-50"
        >
          {isGeneratingVideo ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Video className="w-4 h-4" />
          )}
          {isGeneratingVideo ? "Rendering MP4 Video..." : "Render Final Video"}
        </button>
      </div>

      {/* Scenes List / Cards */}
      <div className="grid grid-cols-1 gap-4">
        {scenes.map((scene) => {
          const matchedAsset = assets.find((a) => a.id === scene.asset_id);
          return (
            <div
              key={scene.id}
              className="glass-card glass-card-hover rounded-2xl p-5 grid grid-cols-1 md:grid-cols-12 gap-6 items-center"
            >
              {/* Scene Number & Badge */}
              <div className="md:col-span-1 flex flex-col items-center justify-center">
                <span className="w-11 h-11 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-extrabold flex items-center justify-center text-sm shadow-inner">
                  #{scene.scene_number}
                </span>
                <span className="text-[10px] text-slate-400 font-mono mt-1.5 font-semibold">{scene.duration}s</span>
              </div>

              {/* Visual Preview / Asset Selector */}
              <div className="md:col-span-3">
                <label className="text-[11px] font-bold text-slate-300 block mb-1 uppercase tracking-wider">Visual Asset</label>
                <div className="aspect-video bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative group flex items-center justify-center">
                  {matchedAsset ? (
                    matchedAsset.type === "IMAGE" ? (
                      <img
                        src={`http://localhost:8000/api/assets/${matchedAsset.id}/file`}
                        alt={matchedAsset.filename}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-indigo-400 p-2">
                        <Film className="w-6 h-6" />
                        <span className="text-[10px] text-slate-300 truncate mt-1">{matchedAsset.filename}</span>
                      </div>
                    )
                  ) : (
                    <div className="text-center p-2 text-slate-500">
                      <ImageIcon className="w-6 h-6 mx-auto mb-1 opacity-60" />
                      <span className="text-[10px]">Auto Ken Burns Motion</span>
                    </div>
                  )}

                  {/* Asset Select dropdown */}
                  <select
                    value={scene.asset_id || ""}
                    onChange={(e) =>
                      updateSceneMutation.mutate({ sceneId: scene.id, data: { asset_id: e.target.value } })
                    }
                    className="absolute inset-x-0 bottom-0 bg-slate-950/95 text-slate-200 text-[11px] p-1.5 focus:outline-none border-t border-slate-800 font-medium"
                  >
                    <option value="">Auto Ken Burns Motion</option>
                    {assets.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.type}: {a.filename}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Narration Text & Caption */}
              <div className="md:col-span-5 space-y-2.5">
                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1 uppercase tracking-wider">Scene Narration Script</label>
                  <textarea
                    value={scene.narration}
                    onChange={(e) =>
                      updateSceneMutation.mutate({ sceneId: scene.id, data: { narration: e.target.value } })
                    }
                    rows={2}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono leading-relaxed"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1 uppercase tracking-wider">Subtitle Caption Overlay</label>
                  <input
                    type="text"
                    value={scene.caption || ""}
                    onChange={(e) =>
                      updateSceneMutation.mutate({ sceneId: scene.id, data: { caption: e.target.value } })
                    }
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Controls (Duration & Transition) */}
              <div className="md:col-span-3 space-y-3 bg-slate-950/80 p-3.5 rounded-2xl border border-slate-800">
                <div>
                  <label className="text-[11px] font-bold text-slate-300 flex justify-between">
                    <span>Scene Duration</span>
                    <span className="text-indigo-400 font-mono">{scene.duration}s</span>
                  </label>
                  <input
                    type="range"
                    min="2"
                    max="15"
                    step="0.5"
                    value={scene.duration}
                    onChange={(e) =>
                      updateSceneMutation.mutate({ sceneId: scene.id, data: { duration: parseFloat(e.target.value) } })
                    }
                    className="w-full accent-indigo-500 bg-slate-900 mt-1"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1">Transition</label>
                  <select
                    value={scene.transition}
                    onChange={(e) =>
                      updateSceneMutation.mutate({ sceneId: scene.id, data: { transition: e.target.value } })
                    }
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
                  >
                    <option value="fade">Fade</option>
                    <option value="crossfade">Crossfade</option>
                    <option value="slide_left">Slide Left</option>
                    <option value="slide_right">Slide Right</option>
                    <option value="zoom">Zoom</option>
                  </select>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

