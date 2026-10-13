import React, { useEffect, useMemo, useRef, useState } from "react";
import { presenterApi, Presenter } from "../lib/api";
import { X, Camera, CheckCircle2, ShieldCheck, ArrowRight, UserCheck, RotateCcw, Mic } from "lucide-react";

interface CreatePresenterModalProps {
  onClose: () => void;
  onCreated: (presenter: Presenter) => void;
}

const MIN_RECORDING_SECONDS = 40;
const MAX_RECORDING_SECONDS = 60;
const REFERENCE_SCRIPT =
  "Hi, thanks for taking a moment to listen. I’m going to talk about a few everyday things in my own words. In the morning, I like to plan what I need to do, but I also leave room for new ideas. Some days are busy; other days move at a slower pace. When I explain something, I try to be clear, pause between thoughts, and speak naturally. It’s useful to share details, ask a question, and then give a simple answer. I might sound a little more energetic when something interests me, but I don’t need to change my voice. This is how I normally speak in a quiet room.";

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
  const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
};

const getVideoMimeType = () => {
  if (typeof MediaRecorder === "undefined") return "";
  return ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]
    .find((type) => MediaRecorder.isTypeSupported(type)) || "";
};

const getFileExtension = (mimeType: string) => mimeType.includes("mp4") ? "mp4" : "webm";

export const CreatePresenterModal: React.FC<CreatePresenterModalProps> = ({ onClose, onCreated }) => {
  const [step, setStep] = useState<number>(1);
  const [name, setName] = useState("Rohit");
  const [description, setDescription] = useState("Personal AI Presenter");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [cameraRecordedBlob, setCameraRecordedBlob] = useState<Blob | null>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedDurationSeconds, setRecordedDurationSeconds] = useState(0);
  const videoPreviewRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recordingStartedAtRef = useRef<number | null>(null);
  const recordedVideoUrl = useMemo(
    () => cameraRecordedBlob ? URL.createObjectURL(cameraRecordedBlob) : "",
    [cameraRecordedBlob],
  );

  useEffect(() => {
    if (step === 2 && cameraStream && videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = cameraStream;
      void videoPreviewRef.current.play().catch(() => undefined);
    }
  }, [cameraStream, step]);

  useEffect(() => () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => () => {
    if (recordedVideoUrl) URL.revokeObjectURL(recordedVideoUrl);
  }, [recordedVideoUrl]);

  const releaseCamera = () => {
    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    setCameraStream(null);
  };

  const startCamera = async () => {
    try {
      setErrorMessage(null);
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        throw new Error("This browser does not support camera and microphone recording.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        // Disable automatic voice processing so the reference keeps the speaker's natural tone.
        audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      });
      cameraStreamRef.current = stream;
      setCameraStream(stream);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Camera or microphone permission was denied, or a device is unavailable.";
      setErrorMessage(message);
    }
  };

  const stopCameraRecording = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === "recording") recorder.stop();
  };

  const startCameraRecording = () => {
    if (!cameraStream) {
      setErrorMessage("Allow camera and microphone access before starting the recording.");
      return;
    }
    if (!cameraStream.getVideoTracks().length || !cameraStream.getAudioTracks().length) {
      setErrorMessage("Both a camera and a microphone are required for this guided recording.");
      return;
    }
    try {
      setErrorMessage(null);
      setCameraRecordedBlob(null);
      setRecordedDurationSeconds(0);
      setRecordingSeconds(0);
      const mimeType = getVideoMimeType();
      const recorder = new MediaRecorder(cameraStream, mimeType ? { mimeType } : undefined);
      const chunks: BlobPart[] = [];
      recordingStartedAtRef.current = Date.now();
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onerror = () => {
        setErrorMessage("The recording stopped unexpectedly. Please try again.");
        setIsRecording(false);
        releaseCamera();
      };
      recorder.onstop = () => {
        const duration = recordingStartedAtRef.current
          ? Math.min(MAX_RECORDING_SECONDS, Math.round((Date.now() - recordingStartedAtRef.current) / 1000))
          : recordingSeconds;
        setRecordedDurationSeconds(duration);
        setRecordingSeconds(duration);
        setCameraRecordedBlob(new Blob(chunks, { type: recorder.mimeType || mimeType || "video/webm" }));
        setIsRecording(false);
        releaseCamera();
      };
      recorder.start(1000);
      setIsRecording(true);
      recordingTimerRef.current = setInterval(() => {
        const startedAt = recordingStartedAtRef.current;
        if (!startedAt) return;
        const elapsed = Math.floor((Date.now() - startedAt) / 1000);
        setRecordingSeconds(elapsed);
        if (elapsed >= MAX_RECORDING_SECONDS) stopCameraRecording();
      }, 250);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not start recording. Please check browser permissions.";
      setErrorMessage(message);
    }
  };

  const handleFinalSubmit = async () => {
    if (!cameraRecordedBlob || recordedDurationSeconds < MIN_RECORDING_SECONDS) {
      setErrorMessage("Record at least 40 seconds of the guided prompt before creating the presenter.");
      return;
    }
    if (!consentConfirmed) {
      setErrorMessage("You must explicitly confirm consent before creating a presenter.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const presenter = await presenterApi.create({
        name,
        description,
        consent_confirmed: consentConfirmed,
      });

      const extension = getFileExtension(cameraRecordedBlob.type);
      const faceFile = new File([cameraRecordedBlob], `face_reference.${extension}`, { type: cameraRecordedBlob.type });
      const voiceFile = new File([cameraRecordedBlob], `voice_reference.${extension}`, { type: cameraRecordedBlob.type });
      await presenterApi.recordReference(presenter.id, "FACE", faceFile);
      // The backend extracts and normalizes the audio track from this exact video take.
      await presenterApi.recordReference(presenter.id, "VOICE", voiceFile);

      const updated = await presenterApi.get(presenter.id);
      onCreated(updated);
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || "Failed to create presenter.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const goToRetake = async () => {
    setCameraRecordedBlob(null);
    setRecordedDurationSeconds(0);
    setRecordingSeconds(0);
    setStep(2);
    await startCamera();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-5xl w-full max-h-[92vh] overflow-y-auto space-y-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
        <button
          onClick={onClose}
          aria-label="Close presenter setup"
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center justify-between border-b border-slate-800 pb-3 pr-12">
          <div>
            <h3 className="text-lg font-bold text-white">Create AI Presenter</h3>
            <p className="text-xs text-slate-400 font-mono">Step {step} of 4</p>
          </div>
          <div className="flex gap-1.5" aria-label={`Step ${step} of 4`}>
            {[1, 2, 3, 4].map((currentStep) => (
              <div
                key={currentStep}
                className={`w-2.5 h-2.5 rounded-full ${
                  currentStep === step ? "bg-indigo-500 scale-125" : currentStep < step ? "bg-emerald-500" : "bg-slate-800"
                }`}
              />
            ))}
          </div>
        </div>

        {errorMessage && (
          <div role="alert" className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-xl text-xs">
            {errorMessage}
          </div>
        )}

        {step === 1 && (
          <div className="max-w-2xl mx-auto space-y-4">
            <div>
              <label htmlFor="presenter-name" className="text-xs font-semibold text-slate-300 block mb-1">Presenter Name</label>
              <input
                id="presenter-name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Rohit"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label htmlFor="presenter-description" className="text-xs font-semibold text-slate-300 block mb-1">Description / Category</label>
              <textarea
                id="presenter-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="e.g. Executive Corporate Spokesperson"
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <button
              onClick={() => { setStep(2); void startCamera(); }}
              disabled={!name.trim()}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50"
            >
              Continue to Guided Recording <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h4 className="text-base font-semibold text-slate-100">Record your face and voice together</h4>
              <p className="text-xs text-slate-400 mt-1">Read at your normal pace for 40–60 seconds. Your voice will be taken from this same video.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_1fr] gap-4 items-start">
              <div className="space-y-3">
                <div className="aspect-video bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden relative flex items-center justify-center">
                  <video ref={videoPreviewRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                  {!cameraStream && !cameraRecordedBlob && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-400 text-sm">
                      <Camera className="w-7 h-7" />
                      <span>Allow camera and microphone access to continue</span>
                    </div>
                  )}
                  {cameraRecordedBlob && !isRecording && (
                    <div className="absolute inset-0 bg-slate-950/75 flex flex-col items-center justify-center text-emerald-400 space-y-2">
                      <CheckCircle2 className="w-10 h-10" />
                      <span className="text-sm font-bold">Recording ready to review</span>
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className={`font-mono text-sm ${isRecording ? "text-red-400" : "text-slate-300"}`} aria-live="polite">
                    {isRecording ? "● Recording" : "Duration"} {formatDuration(recordingSeconds)} / 01:00
                  </p>
                  {!cameraStream && !cameraRecordedBlob && !isRecording ? (
                    <button
                      onClick={() => { void startCamera(); }}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md"
                    >
                      <Camera className="w-4 h-4" /> Enable camera and microphone
                    </button>
                  ) : !isRecording ? (
                    <button
                      onClick={startCameraRecording}
                      disabled={!cameraStream || Boolean(cameraRecordedBlob)}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-md disabled:opacity-50"
                    >
                      <Camera className="w-4 h-4" /> Start recording
                    </button>
                  ) : (
                    <button
                      onClick={stopCameraRecording}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs"
                    >
                      Stop recording
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-slate-500">Use a quiet room, keep your face in frame, and look toward the camera when you can. Recording stops automatically at 60 seconds.</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-3">
                <div className="flex items-center gap-2 text-indigo-300">
                  <Mic className="w-4 h-4" />
                  <h5 className="text-xs font-bold uppercase tracking-wide">Read this naturally</h5>
                </div>
                <p className="text-sm leading-6 text-slate-200">{REFERENCE_SCRIPT}</p>
              </div>
            </div>

            {cameraRecordedBlob && recordedDurationSeconds < MIN_RECORDING_SECONDS && (
              <div className="flex flex-wrap items-center justify-between gap-3" role="status">
                <p className="text-xs text-amber-300">This take is {recordedDurationSeconds} seconds. Please retake and speak for at least 40 seconds.</p>
                <button
                  onClick={() => { void goToRetake(); }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs"
                >
                  <RotateCcw className="w-4 h-4" /> Retake
                </button>
              </div>
            )}
            <button
              onClick={() => { setStep(3); }}
              disabled={!cameraRecordedBlob || recordedDurationSeconds < MIN_RECORDING_SECONDS}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50"
            >
              Review recording <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="max-w-3xl mx-auto space-y-4">
            <div>
              <h4 className="text-base font-semibold text-slate-100">Review your recording</h4>
              <p className="text-xs text-slate-400 mt-1">Check that your face is clear and your voice sounds natural. Both references come from this take ({formatDuration(recordedDurationSeconds)}).</p>
            </div>
            {recordedVideoUrl && (
              <video src={recordedVideoUrl} controls playsInline className="w-full aspect-video bg-slate-950 rounded-2xl border border-slate-800" />
            )}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => { void goToRetake(); }}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm"
              >
                <RotateCcw className="w-4 h-4" /> Retake video and voice
              </button>
              <button
                onClick={() => setStep(4)}
                className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm"
              >
                Use this recording <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="max-w-2xl mx-auto space-y-5">
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-2">
              <h4 className="text-xs font-bold text-slate-300">Presenter Summary</h4>
              <p className="text-xs text-slate-400">Name: <span className="text-white font-semibold">{name}</span></p>
              <p className="text-xs text-slate-400">Face Reference: ✓ Recorded</p>
              <p className="text-xs text-slate-400">Voice Reference: ✓ Extracted from the same recording</p>
              <p className="text-xs text-slate-400">Recording Length: {formatDuration(recordedDurationSeconds)}</p>
            </div>

            <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-4 space-y-2">
              <div className="flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                <label className="text-xs text-slate-200 cursor-pointer space-y-1">
                  <div className="flex items-center gap-2 font-bold text-white">
                    <input
                      type="checkbox"
                      checked={consentConfirmed}
                      onChange={(event) => setConsentConfirmed(event.target.checked)}
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
              onClick={() => { void handleFinalSubmit(); }}
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
