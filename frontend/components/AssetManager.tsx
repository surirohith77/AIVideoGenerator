import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetApi, Asset } from "../lib/api";
import { Upload, Image as ImageIcon, Film, Music, Mic, Trash2, Tag, FileText, CheckCircle2 } from "lucide-react";

interface AssetManagerProps {
  projectId: string;
}

export const AssetManager: React.FC<AssetManagerProps> = ({ projectId }) => {
  const queryClient = useQueryClient();
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", projectId, selectedType],
    queryFn: () => assetApi.list(projectId, selectedType === "ALL" ? undefined : selectedType),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => assetApi.upload(projectId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", projectId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (assetId: string) => assetApi.delete(assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", projectId] });
    },
  });

  const handleFileUpload = async (files: FileList | null) => {
    if (!files) return;
    setIsUploading(true);
    for (let i = 0; i < files.length; i++) {
      await uploadMutation.mutateAsync(files[i]);
    }
    setIsUploading(false);
  };

  const categories = [
    { id: "ALL", label: "All Assets", icon: FileText },
    { id: "IMAGE", label: "Images", icon: ImageIcon },
    { id: "VIDEO", label: "Videos", icon: Film },
    { id: "MUSIC", label: "Music", icon: Music },
    { id: "VOICE", label: "Voice / Audio", icon: Mic },
    { id: "LOGO", label: "Logo & Branding", icon: Tag },
  ];

  return (
    <div className="space-y-6">
      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2.5 border-b border-slate-800/80 pb-4">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedType === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedType(cat.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                isActive
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                  : "bg-slate-900/80 border border-slate-800/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4 text-indigo-400" />
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Upload Box */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => { e.preventDefault(); setDragActive(false); handleFileUpload(e.dataTransfer.files); }}
        className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all ${
          dragActive ? "border-indigo-500 bg-indigo-500/10 glow-indigo" : "border-slate-800/80 glass-card hover:border-indigo-500/40"
        }`}
      >
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto mb-3 shadow-inner">
          <Upload className="w-6 h-6" />
        </div>
        <h4 className="text-base font-bold text-white">Drag & Drop project media assets here</h4>
        <p className="text-xs text-slate-400 mt-1">Supports PNG, JPG, MP4, MP3, WAV, M4A up to 500MB</p>
        <label className="mt-4 inline-flex items-center px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-500 cursor-pointer shadow-lg shadow-indigo-600/20 transition-all">
          Browse Local Files
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
        </label>
        {isUploading && (
          <div className="mt-4 flex items-center justify-center gap-2 text-indigo-400 text-xs font-semibold">
            <span className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            Uploading & Extracting Metadata via FFprobe...
          </div>
        )}
      </div>

      {/* Asset Grid */}
      {isLoading ? (
        <div className="glass-card rounded-2xl p-12 text-center text-slate-400 text-xs">
          Loading project media assets...
        </div>
      ) : assets.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center text-slate-400 text-xs border border-slate-800/80">
          No assets uploaded yet in this category.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="glass-card glass-card-hover rounded-2xl overflow-hidden group flex flex-col justify-between"
            >
              {/* Media Thumbnail */}
              <div className="aspect-video bg-slate-950 relative overflow-hidden flex items-center justify-center">
                {asset.type === "IMAGE" ? (
                  <img
                    src={`http://localhost:8000/api/assets/${asset.id}/file`}
                    alt={asset.filename}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : asset.type === "VIDEO" ? (
                  <div className="relative w-full h-full bg-slate-950 flex items-center justify-center">
                    <Film className="w-8 h-8 text-indigo-400" />
                    {asset.duration && (
                      <span className="absolute bottom-1.5 right-1.5 text-[10px] bg-slate-950/90 border border-slate-800 px-1.5 py-0.5 rounded text-slate-300 font-mono font-semibold">
                        {asset.duration.toFixed(1)}s
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="w-full h-full bg-slate-950/80 flex items-center justify-center text-purple-400">
                    <Music className="w-8 h-8" />
                  </div>
                )}
                
                {/* Delete overlay */}
                <button
                  onClick={() => deleteMutation.mutate(asset.id)}
                  className="absolute top-2 right-2 p-1.5 rounded-lg bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 shadow-md"
                  title="Delete Asset"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Asset Metadata Footer */}
              <div className="p-3.5 space-y-1">
                <p className="text-xs font-bold text-white truncate">{asset.filename}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                  <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-1.5 py-0.5 rounded font-bold">{asset.type}</span>
                  <span>{(asset.size / (1024 * 1024)).toFixed(1)} MB</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

