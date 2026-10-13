import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { presenterApi, scriptApi, projectApi, Presenter, Scene, VideoJob } from "../lib/api";
import { Mic, Film, Wand2, Monitor, Smartphone, Square, Sliders, Sparkles, Layers, Video, ArrowRight } from "lucide-react";

interface CreateVideoWizardProps {
  projectId: string;
  onVideoJobCreated: (job: VideoJob) => void;
  onScenesPlanGenerated: (scenes: Scene[]) => void;
}

export const CreateVideoWizard: React.FC<CreateVideoWizardProps> = ({
  projectId,
  onVideoJobCreated,
  onScenesPlanGenerated,
}) => {
  const queryClient = useQueryClient();

  const [experienceMode, setExperienceMode] = useState<"PRESENTER" | "CONTENT">("CONTENT");
  const [title, setTitle] = useState("India Russia China: Changing Relationship");
  const [content, setContent] = useState(
    `India's relationship with Russia has evolved across decades into a deep economic and strategic partnership.\n` +
      `Trade between the nations has expanded rapidly in recent years, particularly in energy, defense, and infrastructure.\n` +
      `Meanwhile, China's economic footprint continues to reshape global supply chains across Asia and Eurasia.`
  );
  const [selectedPresenterId, setSelectedPresenterId] = useState<string>("");
  const [visualMode, setVisualMode] = useState<"AUTOMATIC" | "MY_MEDIA" | "HYBRID">("HYBRID");
  const [aspectRatio, setAspectRatio] = useState<"16:9" | "9:16" | "1:1">("16:9");
  const [presenterFrequency, setPresenterFrequency] = useState<string>("automatic");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: presenters = [] } = useQuery({
    queryKey: ["presenters"],
    queryFn: presenterApi.list,
  });
  const selectedPresenter = presenters.find((presenter) => presenter.id === selectedPresenterId);
  const presenterModeMissingVoice = experienceMode === "PRESENTER" && (
    !selectedPresenter || !selectedPresenter.voice_reference_asset_id
  );

  const analyzeAndGenerateMutation = useMutation({
    mutationFn: async () => {
      // 1. Create script
      const script = await scriptApi.create(projectId, title, content);
      
      // 2. Update project style profile aspect ratio if changed
      await projectApi.updateStyle(projectId, { aspect_ratio: aspectRatio });

      // 3. Analyze script with mode & presenter parameters
      const scenes = await scriptApi.analyze(script.id, {
        mode: experienceMode,
        presenterId: selectedPresenterId || undefined,
        frequency: presenterFrequency,
      });

      onScenesPlanGenerated(scenes);

      // 4. Trigger Video Generation Job
      const job = await scriptApi.generateVideo(script.id, {
        generationMode: experienceMode,
        presenterId: selectedPresenterId || undefined,
      });

      return job;
    },
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["scripts", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      onVideoJobCreated(job);
    },
  });

  // Presets handlers
  const applyEnterprisePreset = () => {
    setExperienceMode("PRESENTER");
    setVisualMode("AUTOMATIC");
    setAspectRatio("16:9");
    setPresenterFrequency("frequent");
  };

  const applyYouTubeContentPreset = () => {
    setExperienceMode("CONTENT");
    setVisualMode("HYBRID");
    setAspectRatio("16:9");
    setPresenterFrequency("automatic");
  };

  const applyYouTubeShortsPreset = () => {
    setExperienceMode("CONTENT");
    setVisualMode("HYBRID");
    setAspectRatio("9:16");
    setPresenterFrequency("automatic");
  };

  return (
    <div className="glass-card rounded-3xl p-6 sm:p-8 space-y-8 border border-slate-800/80 shadow-2xl">
      {/* Step 1: Experience Choice */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
              <Sparkles className="w-5 h-5 text-indigo-400" /> Video Experience & Workflow Presets
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Select a video style or click a quick preset to apply default layout settings</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={applyEnterprisePreset}
              className="text-[11px] font-bold bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 px-3 py-1.5 rounded-xl text-indigo-300 transition-all"
            >
              Enterprise Presenter
            </button>
            <button
              onClick={applyYouTubeContentPreset}
              className="text-[11px] font-bold bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 px-3 py-1.5 rounded-xl text-purple-300 transition-all"
            >
              YouTube Content
            </button>
            <button
              onClick={applyYouTubeShortsPreset}
              className="text-[11px] font-bold bg-pink-500/10 hover:bg-pink-500/20 border border-pink-500/30 px-3 py-1.5 rounded-xl text-pink-300 transition-all"
            >
              TikTok / Shorts 9:16
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <button
            onClick={() => setExperienceMode("PRESENTER")}
            className={`p-6 rounded-2xl border text-left transition-all relative overflow-hidden ${
              experienceMode === "PRESENTER"
                ? "border-indigo-500/80 bg-indigo-950/40 text-white shadow-xl shadow-indigo-500/15 glow-indigo"
                : "border-slate-800/80 bg-slate-950/40 text-slate-400 hover:border-slate-700/80"
            }`}
          >
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mb-4">
              <Mic className="w-6 h-6" />
            </div>
            <h4 className="text-lg font-bold text-white">🎤 AI Presenter Video</h4>
            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
              Your AI Presenter avatar delivers the entire script on-screen with lip-sync. Perfect for training modules, corporate videos, and sales pitches.
            </p>
          </button>

          <button
            onClick={() => setExperienceMode("CONTENT")}
            className={`p-6 rounded-2xl border text-left transition-all relative overflow-hidden ${
              experienceMode === "CONTENT"
                ? "border-purple-500/80 bg-purple-950/40 text-white shadow-xl shadow-purple-500/15 glow-purple"
                : "border-slate-800/80 bg-slate-950/40 text-slate-400 hover:border-slate-700/80"
            }`}
          >
            <div className="w-12 h-12 rounded-2xl bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center mb-4">
              <Film className="w-6 h-6" />
            </div>
            <h4 className="text-lg font-bold text-white">🎬 Content / Documentary Video</h4>
            <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
              Hybrid YouTube/Documentary style with presenter intro/outro, image motion (Ken Burns pan/zoom), video B-roll, and auto-synced subtitles.
            </p>
          </button>
        </div>
      </div>

      {/* Step 2: Script Input */}
      <div className="space-y-3.5">
        <label className="text-xs font-bold text-slate-200 block uppercase tracking-wider">Video Title & Script</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter video title..."
          className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-bold transition-colors"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={5}
          placeholder="Paste your video script here..."
          className="w-full bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-xs sm:text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono leading-relaxed transition-colors"
        />
      </div>

      {/* Step 3: Presenter, Visuals, Format Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Presenter Selector */}
        <div>
          <label className="text-xs font-bold text-slate-200 block mb-2 uppercase tracking-wider">AI Presenter Avatar</label>
          <select
            value={selectedPresenterId}
            onChange={(e) => setSelectedPresenterId(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="">No Presenter Avatar (Media Only)</option>
            {presenters.map((p) => (
              <option key={p.id} value={p.id}>
                👤 {p.name} ({p.status})
              </option>
            ))}
          </select>
        </div>

        {/* Visuals Source Selector */}
        <div>
          <label className="text-xs font-bold text-slate-200 block mb-2 uppercase tracking-wider">Visual Asset Matching</label>
          <select
            value={visualMode}
            onChange={(e) => setVisualMode(e.target.value as any)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="HYBRID">Auto Ken Burns + Uploaded Media</option>
            <option value="MY_MEDIA">Uploaded Media Assets Only</option>
            <option value="AUTOMATIC">Automatic Visual Motion</option>
          </select>
        </div>

        {/* Format / Aspect Ratio */}
        <div>
          <label className="text-xs font-bold text-slate-200 block mb-2 uppercase tracking-wider">Video Format</label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: "16:9", label: "16:9", icon: Monitor },
              { id: "9:16", label: "9:16", icon: Smartphone },
              { id: "1:1", label: "1:1", icon: Square },
            ].map((f) => {
              const Icon = f.icon;
              return (
                <button
                  key={f.id}
                  onClick={() => setAspectRatio(f.id as any)}
                  className={`py-2.5 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                    aspectRatio === f.id
                      ? "border-indigo-500 bg-indigo-500/20 text-white shadow-md shadow-indigo-500/20"
                      : "border-slate-800 bg-slate-950/80 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <Icon className="w-4 h-4 text-indigo-400" />
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Advanced Settings Toggle */}
      <div className="border-t border-slate-800/80 pt-4">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-bold flex items-center gap-1.5 transition-colors"
        >
          <Sliders className="w-4 h-4" /> {showAdvanced ? "Hide Advanced Settings" : "Configure Presenter Frequency & Controls"}
        </button>

        {showAdvanced && (
          <div className="mt-4 p-5 bg-slate-950/80 border border-slate-800 rounded-2xl grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-2">Presenter Frequency (Content Video Mode)</label>
              <select
                value={presenterFrequency}
                onChange={(e) => setPresenterFrequency(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="automatic">Automatic (Intro, Key Transitions, Outro)</option>
                <option value="frequent">Frequent (Every alternate scene)</option>
                <option value="occasional">Occasional (Intro + Outro + middle)</option>
                <option value="intro_outro">Intro & Outro Only</option>
                <option value="never">Never (Media B-roll Only)</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Generate Video Action Button */}
      {presenterModeMissingVoice && (
        <p role="status" className="text-xs text-amber-300">
          Presenter mode needs a selected presenter with a recorded voice reference. Choose one above or switch to Content mode.
        </p>
      )}
      <button
        onClick={() => analyzeAndGenerateMutation.mutate()}
        disabled={analyzeAndGenerateMutation.isPending || !content.trim() || presenterModeMissingVoice}
        className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 text-white font-extrabold text-base shadow-2xl shadow-indigo-600/30 transition-all disabled:opacity-50 hover:scale-[1.01]"
      >
        {analyzeAndGenerateMutation.isPending ? (
          <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Wand2 className="w-5 h-5" />
        )}
        {analyzeAndGenerateMutation.isPending ? "Analyzing Script & Rendering Video..." : "Generate Video Now"}
      </button>
    </div>
  );
};

