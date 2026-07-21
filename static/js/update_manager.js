/**
 * Salomón AI — Update Manager (Hot-Loader PWA sin frenos)
 * Poll /api/version + /version.json → badge en tuerquita → hot-patch si build cambia.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const POLL_MS = 4000;
  const STORAGE_KEY = "salomon_build_id";
  var applying = false;

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
          } else if (local !== remote && !this._isLocalDevBuild(remote)) {
            // Toast + apply (build real cambió)
            this.applyUpdateNow(remote);
            return;
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
      window.addEventListener("online", () => this.checkForUpdate());
      window.addEventListener("focus", () => this.checkForUpdate());

      const toastBtn = document.getElementById("update-toast-btn");
      if (toastBtn) {
        toastBtn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.hotPatch();
        });
      }

      window.SalomonUpdate = this;
      window.SalomonPWAHotLoader = this;
    },

    _isLocalDevBuild(build) {
      return /^local-/i.test(String(build || ""));
    },

    _wireSwMessages() {
      if (!("serviceWorker" in navigator)) return;
      navigator.serviceWorker.addEventListener("message", (event) => {
        const data = event.data || {};
        if (data.type === "UPDATE_AVAILABLE" && data.forceUpdate !== false) {
          // Solo aplicar si el build remoto realmente cambió
          this.checkForUpdate();
          return;
        }
        if (data.type === "SW_ACTIVATED") {
          // Informativo — no recargar en bucle
          this.checkForUpdate();
          return;
        }
        if (data.type === "CACHES_CLEARED" || data.type === "SW_READY") {
          // Recarga solo si este manager inició el hotPatch
          if (applying || window.__salomon_awaiting_sw_claim) {
            this._hardReload();
          }
        }
      });
    },

    async fetchBuild() {
      var build = null;
      try {
        const res = await fetch("/api/version?t=" + Date.now(), {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (res.ok) {
          const data = await res.json();
          build = data.build_full || data.build || data.version || null;
        }
      } catch (_) {}
      if (build) return build;
      try {
        const res2 = await fetch("/version.json?t=" + Date.now(), {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (res2.ok) {
          const pack = await res2.json();
          build = pack.build || pack.version || pack.label || null;
        }
      } catch (_) {}
      return build;
    },

    async checkForUpdate() {
      try {
        const remote = await this.fetchBuild();
        if (!remote) return;
        window.dispatchEvent(
          new CustomEvent("salomon:build-meta", { detail: { build: remote } })
        );
        const local = localStorage.getItem(STORAGE_KEY) || this.currentBuild;
        if (
          local &&
          remote &&
          local !== remote &&
          !this._isLocalDevBuild(remote)
        ) {
          this.currentBuild = remote;
          this.applyUpdateNow(remote);
        } else if (remote) {
          this.currentBuild = remote;
        }
        if (navigator.serviceWorker) {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg && reg.update) reg.update().catch(function () {});
        }
      } catch (_) {}
    },

    /** Badge inmediato en tuerquita + toast + hot-patch */
    applyUpdateNow(build) {
      if (applying) return;
      if (this._isLocalDevBuild(build)) return;
      window.dispatchEvent(
        new CustomEvent("salomon:deploy-notify", {
          detail: {
            build: build || "",
            source: "pwa_hot_loader",
            instant: true,
          },
        })
      );
      if (window.SalomonDeployBadge && window.SalomonDeployBadge.show) {
        window.SalomonDeployBadge.show(build || "Nueva");
      }
      this.showUpdateToast(build || "nueva");
      setTimeout(() => this.hotPatch(), 220);
    },

    showUpdateToast(build) {
      if (!this.toast) return;
      const text = this.toast.querySelector(".update-toast__text");
      if (text) {
        text.textContent =
          "Actualizando Salomón (" + String(build).slice(0, 10) + ")…";
      }
      this.toast.classList.add("is-visible");
    },

    hideToast() {
      if (this.toast) this.toast.classList.remove("is-visible");
    },

    forceUpdate() {
      return this.hotPatch();
    },

    async hotPatch() {
      if (applying) return;
      applying = true;
      window.__salomon_awaiting_sw_claim = true;
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
          "/version.json",
          "/api/version",
          "/static/css/styles.css",
          "/static/css/global.css",
          "/static/css/boton.css",
          "/static/css/settings_layer.css",
          "/static/css/update_styles.css",
          "/static/js/main.js",
          "/static/js/ai_state_lock.js",
          "/static/js/components/SmartButton.js",
          "/static/js/settings_manager.js",
          "/static/js/update_manager.js",
          "/static/js/realtime_notification_badge.js",
          "/static/js/pwa-register.js",
          "/static/js/script.js",
          "/static/js/input_engine.js",
          "/static/js/ui_controller.js",
          "/static/js/camera_logic.js",
          "/static/js/vision_engine.js",
          "/static/js/vision_mode_trigger.js",
          "/static/manifest.json",
          "/manifest.json",
          "/service-worker.js?v=" + Date.now(),
        ];
        await Promise.all(
          assets.map((u) =>
            fetch(u, { cache: "reload", credentials: "same-origin" }).catch(
              function () {}
            )
          )
        );
      } catch (_) {}

      // Una sola recarga (CACHES_CLEARED / controllerchange pueden llegar después)
      if (!window.__salomon_sw_refreshing) {
        this._hardReload();
      }
    },

    _hardReload() {
      if (window.__salomon_sw_refreshing) return;
      window.__salomon_sw_refreshing = true;
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
