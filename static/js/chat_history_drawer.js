/**
 * Salomón AI — Chat History Drawer (carpeta de chats en Herramientas)
 * Recientes arriba · selector Recientes / Guardados · persistencia local + servidor
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var INDEX_KEY = "salomon_chat_index";
  var SESSION_KEY = "salomon_session_id";

  var Drawer = {
    open: false,
    root: null,
    tab: "recientes", // recientes | guardados
    items: [],

    init() {
      window.SalomonChatDrawer = this;
      // Espejo local al completar turnos
      window.addEventListener("salomon:chat-turn", (ev) => {
        var d = (ev && ev.detail) || {};
        this.mirrorLocal(d.session_id, d.preview || d.mensaje || "");
      });
    },

    currentSessionId() {
      return localStorage.getItem(SESSION_KEY) || null;
    },

    mirrorLocal(sessionId, preview) {
      if (!sessionId) return;
      var list = this._readIndex();
      var now = new Date().toISOString();
      var found = list.find(function (c) {
        return c.session_id === sessionId;
      });
      var titulo = (preview || "").trim().slice(0, 48);
      if (found) {
        found.actualizada_en = now;
        if (titulo) {
          found.preview = titulo;
          if (!found.titulo || found.titulo.indexOf("Chat ") === 0) {
            found.titulo = titulo + (titulo.length >= 48 ? "…" : "");
          }
        }
      } else {
        list.unshift({
          session_id: sessionId,
          titulo: titulo || "Chat " + String(sessionId).slice(0, 8),
          preview: titulo,
          actualizada_en: now,
          guardada: false,
          message_count: 1,
        });
      }
      list.sort(function (a, b) {
        return String(b.actualizada_en).localeCompare(String(a.actualizada_en));
      });
      this._writeIndex(list.slice(0, 60));
    },

    _readIndex() {
      try {
        var raw = localStorage.getItem(INDEX_KEY);
        var arr = raw ? JSON.parse(raw) : [];
        return Array.isArray(arr) ? arr : [];
      } catch (_) {
        return [];
      }
    },

    _writeIndex(list) {
      try {
        localStorage.setItem(INDEX_KEY, JSON.stringify(list || []));
      } catch (_) {}
    },

    async openDrawer() {
      if (this.open) return;
      if (window.SalomonSettings && window.SalomonSettings.close) {
        window.SalomonSettings.close();
      }
      this.open = true;
      document.body.classList.add("chat-drawer-open");
      this._inject();
      await this.loadTab(this.tab);
      requestAnimationFrame(() => {
        if (this.root) this.root.classList.add("is-open");
      });
    },

    close() {
      if (!this.open) return;
      this.open = false;
      document.body.classList.remove("chat-drawer-open");
      if (this.root) {
        this.root.classList.remove("is-open");
        var node = this.root;
        setTimeout(function () {
          if (node && node.parentNode) node.parentNode.removeChild(node);
        }, 120);
      }
      this.root = null;
    },

    _inject() {
      if (this.root && this.root.parentNode) {
        this.root.parentNode.removeChild(this.root);
      }
      var layer = document.createElement("div");
      layer.id = "chat-history-drawer";
      layer.className = "chat-drawer";
      layer.setAttribute("role", "dialog");
      layer.setAttribute("aria-label", "Carpeta de chats");

      layer.innerHTML =
        '<div class="chat-drawer__sheet">' +
        '  <div class="chat-drawer__header">' +
        '    <h2 class="chat-drawer__title">Chat</h2>' +
        '    <button type="button" class="chat-drawer__close" id="chat-drawer-close" aria-label="Cerrar">×</button>' +
        "  </div>" +
        '  <div class="chat-drawer__tabs" role="tablist">' +
        '    <button type="button" class="chat-drawer__tab is-active" data-tab="recientes">Chats recientes</button>' +
        '    <button type="button" class="chat-drawer__tab" data-tab="guardados">Conversaciones guardadas</button>' +
        "  </div>" +
        '  <div class="chat-drawer__actions">' +
        '    <button type="button" class="chat-drawer__btn" id="chat-drawer-new">Nuevo chat</button>' +
        '    <button type="button" class="chat-drawer__btn chat-drawer__btn--gold" id="chat-drawer-save">Guardar actual</button>' +
        "  </div>" +
        '  <ul class="chat-drawer__list" id="chat-drawer-list"></ul>' +
        '  <p class="chat-drawer__hint" id="chat-drawer-hint"></p>' +
        "</div>";

      layer.addEventListener("click", (e) => {
        if (e.target === layer) this.close();
      });

      document.body.appendChild(layer);
      this.root = layer;

      layer.querySelector("#chat-drawer-close").addEventListener("click", (e) => {
        e.preventDefault();
        this.close();
      });
      layer.querySelectorAll(".chat-drawer__tab").forEach((tab) => {
        tab.addEventListener("click", (e) => {
          e.preventDefault();
          var t = tab.getAttribute("data-tab");
          layer.querySelectorAll(".chat-drawer__tab").forEach(function (x) {
            x.classList.toggle("is-active", x === tab);
          });
          this.loadTab(t);
        });
      });
      layer.querySelector("#chat-drawer-new").addEventListener("click", (e) => {
        e.preventDefault();
        this.newChat();
      });
      layer.querySelector("#chat-drawer-save").addEventListener("click", (e) => {
        e.preventDefault();
        this.saveCurrent();
      });
    },

    async loadTab(tab) {
      this.tab = tab || "recientes";
      var listEl = document.getElementById("chat-drawer-list");
      var hint = document.getElementById("chat-drawer-hint");
      if (listEl) listEl.innerHTML = '<li class="chat-drawer__empty">Cargando…</li>';

      var items = [];
      try {
        var q =
          this.tab === "guardados"
            ? "/api/chats?guardadas=true&limite=40"
            : "/api/chats?limite=40";
        var res = await fetch(q + "&t=" + Date.now(), {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (res.ok) {
          var data = await res.json();
          items = data.chats || [];
        }
      } catch (_) {}

      // Merge local index (offline / recién creados)
      var local = this._readIndex();
      if (this.tab === "guardados") {
        local = local.filter(function (c) {
          return c.guardada;
        });
      }
      items = this._mergeLists(items, local);

      // Recientes: no filtrar solo no-guardadas; mostrar todos ordenados
      if (this.tab === "guardados") {
        items = items.filter(function (c) {
          return c.guardada;
        });
      }

      this.items = items;
      this._renderList(items);
      if (hint) {
        hint.textContent = items.length
          ? "Toca un chat para abrirlo. El más reciente está arriba."
          : this.tab === "guardados"
            ? "Aún no hay conversaciones guardadas."
            : "Aún no hay chats recientes.";
      }
    },

    _mergeLists(server, local) {
      var map = {};
      (server || []).forEach(function (c) {
        map[c.session_id] = c;
      });
      (local || []).forEach(function (c) {
        if (!map[c.session_id]) map[c.session_id] = c;
        else {
          var a = map[c.session_id].actualizada_en || "";
          var b = c.actualizada_en || "";
          if (b > a) {
            map[c.session_id] = Object.assign({}, map[c.session_id], c);
          }
        }
      });
      return Object.keys(map)
        .map(function (k) {
          return map[k];
        })
        .sort(function (a, b) {
          return String(b.actualizada_en || "").localeCompare(
            String(a.actualizada_en || "")
          );
        });
    },

    _renderList(items) {
      var listEl = document.getElementById("chat-drawer-list");
      if (!listEl) return;
      listEl.innerHTML = "";
      var current = this.currentSessionId();
      if (!items.length) {
        listEl.innerHTML = '<li class="chat-drawer__empty">Sin conversaciones</li>';
        return;
      }
      items.forEach((item) => {
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className =
          "chat-drawer__item" +
          (item.session_id === current ? " is-current" : "");
        var title = item.titulo || "Chat";
        var preview = item.preview || "";
        var meta =
          (item.guardada ? "Guardado · " : "") +
          (item.message_count ? item.message_count + " msgs · " : "") +
          this._fmtDate(item.actualizada_en);
        btn.innerHTML =
          '<span class="chat-drawer__item-title"></span>' +
          '<span class="chat-drawer__item-preview"></span>' +
          '<span class="chat-drawer__item-meta"></span>';
        btn.querySelector(".chat-drawer__item-title").textContent = title;
        btn.querySelector(".chat-drawer__item-preview").textContent = preview;
        btn.querySelector(".chat-drawer__item-meta").textContent = meta;
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          this.openSession(item.session_id);
        });
        li.appendChild(btn);
        listEl.appendChild(li);
      });
    },

    _fmtDate(iso) {
      if (!iso) return "";
      try {
        var d = new Date(iso);
        if (isNaN(d.getTime())) return String(iso).slice(0, 16);
        return d.toLocaleString("es", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch (_) {
        return String(iso).slice(0, 16);
      }
    },

    async openSession(sessionId) {
      if (!sessionId) return;
      localStorage.setItem(SESSION_KEY, sessionId);
      try {
        var res = await fetch(
          "/api/historial?session_id=" + encodeURIComponent(sessionId) + "&t=" + Date.now(),
          { cache: "no-store", credentials: "same-origin" }
        );
        var data = await res.json().catch(function () {
          return {};
        });
        var msgs = data.mensajes || [];
        if (window.SalomonChat && window.SalomonChat.renderHistory) {
          window.SalomonChat.renderHistory(msgs, sessionId);
        }
      } catch (_) {
        if (window.SalomonChat && window.SalomonChat.setSessionId) {
          window.SalomonChat.setSessionId(sessionId);
        }
      }
      this.close();
    },

    async newChat() {
      try {
        // API usa query params (no body JSON)
        var res = await fetch("/api/chat/nuevo", {
          method: "POST",
          credentials: "same-origin",
        });
        var data = await res.json().catch(function () {
          return {};
        });
        var sid = data.session_id || null;
        if (sid) {
          localStorage.setItem(SESSION_KEY, sid);
          this.mirrorLocal(sid, "Nuevo chat");
        }
        if (window.SalomonChat && window.SalomonChat.startFresh) {
          window.SalomonChat.startFresh(
            sid,
            data.mensaje || data.texto || ""
          );
        } else {
          var chat = document.getElementById("chat");
          if (chat) {
            chat.innerHTML = "";
            if (data.texto) {
              var el = document.createElement("div");
              el.className = "bubble bot";
              el.textContent = data.texto;
              chat.appendChild(el);
            }
          }
        }
      } catch (_) {}
      this.close();
    },

    async saveCurrent() {
      var sid = this.currentSessionId();
      if (!sid) {
        this._toast("No hay chat activo para guardar.");
        return;
      }
      try {
        var res = await fetch(
          "/api/chats/" + encodeURIComponent(sid) + "/guardar",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ guardada: true }),
            credentials: "same-origin",
          }
        );
        var data = await res.json().catch(function () {
          return {};
        });
        var list = this._readIndex();
        var found = list.find(function (c) {
          return c.session_id === sid;
        });
        if (found) {
          found.guardada = true;
          if (data.titulo) found.titulo = data.titulo;
        } else {
          list.unshift({
            session_id: sid,
            titulo: data.titulo || "Chat guardado",
            preview: data.titulo || "",
            actualizada_en: new Date().toISOString(),
            guardada: true,
          });
        }
        this._writeIndex(list);
        this._toast("Conversación guardada.");
        if (this.tab === "guardados") this.loadTab("guardados");
      } catch (_) {
        this._toast("No pude guardar ahora. Intenta de nuevo.");
      }
    },

    _toast(msg) {
      var hint = document.getElementById("chat-drawer-hint");
      if (hint) hint.textContent = msg;
    },
  };

  function boot() {
    Drawer.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
