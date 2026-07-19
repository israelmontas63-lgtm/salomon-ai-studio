/**
 * Salomón AI — Update Manager
 * Monitorea /api/version (build hash). Notifica o recarga al detectar deploy.
 * Botón Actualizar: limpia cachés SW + fuerza paquete nuevo.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const POLL_MS = 45000;
  const STORAGE_KEY = "salomon_build_id";

  const UpdateManager = {
    currentBuild: null,
    polling: null,
    toast: null,
    panel: null,
    metaEl: null,

    async init() {
      this.toast = document.getElementById("update-toast");
      this.panel = document.getElementById("settings-panel");
      this.metaEl = document.getElementById("settings-build-meta");
      this._wireSettingsUi();
      this._wireSwMessages();

      try {
        const remote = await this.fetchBuild();
        if (remote) {
          const local = localStorage.getItem(STORAGE_KEY);
          this.currentBuild = remote;
          if (!local) {
            localStorage.setItem(STORAGE_KEY, remote);
          } else if (local !== remote) {
            this.showUpdateToast(remote);
          }
          this._renderMeta(remote);
        }
      } catch (_) {}

      this.polling = setInterval(() => this.checkForUpdate(), POLL_MS);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") this.checkForUpdate();
      });

      window.SalomonUpdate = this;
    },

    _wireSettingsUi() {
      const btn = document.getElementById("btn-settings");
      const closeBtn = document.getElementById("settings-close");
      const updateBtn = document.getElementById("btn-force-update");
      if (btn) {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.toggleSettings();
        });
      }
      if (closeBtn) {
        closeBtn.addEventListener("click", (e) => {
          e.preventDefault();
          this.closeSettings();
        });
      }
      if (updateBtn) {
        updateBtn.addEventListener("click", (e) => {
          e.preventDefault();
          this.forceUpdate();
        });
      }
      const toastBtn = document.getElementById("update-toast-btn");
      if (toastBtn) {
        toastBtn.addEventListener("click", (e) => {
          e.preventDefault();
          this.forceUpdate();
        });
      }
    },

    _wireSwMessages() {
      if (!("serviceWorker" in navigator)) return;
      navigator.serviceWorker.addEventListener("message", (event) => {
        const data = event.data || {};
        if (data.type === "CACHES_CLEARED" || data.type === "SW_READY") {
          this._hardReload();
        }
      });
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        /* nueva SW activa */
      });
    },

    toggleSettings() {
      if (!this.panel) return;
      if (this.panel.classList.contains("is-open")) this.closeSettings();
      else this.openSettings();
    },

    openSettings() {
      if (!this.panel) return;
      this.panel.classList.add("is-open");
      const btn = document.getElementById("btn-settings");
      if (btn) btn.classList.add("is-open");
      this.checkForUpdate();
    },

    closeSettings() {
      if (!this.panel) return;
      this.panel.classList.remove("is-open");
      const btn = document.getElementById("btn-settings");
      if (btn) btn.classList.remove("is-open");
    },

    async fetchBuild() {
      const res = await fetch("/api/version?t=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.build_full || data.build || null;
    },

    async checkForUpdate() {
      try {
        const remote = await this.fetchBuild();
        if (!remote) return;
        this._renderMeta(remote);
        const local = localStorage.getItem(STORAGE_KEY) || this.currentBuild;
        if (local && remote && local !== remote) {
          this.currentBuild = remote;
          this.showUpdateToast(remote);
          // Si hay SW waiting, activarla
          if (navigator.serviceWorker && navigator.serviceWorker.getRegistration) {
            const reg = await navigator.serviceWorker.getRegistration();
            if (reg && reg.waiting) {
              reg.waiting.postMessage({ type: "SKIP_WAITING" });
            } else if (reg) {
              reg.update();
            }
          }
        } else if (remote) {
          this.currentBuild = remote;
        }
      } catch (_) {}
    },

    showUpdateToast(build) {
      if (!this.toast) return;
      const text = this.toast.querySelector(".update-toast__text");
      if (text) {
        text.textContent =
          "Nueva versión disponible (" +
          String(build).slice(0, 10) +
          "). Toca Actualizar para aplicar.";
      }
      this.toast.classList.add("is-visible");
    },

    hideToast() {
      if (this.toast) this.toast.classList.remove("is-visible");
    },

    /**
     * Limpia caché, fuerza nuevo paquete desde Render y recarga.
     */
    async forceUpdate() {
      const btn = document.getElementById("btn-force-update");
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Actualizando…";
      }
      this.hideToast();

      try {
        const remote = await this.fetchBuild();
        if (remote) localStorage.setItem(STORAGE_KEY, remote);

        // Borrar Cache Storage
        if (window.caches && caches.keys) {
          const keys = await caches.keys();
          await Promise.all(keys.map((k) => caches.delete(k)));
        }

        // Pedir al SW purga + claim
        if (navigator.serviceWorker) {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg && reg.active) {
            reg.active.postMessage({ type: "PURGE_AND_CLAIM" });
          }
          if (reg && reg.waiting) {
            reg.waiting.postMessage({ type: "SKIP_WAITING" });
          }
          if (reg) await reg.update();
        }

        // Prefetch de capas críticas sin caché
        const assets = [
          "/",
          "/static/css/styles.css",
          "/static/css/boton.css",
          "/static/css/camera_full.css",
          "/static/css/input_styles.css",
          "/static/css/update_styles.css",
          "/static/js/update_manager.js",
          "/static/js/input_engine.js",
          "/static/js/camera_logic.js",
          "/static/js/vision_engine.js",
          "/static/manifest.json",
          "/service-worker.js?v=" + Date.now(),
        ];
        await Promise.all(
          assets.map((u) =>
            fetch(u, { cache: "reload", credentials: "same-origin" }).catch(function () {})
          )
        );
      } catch (_) {
        /* igual recargamos */
      }

      this._hardReload();
    },

    _hardReload() {
      const url = new URL(window.location.href);
      url.searchParams.set("v", String(Date.now()));
      window.location.replace(url.toString());
    },

    _renderMeta(build) {
      if (this.metaEl) {
        this.metaEl.textContent = "Build: " + String(build || "—");
      }
    },
  };

  function boot() {
    UpdateManager.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
