"use client";

import { useState, useRef } from "react";

export default function VoiceAuth() {
  const [userId, setUserId] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [status, setStatus] = useState("");
  const [score, setScore] = useState<number | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/wav" });
        setAudioBlob(blob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setStatus("Recording...");
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setStatus("Error accessing microphone");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus("Recording stopped. Ready to submit.");
      
      // Stop all tracks to release microphone
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const handleSubmit = async (endpoint: "register" | "verify") => {
    if (!audioBlob || !userId) {
      setStatus("Please provide a User ID and record audio first.");
      return;
    }

    setStatus(`Sending to ${endpoint}...`);
    const formData = new FormData();
    formData.append("user_id", userId);
    // Append file with a filename so backend detects it properly
    formData.append("file", audioBlob, "recording.wav");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/${endpoint}`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setStatus(data.message || "Success!");
        if (data.score !== undefined) {
            setScore(data.score);
        } else {
            setScore(null);
        }
      } else {
        setStatus(`Error: ${data.detail || "Unknown error"}`);
        setScore(null);
      }
    } catch (err) {
      console.error(err);
      setStatus("Network error. Is the backend running?");
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-md space-y-4 text-gray-900">
      <h2 className="text-xl font-bold text-center text-gray-800">Voice Authentication</h2>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">User ID</label>
        <input
          type="text"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Enter unique username"
        />
      </div>

      <div className="flex justify-center space-x-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            className="px-4 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition"
          >
            🎤 Start Recording
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="px-4 py-2 bg-red-600 text-white rounded-full hover:bg-red-700 transition animate-pulse"
          >
            ⏹ Stop Recording
          </button>
        )}
      </div>

      {audioBlob && (
        <div className="text-center text-sm text-green-600">
          Audio captured! Ready to process.
        </div>
      )}

      <div className="flex space-x-2">
        <button
          onClick={() => handleSubmit("register")}
          disabled={!audioBlob || !userId}
          className="flex-1 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          Register Voice
        </button>
        <button
          onClick={() => handleSubmit("verify")}
          disabled={!audioBlob || !userId}
          className="flex-1 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
        >
          Verify Voice
        </button>
      </div>

      {status && (
        <div className={`p-3 rounded-md text-center ${status.includes("Error") || status.includes("Failed") ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-800"}`}>
          {status}
        </div>
      )}
      
      {score !== null && (
        <div className="text-center font-mono text-lg">
            Match Score: <span className={score > 0.75 ? "text-green-600 font-bold" : "text-red-600 font-bold"}>{score.toFixed(4)}</span>
        </div>
      )}
    </div>
  );
}
