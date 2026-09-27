"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectApi, videoApi, Project, Video } from "../lib/api";
import { PresenterManager } from "../components/PresenterManager";
import { SystemCapabilities } from "../components/SystemCapabilities";
import { VideoPlayerModal } from "../components/VideoPlayerModal";
import { Plus, Film, FolderPlus, Layers, Play, Sparkles, ArrowRight, UserCheck, CheckCircle2 } from "lucide-react";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);

  const { data: projects = [], isLoading: isLoadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: projectApi.list,
  });

  const { data: videos = [] } = useQuery({
    queryKey: ["videos"],
    queryFn: videoApi.listAll,
  });

  const createProjectMutation = useMutation({
    mutationFn: () => projectApi.create({ name: newProjectName, description: newProjectDesc }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowCreateModal(false);
      setNewProjectName("");
      setNewProjectDesc("");
    },
  });

  return (
    <div className="space-y-10">
      {/* Dynamic Ambient Background Glows */}
      <div className="relative">
        <div className="absolute -top-10 -left-10 w-72 h-72 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -top-10 -right-10 w-72 h-72 bg-purple-600/15 rounded-full blur-3xl pointer-events-none" />

        {/* Hero Header Banner */}
        <div className="glass-card rounded-3xl p-8 sm:p-10 border border-slate-800/80 relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-8 shadow-2xl">
          <div className="space-y-3 max-w-2xl z-10">
            <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 px-3.5 py-1 rounded-full text-xs font-semibold text-indigo-300 backdrop-blur-md">
              <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" /> Local-First AI Video Platform
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight">
              Create Stunning Videos <br />
              <span className="gradient-accent-text">From Text & Assets</span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">
              Upload custom media, create AI Presenters, and automatically generate presenter or YouTube documentary-style videos with Ken Burns pan/zoom, dynamic audio ducking, and styled subtitles.
            </p>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="z-10 flex items-center gap-2.5 px-6 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 text-white font-bold text-sm shadow-2xl shadow-indigo-600/30 hover:scale-105 transition-all self-start md:self-auto"
          >
            <Plus className="w-5 h-5" />
            Create Video Project
          </button>
        </div>
      </div>

      {/* Hardware & Acceleration Capabilities */}
      <SystemCapabilities />

      {/* AI Presenter Studio Section */}
      <PresenterManager />

      {/* Projects Grid */}
      <div className="space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
              <Layers className="w-5 h-5 text-indigo-400" />
              Your Channel & Video Projects ({projects.length})
            </h2>
            <p className="text-xs text-slate-400 mt-1">Select a project to upload assets, configure style profiles, and generate videos</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-indigo-500/50 text-xs font-semibold text-slate-300 hover:text-white transition-all"
          >
            <Plus className="w-4 h-4 text-indigo-400" /> New Project
          </button>
        </div>

        {isLoadingProjects ? (
          <div className="glass-card rounded-2xl p-12 text-center text-slate-400 text-xs">
            Loading video projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="glass-card rounded-3xl p-12 text-center space-y-4 border border-slate-800/80">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center mx-auto shadow-inner">
              <FolderPlus className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">No Projects Found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Get started by creating a new video channel project. You can define custom aspect ratios, visual themes, and logo watermarks.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-xl shadow-indigo-600/30 transition-all"
            >
              <Plus className="w-4 h-4" /> Create Your First Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="glass-card glass-card-hover rounded-2xl p-6 flex flex-col justify-between group"
              >
                <div className="space-y-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2.5 py-1 rounded-full font-bold">
                      {project.style_profile?.aspect_ratio || "16:9"} • {project.style_profile?.resolution || "1080p"}
                    </span>
                    <div className="w-7 h-7 rounded-full bg-slate-800/80 group-hover:bg-indigo-600 flex items-center justify-center text-slate-400 group-hover:text-white transition-all">
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">
                      {project.name}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                      {project.description || "No description provided."}
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span className="capitalize">Theme: {project.style_profile?.visual_style || "Documentary"}</span>
                  <span>{new Date(project.created_at).toLocaleDateString()}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Rendered Videos Showcase */}
      {videos.length > 0 && (
        <div className="space-y-5 pt-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2.5">
              <Film className="w-5 h-5 text-purple-400" />
              Rendered Videos Gallery ({videos.length})
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {videos.map((vid) => (
              <div
                key={vid.id}
                onClick={() => setSelectedVideo(vid)}
                className="glass-card glass-card-hover rounded-2xl overflow-hidden cursor-pointer group flex flex-col justify-between"
              >
                <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center group-hover:scale-110 transition-transform shadow-xl shadow-indigo-600/40">
                    <Play className="w-5 h-5 ml-0.5 fill-white" />
                  </div>
                  <span className="absolute bottom-2.5 right-2.5 text-[10px] bg-slate-950/90 border border-slate-800 px-2 py-0.5 rounded-lg text-slate-200 font-mono font-semibold backdrop-blur-md">
                    {vid.duration.toFixed(1)}s
                  </span>
                </div>
                <div className="p-4 space-y-1">
                  <h4 className="text-xs font-bold text-white truncate group-hover:text-indigo-400 transition-colors">
                    {vid.title}
                  </h4>
                  <p className="text-[10px] text-slate-400 font-mono">
                    {vid.aspect_ratio} • {vid.width}x{vid.height}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-xl flex items-center justify-center p-4">
          <div className="glass-card rounded-3xl p-6 sm:p-8 max-w-md w-full space-y-5 border border-slate-800/80 shadow-2xl animate-in fade-in zoom-in duration-200">
            <div>
              <h3 className="text-xl font-bold text-white">Create Video Project</h3>
              <p className="text-xs text-slate-400 mt-1">Configure channel or video series details</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">Project Name</label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. World History Documentary Series"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Channel topic or purpose..."
                  rows={3}
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => createProjectMutation.mutate()}
                disabled={!newProjectName.trim() || createProjectMutation.isPending}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
              >
                Create Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Video Player Modal */}
      <VideoPlayerModal video={selectedVideo} onClose={() => setSelectedVideo(null)} />
    </div>
  );
}

