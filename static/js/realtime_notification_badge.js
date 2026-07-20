/**
 * Salomón AI — Badge de notificación en tiempo real (tuerquita)
 * Gatillo: post_deploy_success (SSE /api/deploy/stream + poll /api/version)
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var STORAGE_SEEN = "salomon_deploy_badge_seen";
  var es = null;

  var Badge = {
    init() {
      this.ensureBadgeDom();
      this.bindEvents();
      this.connectStream();
      window.SalomonDeployBadge = this;
    },

    ensureBadgeDom() {
      var gear = document.getElementById("btn-settings");
      if (!gear) return;
      if (!gear.querySelector(".deploy-badge")) {
        var badge = document.createElement("span");
        badge.className = "deploy-badge";
        badge.id = "deploy-badge";
        badge.setAttribute("aria-hidden", "true");
        badge.innerHTML =
          '<span class="deploy-badge__dot"></span>' +
          '<span class="deploy-badge__card">Nueva</span>';
        gear.appendChild(badge);
      }
      if (!gear.classList.contains("profile-btn--badge-host")) {
        gear.classList.add("profile-btn--badge-host");
      }
    },

    bindEvents() {
      window.addEventListener("salomon:deploy-notify", (ev) => {
        var d = (ev && ev.detail) || {};
        this.show(d.build || d.version || "");
      });
      window.addEventListener("salomon:build-meta", (ev) => {
        var build = ev.detail && ev.detail.build;
        if (!build) return;
        var seen = localStorage.getItem(STORAGE_SEEN);
        var current = localStorage.getItem("salomon_build_id");
        if (current && build !== current) {
          this.show(build);
        } else if (!seen && current && build === current) {
          /* primer arranque: no badge */
        }
      });
      var gear = document.getElementById("btn-settings");
      if (gear) {
        gear.addEventListener(
          "click",
          () => {
            this.hide(true);
          },
          true
        );
      }
    },

    connectStream() {
      if (!window.EventSource) return;
      try {
        if (es) {
          try {
            es.close();
          } catch (_) {}
        }
        es = new EventSource("/api/deploy/stream");
        es.onmessage = (evt) => {
          try {
            var data = JSON.parse(evt.data || "{}");
            if (data.event === "post_deploy_success" && data.build) {
              var local = localStorage.getItem("salomon_build_id");
              // Badge + hot-load al instante ante cualquier deploy nuevo
              if (!local || data.build !== local) {
                window.dispatchEvent(
                  new CustomEvent("salomon:deploy-notify", {
                    detail: {
                      build: data.build,
                      source: "sse",
                      instant: true,
                    },
                  })
                );
                if (window.SalomonUpdate && window.SalomonUpdate.applyUpdateNow) {
                  window.SalomonUpdate.applyUpdateNow(data.build);
                }
              }
            }
          } catch (_) {}
        };
        es.onerror = function () {
          /* el poll de update_manager cubre el fallback */
        };
      } catch (_) {}
    },

    show(build) {
      this.ensureBadgeDom();
      var gear = document.getElementById("btn-settings");
      var badge = document.getElementById("deploy-badge");
      if (!gear || !badge) return;
      gear.classList.add("has-deploy-badge");
      badge.classList.add("is-visible");
      badge.setAttribute("aria-hidden", "false");
      var card = badge.querySelector(".deploy-badge__card");
      if (card && build) {
        card.textContent = "v" + String(build).slice(0, 7);
      } else if (card) {
        card.textContent = "Nueva";
      }
    },

    hide(markSeen) {
      var gear = document.getElementById("btn-settings");
      var badge = document.getElementById("deploy-badge");
      if (gear) gear.classList.remove("has-deploy-badge");
      if (badge) {
        badge.classList.remove("is-visible");
        badge.setAttribute("aria-hidden", "true");
      }
      if (markSeen) {
        var build = localStorage.getItem("salomon_build_id");
        if (build) localStorage.setItem(STORAGE_SEEN, build);
      }
    },
  };

  function boot() {
    Badge.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
