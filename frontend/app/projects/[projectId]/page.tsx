"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectApi, assetApi, scriptApi, videoApi, Scene, Video, VideoJob } from "../../../lib/api";
import { AssetManager } from "../../../components/AssetManager";
import { StyleProfileEditor } from "../../../components/StyleProfileEditor";
import { CreateVideoWizard } from "../../../components/CreateVideoWizard";
import { SceneTimelineEditor } from "../../../components/SceneTimelineEditor";
import { VideoJobProgress } from "../../../components/VideoJobProgress";
import { VideoPlayerModal } from "../../../components/VideoPlayerModal";
import { ArrowLeft, Layers, Sliders, Folder, FileText, Film, Play, Sparkles, Wand2 } from "lucide-react";

export default function ProjectPage() {
  const params = useParams();
  const projectId = params?.projectId as string;
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<"create" | "assets" | "style" | "videos">("create");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [plannedScenes, setPlannedScenes] = useState<Scene[]>([]);

  const { data: project, isLoading: isLoadingProject } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectApi.get(projectId),
    enabled: !!projectId,
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["assets", projectId],
    queryFn: () => assetApi.list(projectId),
    enabled: !!projectId,
  });

  const { data: scripts = [] } = useQuery({
    queryKey: ["scripts", projectId],
    queryFn: () => scriptApi.list(projectId),
    enabled: !!projectId,
  });

  const { data: videos = [] } = useQuery({
    queryKey: ["videos", projectId],
    queryFn: () => videoApi.listByProject(projectId),
    enabled: !!projectId,
  });

  const activeScript = scripts[0];
  const displayScenes = plannedScenes.length > 0 ? plannedScenes : (activeScript?.scenes || []);

  const triggerVideoMutation = useMutation({
    mutationFn: (scriptId: string) => scriptApi.generateVideo(scriptId),
    onSuccess: (job: VideoJob) => {
      setActiveJobId(job.id);
    },
  });

  if (isLoadingProject) {
    return <div className="text-center py-20 text-slate-500">Loading project details...</div>;
  }

  if (!project) {
    return <div className="text-center py-20 text-slate-500">Project not found.</div>;
  }

  const tabs = [
    { id: "create", label: "Create Video Studio", icon: Wand2 },
    { id: "assets", label: "Media Assets", icon: Folder, count: assets.length },
    { id: "style", label: "Style Profile", icon: Sliders },
    { id: "videos", label: "Rendered Videos", icon: Film, count: videos.length },
  ];

  return (
    <div className="space-y-8">
      {/* Back Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-white">{project.name}</h1>
              <span className="text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full font-semibold">
                {project.style_profile?.aspect_ratio} • {project.style_profile?.resolution}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">{project.description || "Local-First Video Channel Project"}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-800 pb-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                isActive
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Icon className="w-4 h-4" />
              {t.label}
              {t.count !== undefined && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-slate-950 font-mono">
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Active Rendering Job Banner */}
      {activeJobId && (
        <VideoJobProgress
          jobId={activeJobId}
          onCompleted={() => {
            queryClient.invalidateQueries({ queryKey: ["videos", projectId] });
          }}
        />
      )}

      {/* Tab Contents */}
      {activeTab === "create" && (
        <div className="space-y-8">
          <CreateVideoWizard
            projectId={projectId}
            onVideoJobCreated={(job) => setActiveJobId(job.id)}
            onScenesPlanGenerated={(scenes) => setPlannedScenes(scenes)}
          />

          {displayScenes.length > 0 && activeScript && (
            <SceneTimelineEditor
              scriptId={activeScript.id}
              scenes={displayScenes}
              assets={assets}
              isGeneratingVideo={triggerVideoMutation.isPending}
              onGenerateVideo={() => triggerVideoMutation.mutate(activeScript.id)}
            />
          )}
        </div>
      )}

      {activeTab === "assets" && <AssetManager projectId={projectId} />}

      {activeTab === "style" && (
        <StyleProfileEditor projectId={projectId} style={project.style_profile} assets={assets} />
      )}

      {activeTab === "videos" && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-indigo-400" /> Generated MP4 Videos ({videos.length})
          </h3>

          {videos.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-3xl p-8 text-slate-500 text-sm">
              No videos rendered yet. Use the Create Video Studio tab to generate your first video!
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {videos.map((vid) => (
                <div
                  key={vid.id}
                  onClick={() => setSelectedVideo(vid)}
                  className="group bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden cursor-pointer hover:border-slate-700 transition-all"
                >
                  <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                    <div className="w-12 h-12 rounded-full bg-indigo-600/80 text-white flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg">
                      <Play className="w-5 h-5 ml-0.5" />
                    </div>
                    <span className="absolute bottom-2 right-2 text-[10px] bg-slate-950/80 px-2 py-0.5 rounded text-slate-300 font-mono">
                      {vid.duration.toFixed(1)}s
                    </span>
                  </div>
                  <div className="p-4">
                    <h4 className="text-xs font-bold text-white truncate">{vid.title}</h4>
                    <p className="text-[10px] text-slate-500 font-mono mt-1">
                      {vid.aspect_ratio} • {vid.width}x{vid.height} • {new Date(vid.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Video Player Modal */}
      <VideoPlayerModal video={selectedVideo} onClose={() => setSelectedVideo(null)} />
    </div>
  );
}
