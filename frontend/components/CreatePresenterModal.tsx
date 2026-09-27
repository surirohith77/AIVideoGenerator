import React, { useState, useRef } from "react";
import { presenterApi, Presenter } from "../lib/api";
import { X, Camera, Mic, CheckCircle2, Play, RefreshCw, ShieldCheck, ArrowRight, UserCheck } from "lucide-react";

interface CreatePresenterModalProps {
  onClose: () => void;
  onCreated: (presenter: Presenter) => void;
}

export const CreatePresenterModal: React.FC<CreatePresenterModalProps> = ({ onClose, onCreated }) => {
  const [step, setStep] = useState<number>(1);
  const [name, setName] = useState("Rohit");
  const [description, setDescription] = useState("Personal AI Presenter");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Camera recording state
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [isRecordingCamera, setIsRecordingCamera] = useState(false);
  const [cameraRecordedBlob, setCameraRecordedBlob] = useState<Blob | null>(null);
  const videoPreviewRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // Mic recording state
  const [isRecordingMic, setIsRecordingMic] = useState(false);
  const [micRecordedBlob, setMicRecordedBlob] = useState<Blob | null>(null);

  // Step 2: Start Camera
  const startCamera = async () => {
    try {
      setErrorMessage(null);
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      setCameraStream(stream);
      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
      }
    } catch (err) {
      setErrorMessage("Camera permission denied or camera device unavailable.");
    }
  };

  const startCameraRecording = () => {
    if (!cameraStream) return;
    const chunks: BlobPart[] = [];
    const recorder = new MediaRecorder(cameraStream);
    mediaRecorderRef.current = recorder;
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: "video/mp4" });
      setCameraRecordedBlob(blob);
    };
    recorder.start();
    setIsRecordingCamera(true);
  };

  const stopCameraRecording = () => {
    if (mediaRecorderRef.current && isRecordingCamera) {
      mediaRecorderRef.current.stop();
      setIsRecordingCamera(false);
      if (cameraStream) {
        cameraStream.getTracks().forEach((t) => t.stop());
        setCameraStream(null);
      }
    }
  };

  // Step 3: Start Mic Recording
  const startMicRecording = async () => {
    try {
      setErrorMessage(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: "audio/wav" });
        setMicRecordedBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      setIsRecordingMic(true);
    } catch (err) {
      setErrorMessage("Microphone permission denied or audio device unavailable.");
    }
  };

  const stopMicRecording = () => {
    if (mediaRecorderRef.current && isRecordingMic) {
      mediaRecorderRef.current.stop();
      setIsRecordingMic(false);
    }
  };

  const handleFinalSubmit = async () => {
    if (!consentConfirmed) {
      setErrorMessage("You must explicitly confirm consent before creating a presenter.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      // 1. Create Presenter record
      const presenter = await presenterApi.create({
        name,
        description,
        consent_confirmed: consentConfirmed,
      });

      // 2. Upload face video if recorded
      if (cameraRecordedBlob) {
        const file = new File([cameraRecordedBlob], "face_reference.mp4", { type: "video/mp4" });
        await presenterApi.recordReference(presenter.id, "FACE", file);
      }

      // 3. Upload voice audio if recorded
      if (micRecordedBlob) {
        const file = new File([micRecordedBlob], "voice_reference.wav", { type: "audio/wav" });
        await presenterApi.recordReference(presenter.id, "VOICE", file);
      }

      const updated = await presenterApi.get(presenter.id);
      onCreated(updated);
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || "Failed to create presenter.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-lg w-full space-y-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Wizard Step Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-lg font-bold text-white">Create AI Presenter</h3>
            <p className="text-xs text-slate-400 font-mono">Step {step} of 4</p>
          </div>
          <div className="flex gap-1.5">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`w-2.5 h-2.5 rounded-full ${
                  s === step ? "bg-indigo-500 scale-125" : s < step ? "bg-emerald-500" : "bg-slate-800"
                }`}
              />
            ))}
          </div>
        </div>

        {errorMessage && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-xl text-xs font-mono">
            {errorMessage}
          </div>
        )}

        {/* Step 1: Presenter Metadata */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Presenter Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Rohit"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Description / Category</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Executive Corporate Spokesperson"
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <button
              onClick={() => { setStep(2); startCamera(); }}
              disabled={!name.trim()}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50"
            >
              Continue to Face Recording <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 2: Record Face Video */}
        {step === 2 && (
          <div className="space-y-4 text-center">
            <h4 className="text-sm font-semibold text-slate-200">Record 20–30 Seconds of Face Video</h4>
            <p className="text-xs text-slate-400">Look directly at the camera, speak naturally, and keep your face visible.</p>

            <div className="aspect-video bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden relative flex items-center justify-center">
              <video ref={videoPreviewRef} autoPlay muted playsInline className="w-full h-full object-cover" />
              {cameraRecordedBlob && (
                <div className="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center text-emerald-400 space-y-2">
                  <CheckCircle2 className="w-10 h-10" />
                  <span className="text-xs font-bold">Face Video Recorded Successfully!</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-center gap-3">
              {!isRecordingCamera ? (
                <button
                  onClick={startCameraRecording}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-md"
                >
                  <Camera className="w-4 h-4" /> Start Recording
                </button>
              ) : (
                <button
                  onClick={stopCameraRecording}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs animate-pulse"
                >
                  ● Recording... Click to Stop
                </button>
              )}
            </div>

            <button
              onClick={() => setStep(3)}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-all"
            >
              Continue to Voice Recording <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 3: Record Voice Sample */}
        {step === 3 && (
          <div className="space-y-4 text-center">
            <h4 className="text-sm font-semibold text-slate-200">Record Voice Audio Sample</h4>
            <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl text-left text-xs text-slate-300 italic font-mono leading-relaxed">
              "Welcome to our AI Video Studio. I authorize the creation of this digital presenter for automated content generation."
            </div>

            <div className="flex items-center justify-center gap-3 pt-2">
              {!isRecordingMic ? (
                <button
                  onClick={startMicRecording}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-md"
                >
                  <Mic className="w-4 h-4" /> Start Voice Recording
                </button>
              ) : (
                <button
                  onClick={stopMicRecording}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs animate-pulse"
                >
                  ● Listening... Click to Stop
                </button>
              )}
            </div>

            {micRecordedBlob && (
              <p className="text-xs text-emerald-400 font-semibold flex items-center justify-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> Voice Sample Recorded!
              </p>
            )}

            <button
              onClick={() => setStep(4)}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-all"
            >
              Review & Legal Consent <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Step 4: Review & Legal Consent Confirmation */}
        {step === 4 && (
          <div className="space-y-5">
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-2">
              <h4 className="text-xs font-bold text-slate-300">Presenter Summary</h4>
              <p className="text-xs text-slate-400">Name: <span className="text-white font-semibold">{name}</span></p>
              <p className="text-xs text-slate-400">Face Reference: {cameraRecordedBlob ? "✓ Recorded" : "Uploaded / Default"}</p>
              <p className="text-xs text-slate-400">Voice Reference: {micRecordedBlob ? "✓ Recorded" : "Uploaded / Default"}</p>
            </div>

            {/* Mandatory Legal Consent Box */}
            <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-4 space-y-2">
              <div className="flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                <label className="text-xs text-slate-200 cursor-pointer space-y-1">
                  <div className="flex items-center gap-2 font-bold text-white">
                    <input
                      type="checkbox"
                      checked={consentConfirmed}
                      onChange={(e) => setConsentConfirmed(e.target.checked)}
                      className="w-4 h-4 accent-indigo-500 rounded"
                    />
                    Explicit Rights & Consent Confirmation
                  </div>
                  <p className="text-[11px] text-slate-400 leading-normal">
                    I confirm that I own this likeness and voice or have explicit legal permission to create and render videos with this AI Presenter.
                  </p>
                </label>
              </div>
            </div>

            <button
              onClick={handleFinalSubmit}
              disabled={!consentConfirmed || isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm shadow-xl shadow-emerald-500/20 transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <UserCheck className="w-5 h-5" />
              )}
              {isSubmitting ? "Creating Presenter Profile..." : "Create Presenter ✓"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
