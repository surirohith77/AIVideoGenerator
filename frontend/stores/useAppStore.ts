import { create } from "zustand";
import { Project, VideoJob, Video } from "../lib/api";

interface AppState {
  currentProject: Project | null;
  activeJob: VideoJob | null;
  previewVideo: Video | null;
  setCurrentProject: (project: Project | null) => void;
  setActiveJob: (job: VideoJob | null) => void;
  setPreviewVideo: (video: Video | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentProject: null,
  activeJob: null,
  previewVideo: null,
  setCurrentProject: (project) => set({ currentProject: project }),
  setActiveJob: (job) => set({ activeJob: job }),
  setPreviewVideo: (video) => set({ previewVideo: video }),
}));
