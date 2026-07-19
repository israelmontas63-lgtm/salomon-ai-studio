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
      id: "update",
      label: "Actualización",
      action: "hotPatch",
      primary: true,
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
      const gear = document.getElementById("btn-settings");
      if (!gear) return;

      // Única entrada al Control Layer — captura en fase bubble aislada
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
        if (build) this.setBuildMeta(build);
      });
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

      // Pedir meta de build sin tocar cámara/mic/chat
      if (window.SalomonUpdate && window.SalomonUpdate.fetchBuild) {
        window.SalomonUpdate.fetchBuild().then((b) => {
          if (b) this.setBuildMeta(b);
        });
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
        }, 200);
      }

      window.dispatchEvent(new CustomEvent("salomon:control-layer", { detail: { open: false } }));
    },

    setBuildMeta(build) {
      if (this.metaEl) {
        this.metaEl.textContent = "Build: " + String(build);
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
      meta.textContent = "Build: —";
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
    SettingsManager.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
