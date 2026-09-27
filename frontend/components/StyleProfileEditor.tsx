import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { projectApi, StyleProfile, Asset } from "../lib/api";
import { Sliders, Monitor, Smartphone, Square, Palette, Music, Check, Sparkles } from "lucide-react";

interface StyleProfileEditorProps {
  projectId: string;
  style?: StyleProfile;
  assets?: Asset[];
}

export const StyleProfileEditor: React.FC<StyleProfileEditorProps> = ({ projectId, style, assets = [] }) => {
  const queryClient = useQueryClient();

  const [form, setForm] = useState<Partial<StyleProfile>>({
    aspect_ratio: style?.aspect_ratio || "16:9",
    resolution: style?.resolution || "1080p",
    visual_style: style?.visual_style || "documentary",
    caption_style: style?.caption_style || "bold",
    caption_position: style?.caption_position || "bottom",
    font_family: style?.font_family || "Inter",
    primary_color: style?.primary_color || "#FFFFFF",
    secondary_color: style?.secondary_color || "#FACC15",
    transition: style?.transition || "fade",
    default_scene_duration: style?.default_scene_duration || 6.0,
    music_volume: style?.music_volume || 0.12,
    use_logo: style?.use_logo ?? true,
    music_asset_id: style?.music_asset_id || "",
    logo_asset_id: style?.logo_asset_id || "",
  });

  const [isSaved, setIsSaved] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<StyleProfile>) => projectApi.updateStyle(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    },
  });

  const handleSave = () => {
    updateMutation.mutate(form);
  };

  const musicAssets = assets.filter((a) => a.type === "MUSIC" || a.type === "AUDIO");
  const logoAssets = assets.filter((a) => a.type === "LOGO" || a.type === "IMAGE");

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-400" /> Reusable Project Style Profile
          </h3>
          <p className="text-xs text-slate-400 mt-1">Configure layout, resolution, caption styling, transition defaults, and branding</p>
        </div>
        <button
          onClick={handleSave}
          disabled={updateMutation.isPending}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50"
        >
          {isSaved ? <Check className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
          {isSaved ? "Saved!" : "Save Style Profile"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Aspect Ratio Selector */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-3">Aspect Ratio</label>
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: "16:9", label: "16:9 Landscape", sub: "YouTube / Widescreen", icon: Monitor },
              { id: "9:16", label: "9:16 Vertical", sub: "TikTok / Shorts / Reels", icon: Smartphone },
              { id: "1:1", label: "1:1 Square", sub: "Instagram / Feeds", icon: Square },
            ].map((ar) => {
              const Icon = ar.icon;
              const isSelected = form.aspect_ratio === ar.id;
              return (
                <button
                  key={ar.id}
                  onClick={() => setForm({ ...form, aspect_ratio: ar.id })}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-500/10 text-white shadow-md shadow-indigo-500/10"
                      : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <Icon className="w-5 h-5 mb-2 text-indigo-400" />
                  <div className="text-xs font-bold">{ar.label}</div>
                  <div className="text-[10px] text-slate-500">{ar.sub}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Resolution */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-3">Target Resolution</label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: "1080p", label: "1080p Full HD", desc: "1920x1080 / 1080x1920" },
              { id: "720p", label: "720p HD", desc: "1280x720 / 720x1280" },
            ].map((res) => (
              <button
                key={res.id}
                onClick={() => setForm({ ...form, resolution: res.id })}
                className={`p-3 rounded-xl border text-left transition-all ${
                  form.resolution === res.id
                    ? "border-indigo-500 bg-indigo-500/10 text-white"
                    : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div className="text-xs font-bold">{res.label}</div>
                <div className="text-[10px] text-slate-500">{res.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Transition & Duration */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">Default Transition</label>
          <select
            value={form.transition}
            onChange={(e) => setForm({ ...form, transition: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="fade">Fade</option>
            <option value="crossfade">Crossfade</option>
            <option value="slide_left">Slide Left</option>
            <option value="slide_right">Slide Right</option>
            <option value="zoom">Zoom</option>
            <option value="dip_to_black">Dip to Black</option>
          </select>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">
            Default Scene Duration: <span className="text-indigo-400">{form.default_scene_duration}s</span>
          </label>
          <input
            type="range"
            min="3"
            max="15"
            step="0.5"
            value={form.default_scene_duration}
            onChange={(e) => setForm({ ...form, default_scene_duration: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 bg-slate-950"
          />
        </div>

        {/* Background Music Volume */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">
            Background Music Volume: <span className="text-indigo-400">{Math.round((form.music_volume || 0.12) * 100)}%</span>
          </label>
          <input
            type="range"
            min="0.0"
            max="0.5"
            step="0.02"
            value={form.music_volume}
            onChange={(e) => setForm({ ...form, music_volume: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 bg-slate-950"
          />
        </div>

        {/* Branding Assets */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">Default Background Music Track</label>
          <select
            value={form.music_asset_id}
            onChange={(e) => setForm({ ...form, music_asset_id: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">No Background Music</option>
            {musicAssets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.filename}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">Watermark Logo Asset</label>
          <select
            value={form.logo_asset_id}
            onChange={(e) => setForm({ ...form, logo_asset_id: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">No Logo Watermark</option>
            {logoAssets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.filename}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};
