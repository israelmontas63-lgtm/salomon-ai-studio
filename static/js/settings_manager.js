/**
 * Salomón AI — Settings Manager (Control Layer)
 * Capas Zero-Conflict: aislado de cámara, micrófono y chat.
 * Herramientas vía array JSON expandable.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  /** Catálogo escalable de herramientas futuras */
  const TOOLS = [
    {
      id: "chat",
      label: "Chat",
      action: "chatDrawer",
      primary: true,
      description: "Carpeta de chats recientes y conversaciones guardadas",
    },
    {
      id: "update",
      label: "Actualización",
      action: "hotPatch",
      primary: false,
      description: "Hot Patching: descarga el paquete nuevo desde Render",
    },
    {
      id: "close",
      label: "Cerrar",
      action: "close",
      primary: false,
    },
  ];

  const SettingsManager = {
    open: false,
    root: null,
    sheet: null,
    metaEl: null,
    tools: TOOLS.slice(),

    init() {
      // Arranque seguro: no tocar DOM si aún no existe el gear
      try {
        const gear = document.getElementById("btn-settings");
        if (!gear) return;

        // Única entrada al Control Layer — captura aislada
        gear.addEventListener(
          "click",
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            this.toggle();
          },
          true
        );

        window.SalomonSettings = this;
        window.addEventListener("salomon:build-meta", (ev) => {
          const build = ev.detail && ev.detail.build;
          if (build && this.metaEl) this.setBuildMeta(build);
        });
      } catch (_) {
        /* sin errores de consola si el nodo no está listo */
      }
    },

    isOpen() {
      return !!this.open;
    },

    toggle() {
      if (this.open) this.close();
      else this.openLayer();
    },

    openLayer() {
      if (this.open) return;
      // ui_layer_manager: menús bloqueados mientras IA activa
      var gateSettings =
        window.request_ui_action ||
        (window.SalomonAILock && window.SalomonAILock.request_ui_action);
      if (gateSettings && !gateSettings("settings")) return;
      this.open = true;
      document.body.classList.add("control-layer-open");
      // Aislamiento neuronal: cerrar input sheet si estuviera abierto (solo UI flag)
      try {
        if (window.SalomonUiManager && window.SalomonUiManager.hide) {
          window.SalomonUiManager.hide();
        }
      } catch (_) {}

      this._inject();
      const gear = document.getElementById("btn-settings");
      if (gear) gear.classList.add("is-open");

      requestAnimationFrame(() => {
        if (this.root) this.root.classList.add("is-open");
      });

      // Pedir meta de build + sello neuronal (tuerquita)
      this._refreshVersionMeta();
      if (window.SalomonUpdate && window.SalomonUpdate.fetchBuild) {
        window.SalomonUpdate.fetchBuild()
          .then((b) => {
            if (b && this.metaEl && !this.metaEl.querySelector(".control-layer__meta-ok")) {
              this.setBuildMeta(b);
            }
          })
          .catch(function () {});
      }

      window.dispatchEvent(new CustomEvent("salomon:control-layer", { detail: { open: true } }));
    },

    close() {
      if (!this.open) return;
      this.open = false;
      document.body.classList.remove("control-layer-open");
      const gear = document.getElementById("btn-settings");
      if (gear) gear.classList.remove("is-open");

      if (this.root) {
        this.root.classList.remove("is-open");
        const node = this.root;
        setTimeout(() => {
          if (node && node.parentNode) node.parentNode.removeChild(node);
          if (this.root === node) this.root = null;
        }, 100);
      }

      window.dispatchEvent(new CustomEvent("salomon:control-layer", { detail: { open: false } }));
    },

    setBuildMeta(build) {
      if (this.metaEl) {
        this.metaEl.textContent = "Build: " + String(build);
      }
    },

    setSystemMeta(pack) {
      if (!this.metaEl || !pack) return;
      var ver = pack.version || "—";
      var build = pack.build || "—";
      var proto = (pack.protocol || pack.label || "").toString();
      var sis = pack.sistema || {};
      var sce = sis.sce || "102";
      var sealed =
        sis.bridges_sealed === true
          ? "sellado"
          : sis.bridges_sealed === false
            ? "pendiente"
            : "activo";
      this.metaEl.innerHTML = "";
      var line1 = document.createElement("div");
      line1.textContent = "v" + ver + " · Build " + String(build);
      var line2 = document.createElement("div");
      line2.className = "control-layer__meta-sub";
      line2.textContent =
        "SCE " +
        sce +
        " · Capas 1–7 " +
        sealed +
        (proto ? " · " + proto : "");
      var line3 = document.createElement("div");
      line3.className = "control-layer__meta-ok";
      line3.textContent =
        pack.actualizacion_activa !== false
          ? "Actualización activa en la tuerquita"
          : "Actualización pendiente";
      this.metaEl.appendChild(line1);
      this.metaEl.appendChild(line2);
      this.metaEl.appendChild(line3);
    },

    async _refreshVersionMeta() {
      try {
        var res = await fetch("/api/version?t=" + Date.now(), {
          cache: "no-store",
          credentials: "same-origin",
        });
        var pack = await res.json().catch(function () {
          return null;
        });
        if (pack) this.setSystemMeta(pack);
      } catch (_) {
        if (window.SalomonUpdate && window.SalomonUpdate.fetchBuild) {
          window.SalomonUpdate.fetchBuild().then((b) => {
            if (b) this.setBuildMeta(b);
          }).catch(function () {});
        }
      }
    },

    _inject() {
      if (this.root && this.root.parentNode) {
        this.root.parentNode.removeChild(this.root);
      }

      const layer = document.createElement("div");
      layer.className = "control-layer";
      layer.id = "control-layer";
      layer.setAttribute("role", "dialog");
      layer.setAttribute("aria-modal", "true");
      layer.setAttribute("aria-label", "Herramientas");

      const sheet = document.createElement("div");
      sheet.className = "control-layer__sheet";

      const title = document.createElement("div");
      title.className = "control-layer__title";
      title.textContent = "Herramientas";

      const meta = document.createElement("div");
      meta.className = "control-layer__meta";
      meta.id = "control-layer-build";
      meta.textContent = "Sincronizando sello neuronal…";
      this.metaEl = meta;

      const list = document.createElement("ul");
      list.className = "control-layer__list";

      this.tools.forEach((tool) => {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "control-tool" + (tool.primary ? " control-tool--primary" : "");
        btn.dataset.toolId = tool.id;
        btn.dataset.action = tool.action;
        btn.textContent = tool.label;
        btn.addEventListener(
          "click",
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            this._runTool(tool, btn);
          },
          true
        );
        li.appendChild(btn);
        list.appendChild(li);
      });

      sheet.appendChild(title);
      sheet.appendChild(meta);
      sheet.appendChild(list);
      layer.appendChild(sheet);

      // Clic en backdrop cierra (sin tocar otras capas)
      layer.addEventListener(
        "click",
        (e) => {
          if (e.target === layer) {
            e.preventDefault();
            e.stopPropagation();
            this.close();
          }
        },
        true
      );

      // Bloquear scroll/propagation hacia capas inferiores
      layer.addEventListener(
        "touchmove",
        (e) => {
          if (e.target === layer) e.preventDefault();
        },
        { passive: false }
      );

      document.body.appendChild(layer);
      this.root = layer;
      this.sheet = sheet;
    },

    _runTool(tool, btn) {
      if (!tool) return;
      if (tool.action === "close") {
        this.close();
        return;
      }
      if (tool.action === "chatDrawer") {
        this.close();
        if (window.SalomonChatDrawer && window.SalomonChatDrawer.openDrawer) {
          window.SalomonChatDrawer.openDrawer();
        }
        return;
      }
      if (tool.action === "hotPatch") {
        // Hot Patching: SOLO ServiceWorker.update + purge — sin cámara/mic/chat
        if (btn) {
          btn.disabled = true;
          btn.textContent = "Actualizando…";
        }
        if (window.SalomonUpdate && typeof window.SalomonUpdate.hotPatch === "function") {
          window.SalomonUpdate.hotPatch();
        } else if (window.SalomonUpdate && typeof window.SalomonUpdate.forceUpdate === "function") {
          window.SalomonUpdate.forceUpdate();
        } else {
          this._fallbackHotPatch();
        }
        return;
      }
      // Extensible: futuras acciones se registran en TOOLS
    },

    async _fallbackHotPatch() {
      try {
        if (window.caches && caches.keys) {
          const keys = await caches.keys();
          await Promise.all(keys.map((k) => caches.delete(k)));
        }
        if (navigator.serviceWorker) {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg) {
            await reg.update();
            if (reg.waiting) reg.waiting.postMessage({ type: "SKIP_WAITING" });
            if (reg.active) reg.active.postMessage({ type: "PURGE_AND_CLAIM" });
          }
        }
      } catch (_) {}
      const url = new URL(window.location.href);
      url.searchParams.set("v", String(Date.now()));
      window.location.replace(url.toString());
    },
  };

  function boot() {
    // Solo tras DOM parseado (defer + readyState)
    if (!document.body || !document.getElementById("btn-settings")) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
      }
      return;
    }
    SettingsManager.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
