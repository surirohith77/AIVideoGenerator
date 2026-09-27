import React from "react";
import { Video } from "../lib/api";
import { X, Download, Play, RefreshCw, Film } from "lucide-react";

interface VideoPlayerModalProps {
  video: Video | null;
  onClose: () => void;
}

export const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({ video, onClose }) => {
  if (!video) return null;

  const videoStreamUrl = `http://localhost:8000/api/videos/${video.id}/stream`;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden max-w-4xl w-full shadow-2xl space-y-4 p-6 relative animate-in fade-in zoom-in duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors z-10"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">{video.title}</h3>
            <p className="text-xs text-slate-400 font-mono">
              Duration: {video.duration.toFixed(1)}s • Aspect Ratio: {video.aspect_ratio} • {video.width}x{video.height}
            </p>
          </div>
        </div>

        {/* Video Player */}
        <div className="aspect-video bg-black rounded-2xl overflow-hidden border border-slate-800 relative shadow-inner">
          <video
            src={videoStreamUrl}
            controls
            autoPlay
            className="w-full h-full object-contain"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800">
          <div className="text-xs text-emerald-400 flex items-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            MP4 Video Ready for Download
          </div>
          <div className="flex items-center gap-3">
            <a
              href={videoStreamUrl}
              download={`${video.title}.mp4`}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-lg shadow-indigo-600/20 transition-all"
            >
              <Download className="w-4 h-4" />
              Download MP4
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
