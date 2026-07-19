/**
 * Salomón AI — Update Manager (Hot Patching)
 * Monitorea /api/version. Dispara ServiceWorker.registration.update().
 * No controla UI del menú (eso es settings_manager.js).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const POLL_MS = 45000;
  const STORAGE_KEY = "salomon_build_id";

  const UpdateManager = {
    currentBuild: null,
    polling: null,
    toast: null,

    async init() {
      this.toast = document.getElementById("update-toast");
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
          window.dispatchEvent(
            new CustomEvent("salomon:build-meta", { detail: { build: remote } })
          );
        }
      } catch (_) {}

      this.polling = setInterval(() => this.checkForUpdate(), POLL_MS);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") this.checkForUpdate();
      });

      const toastBtn = document.getElementById("update-toast-btn");
      if (toastBtn) {
        toastBtn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.hotPatch();
        });
      }

      window.SalomonUpdate = this;
    },

    _wireSwMessages() {
      if (!("serviceWorker" in navigator)) return;
      navigator.serviceWorker.addEventListener("message", (event) => {
        const data = event.data || {};
        if (data.type === "CACHES_CLEARED" || data.type === "SW_READY") {
          this._hardReload();
        }
      });
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
        window.dispatchEvent(
          new CustomEvent("salomon:build-meta", { detail: { build: remote } })
        );
        const local = localStorage.getItem(STORAGE_KEY) || this.currentBuild;
        if (local && remote && local !== remote) {
          this.currentBuild = remote;
          this.showUpdateToast(remote);
          if (navigator.serviceWorker && navigator.serviceWorker.getRegistration) {
            const reg = await navigator.serviceWorker.getRegistration();
            if (reg) {
              await reg.update();
              if (reg.waiting) reg.waiting.postMessage({ type: "SKIP_WAITING" });
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
          "). Toca Actualizar.";
      }
      this.toast.classList.add("is-visible");
    },

    hideToast() {
      if (this.toast) this.toast.classList.remove("is-visible");
    },

    /** Alias usado por settings_manager */
    forceUpdate() {
      return this.hotPatch();
    },

    /**
     * Hot Patching: registration.update() + purge de caché + reload.
     * Sin tocar cámara, micrófono ni chat.
     */
    async hotPatch() {
      this.hideToast();
      try {
        const remote = await this.fetchBuild();
        if (remote) localStorage.setItem(STORAGE_KEY, remote);

        if (window.caches && caches.keys) {
          const keys = await caches.keys();
          await Promise.all(keys.map((k) => caches.delete(k)));
        }

        if (navigator.serviceWorker) {
          const registration = await navigator.serviceWorker.getRegistration();
          if (registration) {
            // Disparador estricto: forzar chequeo de nuevo SW en Render
            await registration.update();
            if (registration.waiting) {
              registration.waiting.postMessage({ type: "SKIP_WAITING" });
            }
            if (registration.active) {
              registration.active.postMessage({ type: "PURGE_AND_CLAIM" });
            }
            if (registration.installing) {
              registration.installing.postMessage({ type: "SKIP_WAITING" });
            }
          }
        }

        const assets = [
          "/",
          "/static/css/styles.css",
          "/static/css/settings_layer.css",
          "/static/js/settings_manager.js",
          "/static/js/update_manager.js",
          "/static/js/input_engine.js",
          "/static/js/camera_logic.js",
          "/static/manifest.json",
          "/service-worker.js?v=" + Date.now(),
        ];
        await Promise.all(
          assets.map((u) =>
            fetch(u, { cache: "reload", credentials: "same-origin" }).catch(function () {})
          )
        );
      } catch (_) {}

      this._hardReload();
    },

    _hardReload() {
      const url = new URL(window.location.href);
      url.searchParams.set("v", String(Date.now()));
      window.location.replace(url.toString());
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
