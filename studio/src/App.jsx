import { useCallback, useEffect, useRef, useState } from "react";
import Header from "./components/Header";
import ChatBody from "./components/ChatBody";
import BottomBar from "./components/BottomBar";
import GlassPanel from "./components/GlassPanel";
import CameraView from "./components/CameraView";
import MediaPanel from "./components/MediaPanel";
import { useDayNight } from "./hooks/useTypewriter";
import { useSalomonOrchestrator } from "./hooks/useSalomonOrchestrator";
import { WELCOME_MESSAGES, TOOLS_MENU, ACCOUNT_MENU } from "./data/constants";
import { pickRandom, skeletonAlert, hapticPulse } from "./utils/helpers";
import { playSalomonAudio } from "./utils/audio";
import { getCachedGeo, initGeo } from "./utils/geo";
import { checkSalud, iniciarSesion, obtenerHistorial, sintetizarVoz, herramientaAyuda, herramientaAnaliticas, herramientaPlanes, herramientaSolar, herramientaOptimizar, herramientaSeguridad, herramientaCorregir, herramientaTraducir, herramientaCli, herramientaBackupExport } from "./api/salomon";
import "./App.css";

let msgId = 0;
const nextId = () => {
  msgId += 1;
  return String(msgId);
};

const SESSION_KEY = "salomon_session_id";

export default function App() {
  const isDay = useDayNight();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) || null
  );
  const [appStatus, setAppStatus] = useState("ready");
  const [toolsOpen, setToolsOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  /** Si true: Chat NO se renderiza; solo CameraView en el DOM */
  const [modoCamaraActiva, setModoCamaraActiva] = useState(false);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [keyboardVisible, setKeyboardVisible] = useState(true);
  const [inputValue, setInputValue] = useState("");
  const [showWelcomeFlash, setShowWelcomeFlash] = useState(true);
  const [accessibilityMode, setAccessibilityMode] = useState(false);
  const [lastAiSnapshot, setLastAiSnapshot] = useState(null);
  const [sending, setSending] = useState(false);
  const [voiceHint, setVoiceHint] = useState("");
  const initialized = useRef(false);
  const audioPlayingRef = useRef(false);
  const consoleErrorRef = useRef(null);

  const isListeningOrSpeaking =
    appStatus === "listening" ||
    appStatus === "speaking" ||
    appStatus === "thinking" ||
    voiceMode !== null;

  const playResponseAudio = useCallback((audioBase64, audioMime) => {
    if (!audioBase64) return;

    playSalomonAudio(audioBase64, audioMime, {
      onStart: () => {
        audioPlayingRef.current = true;
        setAppStatus("speaking");
        hapticPulse(10);
      },
      onEnd: () => {
        audioPlayingRef.current = false;
        setAppStatus("ready");
        hapticPulse(8);
      },
      onError: () => {
        // Fallo de audio (ElevenLabs/repro): omitir, UI sigue con el texto
        audioPlayingRef.current = false;
        setAppStatus("ready");
      },
    });
  }, []);

  const resolveResponseAudio = useCallback(async (data) => {
    try {
      if (data?.audio_base64) {
        return {
          audioBase64: data.audio_base64,
          audioMime: data.audio_mime || "audio/wav",
        };
      }
      const asyncTts =
        data?.metadata?.tts_pendiente ||
        import.meta.env.VITE_TTS_ASYNC === "true";
      if (data?.texto && asyncTts) {
        try {
          const tts = await sintetizarVoz(data.texto);
          if (tts?.audio_base64) {
            return {
              audioBase64: tts.audio_base64,
              audioMime: tts.audio_mime || "audio/wav",
            };
          }
        } catch {
          /* ElevenLabs / TTS opcional — no bloquea el chat */
        }
      }
    } catch {
      /* cualquier fallo de audio se omite */
    }
    return { audioBase64: null, audioMime: "audio/wav" };
  }, []);

  /** Adjunta y reproduce audio sin bloquear el texto ya renderizado. */
  const attachAudioInBackground = useCallback(
    (messageId, data) => {
      void (async () => {
        try {
          const audio = await resolveResponseAudio(data);
          if (!audio.audioBase64) {
            if (!audioPlayingRef.current) setAppStatus("ready");
            return;
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? {
                    ...m,
                    audioBase64: audio.audioBase64,
                    audioMime: audio.audioMime,
                  }
                : m
            )
          );
          playResponseAudio(audio.audioBase64, audio.audioMime);
        } catch {
          if (!audioPlayingRef.current) setAppStatus("ready");
        }
      })();
    },
    [resolveResponseAudio, playResponseAudio]
  );

  const pushAiMessage = useCallback(
    (text, audioBase64 = null, audioMime = "audio/wav") => {
      const id = nextId();
      const safeText = text == null ? "" : String(text);
      setMessages((prev) => [
        ...prev,
        {
          id,
          role: "ai",
          text: safeText,
          typing: true,
          saved: false,
          audioBase64,
          audioMime,
        },
      ]);

      if (audioBase64) {
        playResponseAudio(audioBase64, audioMime);
      } else {
        // Texto primero: interfaz activa sin esperar audio
        setAppStatus("speaking");
        window.setTimeout(
          () => {
            if (!audioPlayingRef.current) setAppStatus("ready");
          },
          Math.min(safeText.length * 28 + 300, 5000)
        );
      }
      return id;
    },
    [playResponseAudio]
  );

  const persistSession = useCallback((id) => {
    setSessionId(id);
    localStorage.setItem(SESSION_KEY, id);
  }, []);

  const showVoiceHint = useCallback((msg) => {
    setVoiceHint(typeof msg === "string" ? msg : String(msg || ""));
    window.setTimeout(() => setVoiceHint(""), 3200);
  }, []);

  const pushAiMessageRef = useRef(null);
  const attachAudioRef = useRef(null);

  const orchestrator = useSalomonOrchestrator({
    sessionId,
    onSession: persistSession,
    onUserText: (text, { autoSend } = {}) => {
      if (autoSend === false) {
        setInputValue(text);
        setKeyboardVisible(true);
        return;
      }
      setMessages((prev) => [...prev, { id: nextId(), role: "user", text }]);
    },
    onAiText: (text, data) => {
      const id = pushAiMessageRef.current?.(text);
      if (id && data) attachAudioRef.current?.(id, data);
      if (data?.resultado?.imagen_base64) {
        showVoiceHint("Imagen lista");
      }
    },
    onNotify: showVoiceHint,
  });

  useEffect(() => {
    setAppStatus(orchestrator.appStatus);
  }, [orchestrator.appStatus]);

  useEffect(() => {
    pushAiMessageRef.current = pushAiMessage;
    attachAudioRef.current = attachAudioInBackground;
  }, [pushAiMessage, attachAudioInBackground]);

  const voiceMode = orchestrator.voiceMode;

  const sendMessage = useCallback(
    async (textOverride, extras = {}) => {
      const text = (textOverride ?? inputValue).trim();
      if (!text || sending) return;

      setSending(true);
      if (!textOverride) setInputValue("");

      try {
        await orchestrator.dispatchIntent(text, {
          fromVoice: false,
          autoSend: true,
          meta: extras,
        });
      } finally {
        setSending(false);
      }
    },
    [inputValue, sending, orchestrator]
  );

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    async function boot() {
      try {
        await checkSalud();
        setAppStatus("ready");

        const stored = localStorage.getItem(SESSION_KEY);

        if (stored) {
          try {
            const hist = await obtenerHistorial(stored);
            if (hist.mensajes?.length) {
              persistSession(hist.session_id);
              setMessages(
                hist.mensajes.map((m) => ({
                  id: nextId(),
                  role: m.rol === "usuario" ? "user" : "ai",
                  text: m.contenido,
                  typing: false,
                  saved: false,
                }))
              );
              window.setTimeout(() => setShowWelcomeFlash(false), 1600);
              return;
            }
          } catch {
            /* sesión no encontrada — crear nueva */
          }
        }

        const data = await iniciarSesion(stored);
        persistSession(data.session_id);

        const welcomeId = nextId();
        setMessages([
          {
            id: welcomeId,
            role: "ai",
            text: data.mensaje || "",
            typing: true,
            saved: false,
            audioBase64: null,
            audioMime: "audio/wav",
          },
        ]);
        setAppStatus("speaking");
        attachAudioInBackground(welcomeId, {
          texto: data.mensaje,
          audio_base64: data.audio_base64,
          audio_mime: data.audio_mime,
          metadata: {},
        });
      } catch {
        setAppStatus("offline");
        const fallback = pickRandom(WELCOME_MESSAGES);
        setMessages([
          {
            id: nextId(),
            role: "ai",
            text: `${fallback} (Modo sin conexión — el backend aún no responde. Espera el arranque en Render.)`,
            typing: true,
            saved: false,
          },
        ]);
      }

      window.setTimeout(() => setShowWelcomeFlash(false), 1600);
    }

    boot();
    initGeo();
  }, [persistSession, attachAudioInBackground]);

  useEffect(() => {
    const guardarError = (texto) => {
      if (!texto || texto.length < 8) return;
      consoleErrorRef.current = { text: texto.slice(0, 4000), at: Date.now() };
    };

    const onWindowError = (event) => {
      guardarError(event.message || String(event.error || ""));
    };

    const onRejection = (event) => {
      guardarError(String(event.reason || ""));
    };

    const originalError = console.error;
    console.error = (...args) => {
      guardarError(args.map((a) => String(a)).join(" "));
      originalError.apply(console, args);
    };

    window.addEventListener("error", onWindowError);
    window.addEventListener("unhandledrejection", onRejection);

    return () => {
      console.error = originalError;
      window.removeEventListener("error", onWindowError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  const toggleTools = () => {
    setToolsOpen((v) => !v);
    if (!toolsOpen) setAccountOpen(false);
  };

  const toggleAccount = () => {
    setAccountOpen((v) => !v);
    if (!accountOpen) setToolsOpen(false);
  };

  const handleTypingDone = useCallback((id) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, typing: false } : m))
    );
    if (!audioPlayingRef.current) setAppStatus("ready");
  }, []);

  const handleToggleSaved = (id) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, saved: !m.saved } : m))
    );
  };

  const handleRepeatLast = () => {
    if (!lastAiSnapshot) return;
    setMessages((prev) => {
      const idx = [...prev].reverse().findIndex((m) => m.role === "ai");
      if (idx === -1) return prev;
      const realIdx = prev.length - 1 - idx;
      const copy = [...prev];
      copy[realIdx] = { ...lastAiSnapshot, typing: true };
      return copy;
    });

    if (lastAiSnapshot.audioBase64) {
      playResponseAudio(
        lastAiSnapshot.audioBase64,
        lastAiSnapshot.audioMime || "audio/wav"
      );
    } else {
      setAppStatus("speaking");
    }
  };

  useEffect(() => {
    const lastAi = [...messages]
      .reverse()
      .find((m) => m.role === "ai" && !m.typing);
    if (lastAi) setLastAiSnapshot({ ...lastAi, typing: false });
  }, [messages]);

  const handleCameraComment = (payload) => {
    if (typeof payload === "string") {
      sendMessage(payload);
      return;
    }
    sendMessage(payload.mensaje, {
      imagen_base64: payload.imagen_base64,
      imagen_mime: payload.imagen_mime || "image/png",
    });
  };

  const formatToolData = (data) => {
    if (typeof data === "string") return data;
    if (data?.mensaje) return String(data.mensaje);
    if (data?.titulo && data?.detalle) return `${data.titulo}\n${data.detalle}`;
    return JSON.stringify(data, null, 2);
  };

  const handleToolClick = useCallback(
    async (item) => {
      if (item === "Nuevo Chat") {
        try {
          const data = await iniciarSesion(sessionId);
          persistSession(data.session_id);
          const welcomeId = nextId();
          setMessages([
            {
              id: welcomeId,
              role: "ai",
              text: data.mensaje || "",
              typing: true,
              saved: false,
              audioBase64: null,
              audioMime: "audio/wav",
            },
          ]);
          setToolsOpen(false);
          attachAudioInBackground(welcomeId, {
            texto: data.mensaje,
            audio_base64: data.audio_base64,
            audio_mime: data.audio_mime,
            metadata: {},
          });
        } catch {
          showVoiceHint("No pude iniciar un chat nuevo.");
        }
        return;
      }

      if (item === "Multimedia" || item === "Generar Imagen" || item === "Editar Video") {
        setMediaOpen(true);
        setToolsOpen(false);
        return;
      }

      if (item === "Configuración") {
        setAccessibilityMode((v) => {
          showVoiceHint(v ? "Modo estándar activado" : "Modo accesibilidad activado");
          return !v;
        });
        return;
      }

      if (item === "Cambiar Idioma") {
        showVoiceHint("Idioma activo: Español dominicano");
        setToolsOpen(false);
        return;
      }

      if (item === "Gestor de APIs") {
        pushAiMessage(
          "Gestor de APIs:\n" +
          "• Las claves (Gemini, OpenAI, clima) van solo en .env del backend.\n" +
          "• Nunca las pegues en el chat ni en el frontend.\n" +
          "• Opcional: SALOMON_API_KEY protege /api/* con header X-API-Key.\n" +
          "Reinicia el servidor después de cambiar .env."
        );
        setToolsOpen(false);
        return;
      }

      if (item === "Corrección de Texto") {
        const texto = window.prompt("Texto a corregir:");
        if (!texto?.trim()) return;
        try {
          const data = await herramientaCorregir(texto.trim());
          pushAiMessage(`Corrección:\nOriginal: ${data.original}\nCorregido: ${data.corregido}`);
          setToolsOpen(false);
        } catch {
          showVoiceHint("Error al corregir texto.");
        }
        return;
      }

      if (item === "Traducción Simultánea") {
        const texto = window.prompt("Texto a traducir (ES → EN):");
        if (!texto?.trim()) return;
        try {
          const data = await herramientaTraducir(texto.trim());
          pushAiMessage(`Traducción:\n${data.original}\n→ ${data.traduccion}`);
          setToolsOpen(false);
        } catch {
          showVoiceHint("Error al traducir.");
        }
        return;
      }

      if (item === "Terminal de Comandos") {
        const cmd = window.prompt("Comando (help, status, version, fecha):");
        if (!cmd?.trim()) return;
        try {
          const data = await herramientaCli(cmd.trim());
          pushAiMessage(`Terminal:\n${data.salida || "(sin salida)"}`);
          setToolsOpen(false);
        } catch {
          showVoiceHint("Error en terminal.");
        }
        return;
      }

      if (item === "Copia de Seguridad") {
        try {
          const historial = messages.map((m) => ({
            rol: m.role === "user" ? "usuario" : "asistente",
            contenido: m.text,
          }));
          const data = await herramientaBackupExport(historial, {
            session_id: sessionId,
            accessibility_mode: accessibilityMode,
          });
          pushAiMessage(`Backup exportado (${historial.length} mensajes). Copia el JSON desde la consola del navegador si lo necesitas.`);
          console.info("[Salomón Backup]", data.json);
          setToolsOpen(false);
        } catch {
          showVoiceHint("Error al exportar backup.");
        }
        return;
      }

      const loaders = {
        "Ayuda": herramientaAyuda,
        "Analíticas y Consumo": () => herramientaAnaliticas(sessionId),
        "Suscripción y Planes": herramientaPlanes,
        "Monitor Solar": herramientaSolar,
        "Optimización de Rendimiento": herramientaOptimizar,
        "Seguridad YIIOT": herramientaSeguridad,
      };

      const loader = loaders[item];
      if (!loader) {
        skeletonAlert(`${item} — no disponible`);
        return;
      }

      try {
        const data = await loader();
        pushAiMessage(`${item}:\n${formatToolData(data)}`);
        setToolsOpen(false);
      } catch {
        showVoiceHint(`No pude cargar «${item}». Verifica el servidor.`);
      }
    },
    [
      sessionId,
      messages,
      accessibilityMode,
      persistSession,
      pushAiMessage,
      showVoiceHint,
      attachAudioInBackground,
    ]
  );

  const handleAccountClick = useCallback(
    async (item) => {
      if (item.includes("Planes")) {
        try {
          const data = await herramientaPlanes();
          pushAiMessage(`Planes de Salomón:\n${formatToolData(data)}`);
          setAccountOpen(false);
        } catch {
          showVoiceHint("No pude cargar los planes.");
        }
        return;
      }
      skeletonAlert(item);
    },
    [pushAiMessage, showVoiceHint]
  );

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") {
        if (modoCamaraActiva) {
          setModoCamaraActiva(false);
          return;
        }
        setToolsOpen(false);
        setAccountOpen(false);
        orchestrator.cancelAll("user");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [orchestrator, modoCamaraActiva]);

  // Señal global + cancelación de voz al entrar en cámara (Chat desmontado)
  useEffect(() => {
    window.__SALOMON_MODO_CAMARA__ = modoCamaraActiva;
    document.documentElement.classList.toggle("salomon-modo-camara", modoCamaraActiva);
    if (modoCamaraActiva) {
      try {
        window.SalomonBridge?.cancelAll?.("modo-camara-activa");
      } catch {
        /* noop */
      }
      setKeyboardVisible(false);
      setToolsOpen(false);
      setAccountOpen(false);
      setMediaOpen(false);
    }
    return () => {
      if (modoCamaraActiva) {
        window.__SALOMON_MODO_CAMARA__ = false;
        document.documentElement.classList.remove("salomon-modo-camara");
      }
    };
  }, [modoCamaraActiva]);

  // RENDER CONDICIONAL: con cámara activa el Chat NO existe en el DOM
  if (modoCamaraActiva) {
    return (
      <div
        className={[
          "app-shell",
          "app-shell--camera",
          isDay ? "app-shell--day" : "app-shell--night",
        ].join(" ")}
      >
        <CameraView
          onClose={() => setModoCamaraActiva(false)}
          onCaptured={() => {
            /* visión via salomon:ui-photo; Chat se remonta al cerrar */
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={[
        "app-shell",
        isDay ? "app-shell--day" : "app-shell--night",
        accessibilityMode ? "app-shell--a11y" : "",
      ].join(" ")}
    >
      <Header
        appStatus={appStatus}
        onOpenTools={toggleTools}
        onOpenAccount={toggleAccount}
        showWelcomeFlash={showWelcomeFlash}
        isListeningOrSpeaking={isListeningOrSpeaking}
      />

      <ChatBody
        messages={messages}
        onToggleSaved={handleToggleSaved}
        accessibilityMode={accessibilityMode}
        onRepeatLast={handleRepeatLast}
        canRepeat={Boolean(lastAiSnapshot)}
        onTypingDone={handleTypingDone}
      />

      <BottomBar
        orchestrator={orchestrator}
        keyboardVisible={keyboardVisible}
        inputValue={inputValue}
        sending={sending}
        onInputChange={setInputValue}
        onSend={() => sendMessage()}
        onOpenCamera={() => setModoCamaraActiva(true)}
        onToggleKeyboard={() => setKeyboardVisible((v) => !v)}
        onNotify={showVoiceHint}
        onOpenMedia={() => setMediaOpen(true)}
        onToggleHandsFree={orchestrator.toggleHandsFree}
      />

      {voiceHint && <div className="voice-hint" role="status">{voiceHint}</div>}

      <GlassPanel
        open={accountOpen}
        title="Correo"
        items={ACCOUNT_MENU}
        onClose={() => setAccountOpen(false)}
        side="left"
        onItemClick={handleAccountClick}
      />

      <GlassPanel
        open={toolsOpen}
        title="Herramientas"
        items={TOOLS_MENU}
        onClose={() => setToolsOpen(false)}
        side="right"
        onItemClick={handleToolClick}
      />

      <MediaPanel
        open={mediaOpen}
        onClose={() => setMediaOpen(false)}
        sessionId={sessionId}
        onNotify={showVoiceHint}
        onResult={(data) => {
          const r = data?.resultado || {};
          if (r.imagen_base64) {
            pushAiMessage(
              data.respuesta || "Imagen generada.",
              null
            );
          } else if (r.url_relativa) {
            pushAiMessage(
              `${data.respuesta || "Listo."}\n${r.url_relativa}`
            );
          } else {
            pushAiMessage(data.respuesta || data.error || "Resultado multimedia.");
          }
        }}
      />
    </div>
  );
}
