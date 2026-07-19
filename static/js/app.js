/**
 * Salomón AI — Capa de lógica de cliente (chat Premium).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const chat = document.getElementById("chat");
  const form = document.getElementById("form-chat");
  const input = document.getElementById("input-msg");
  if (!chat || !form || !input) return;

  let sessionId = localStorage.getItem("salomon_session_id") || null;
  let busy = false;

  function addBubble(text, role) {
    const el = document.createElement("div");
    el.className = "bubble " + (role === "user" ? "user" : "bot");
    el.textContent = text;
    chat.appendChild(el);
    chat.scrollTop = chat.scrollHeight;
    return el;
  }

  async function sendMessage(mensaje) {
    const msg = (mensaje || "").trim();
    if (!msg || busy) return;
    busy = true;
    addBubble(msg, "user");
    input.value = "";
    const typing = addBubble("Pensando…", "bot");
    typing.classList.add("typing");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensaje: msg, session_id: sessionId }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      typing.remove();
      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem("salomon_session_id", sessionId);
      }
      if (res.ok && data.texto) {
        addBubble(data.texto, "bot");
      } else {
        addBubble(
          data.detail
            ? String(data.detail)
            : "No pude completar la respuesta. ¿Lo intentamos de nuevo?",
          "bot"
        );
      }
    } catch (err) {
      typing.remove();
      addBubble("Hubo un problema de conexión. ¿Reintentamos?", "bot");
    } finally {
      busy = false;
      input.focus();
    }
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    sendMessage(input.value);
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then(function (regs) {
      regs.forEach(function (r) {
        r.unregister();
      });
    });
  }
})();
