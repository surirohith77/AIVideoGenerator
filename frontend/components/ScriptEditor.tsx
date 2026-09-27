import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { scriptApi, Script, Scene } from "../lib/api";
import { FileText, Clock, Sparkles, Wand2, Layers } from "lucide-react";

interface ScriptEditorProps {
  projectId: string;
  activeScript?: Script;
  onScenesGenerated?: (scenes: Scene[]) => void;
}

export const ScriptEditor: React.FC<ScriptEditorProps> = ({ projectId, activeScript, onScenesGenerated }) => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(activeScript?.title || "India Russia China: Changing Relationship");
  const [content, setContent] = useState(
    activeScript?.content ||
      `India's relationship with Russia has evolved across decades into a deep economic and strategic partnership.\n` +
      `Trade between the nations has expanded rapidly in recent years, particularly in energy, defense, and infrastructure.\n` +
      `Meanwhile, China's economic footprint continues to reshape global supply chains across Asia and Eurasia.`
  );

  const words = content.trim().split(/\s+/).filter(Boolean).length;
  // Speech duration estimate (~140 wpm = ~2.3 words/sec)
  const estSeconds = Math.ceil(words / 2.3);
  const minutes = Math.floor(estSeconds / 60);
  const seconds = estSeconds % 60;
  const estTimeFormatted = `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;

  const createScriptMutation = useMutation({
    mutationFn: async () => {
      const script = await scriptApi.create(projectId, title, content);
      return script;
    },
    onSuccess: (newScript) => {
      queryClient.invalidateQueries({ queryKey: ["scripts", projectId] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      let currentScriptId = activeScript?.id;
      if (!currentScriptId) {
        const created = await createScriptMutation.mutateAsync();
        currentScriptId = created.id;
      }
      const scenes = await scriptApi.analyze(currentScriptId);
      return scenes;
    },
    onSuccess: (scenes) => {
      queryClient.invalidateQueries({ queryKey: ["scripts", projectId] });
      if (onScenesGenerated) {
        onScenesGenerated(scenes);
      }
    },
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex-1">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter Script Title..."
            className="w-full bg-transparent text-xl font-bold text-white focus:outline-none placeholder-slate-600"
          />
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-400 font-mono bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
          <span>{words} Words</span>
          <span className="h-3 w-px bg-slate-800" />
          <span className="flex items-center gap-1 text-indigo-400">
            <Clock className="w-3.5 h-3.5" />
            Est. Duration: {estTimeFormatted}
          </span>
        </div>
      </div>

      {/* Main Script Textarea */}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={8}
        placeholder="Type or paste your video script here..."
        className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono leading-relaxed"
      />

      <div className="flex items-center justify-between pt-2">
        <p className="text-xs text-slate-500 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Script is processed offline via Local LLM / Rule Analyzer
        </p>

        <button
          onClick={() => analyzeMutation.mutate()}
          disabled={analyzeMutation.isPending || !content.trim()}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-sm shadow-lg shadow-indigo-600/25 transition-all disabled:opacity-50"
        >
          {analyzeMutation.isPending ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Wand2 className="w-4 h-4" />
          )}
          {analyzeMutation.isPending ? "Analyzing & Planning Scenes..." : "Generate Scene Breakdown"}
        </button>
      </div>
    </div>
  );
};
