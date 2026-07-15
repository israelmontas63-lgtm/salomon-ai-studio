import { useRef, useState } from "react";
import { editarVideo, generarImagen } from "../api/media";
import "./MediaPanel.css";

/**
 * Panel de subida / generación multimedia (imagen + video).
 * Independiente del estado de audio.
 */
export default function MediaPanel({
  open,
  onClose,
  sessionId,
  onResult,
  onNotify,
}) {
  const [tab, setTab] = useState("imagen");
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [operacion, setOperacion] = useState("cortar");
  const [inicio, setInicio] = useState("0");
  const [fin, setFin] = useState("");
  const [overlay, setOverlay] = useState("Salomón");
  const fileRef = useRef(null);

  if (!open) return null;

  const runImagen = async () => {
    const p = prompt.trim();
    if (!p || busy) return;
    setBusy(true);
    try {
      const data = await generarImagen(p, { sessionId });
      onResult?.(data);
      onNotify?.(data.exito ? "Imagen generada" : "No se pudo generar la imagen");
    } catch {
      onNotify?.("Error al generar imagen");
    } finally {
      setBusy(false);
    }
  };

  const runVideo = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || busy) return;
    setBusy(true);
    try {
      const data = await editarVideo(file, {
        sessionId,
        operacion,
        inicio: Number(inicio) || 0,
        fin: fin === "" ? null : Number(fin),
        textoOverlay: overlay,
      });
      onResult?.(data);
      onNotify?.(data.exito ? "Video procesado" : "No se pudo editar el video");
    } catch {
      onNotify?.("Error al editar video");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="media-panel-overlay" role="dialog" aria-label="Multimedia">
      <div className="media-panel">
        <header className="media-panel__head">
          <h2>Multimedia Salomón</h2>
          <button type="button" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>

        <div className="media-panel__tabs">
          <button
            type="button"
            className={tab === "imagen" ? "is-active" : ""}
            onClick={() => setTab("imagen")}
          >
            Generar imagen
          </button>
          <button
            type="button"
            className={tab === "video" ? "is-active" : ""}
            onClick={() => setTab("video")}
          >
            Editar video
          </button>
        </div>

        {tab === "imagen" ? (
          <div className="media-panel__body">
            <label>
              Prompt
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                placeholder="Describe la imagen (estilo negro y oro)…"
              />
            </label>
            <button type="button" disabled={busy || !prompt.trim()} onClick={runImagen}>
              {busy ? "Generando…" : "Generar"}
            </button>
          </div>
        ) : (
          <div className="media-panel__body">
            <label>
              Archivo de video
              <input ref={fileRef} type="file" accept="video/*" />
            </label>
            <label>
              Operación
              <select value={operacion} onChange={(e) => setOperacion(e.target.value)}>
                <option value="cortar">Cortar</option>
                <option value="overlay_texto">Superponer texto</option>
                <option value="filtro_bn">Filtro B/N</option>
                <option value="filtro_brillo">Filtro brillo</option>
                <option value="info">Info</option>
              </select>
            </label>
            <div className="media-panel__row">
              <label>
                Inicio (s)
                <input value={inicio} onChange={(e) => setInicio(e.target.value)} />
              </label>
              <label>
                Fin (s)
                <input
                  value={fin}
                  onChange={(e) => setFin(e.target.value)}
                  placeholder="fin"
                />
              </label>
            </div>
            <label>
              Texto overlay
              <input value={overlay} onChange={(e) => setOverlay(e.target.value)} />
            </label>
            <button type="button" disabled={busy} onClick={runVideo}>
              {busy ? "Procesando…" : "Subir y editar"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
