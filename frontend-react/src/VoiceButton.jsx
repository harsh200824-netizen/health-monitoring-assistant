import { useEffect, useRef, useState } from "react";

// Uses the browser's built-in speech recognition (Chrome and Edge).
// Speech is sent to the browser vendor for recognition, so an internet connection is needed.
const SpeechRecognition =
  typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function VoiceButton({ onText, disabled }) {
  const [listening, setListening] = useState(false);
  const [message, setMessage] = useState("");
  const recognitionRef = useRef(null);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  if (!SpeechRecognition) {
    return <span className="muted">Voice input works in Chrome or Edge.</span>;
  }

  const toggle = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      onText(text);
      setMessage("Heard: " + text);
    };
    recognition.onerror = (event) => {
      setMessage(event.error === "not-allowed"
        ? "Microphone permission was denied."
        : "Voice input error: " + event.error);
    };
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    setMessage("");
    setListening(true);
    recognition.start();
  };

  return (
    <div className="voice-input">
      <button type="button" className="button button-secondary" onClick={toggle} disabled={disabled}>
        {listening ? "Stop listening" : "🎤 Speak question"}
      </button>
      {message && <small className="muted">{message}</small>}
    </div>
  );
}