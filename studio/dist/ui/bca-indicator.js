/**
 * Indicador UI — Branch de Control Autónomo (BCA)
 * Verde = BCA activo · Ámbar = reiniciando/sin BCA · Rojo = intervención
 */
(function () {
  function ensureBadge() {
    let el = document.getElementById("bca-estado");
    if (el) return el;
    el = document.createElement("div");
    el.id = "bca-estado";
    el.setAttribute("title", "Estado del Sistema (BCA)");
    el.innerHTML =
      '<span class="bca-dot" aria-hidden="true"></span>' +
      '<span class="bca-label">Estado del Sistema</span>';
    const style = document.createElement("style");
    style.textContent = `
#bca-estado{
  position:fixed;top:12px;right:14px;z-index:99999;
  display:flex;align-items:center;gap:8px;
  padding:6px 12px;border-radius:999px;
  font:500 12px/1.2 "Segoe UI",system-ui,sans-serif;
  letter-spacing:.02em;color:#e8e4d9;
  background:rgba(8,8,8,.78);border:1px solid rgba(212,175,55,.35);
  backdrop-filter:blur(8px);cursor:default;user-select:none;
}
#bca-estado .bca-dot{
  width:9px;height:9px;border-radius:50%;
  background:#666;box-shadow:0 0 0 2px rgba(0,0,0,.35);
  transition:background .25s,box-shadow .25s;
}
#bca-estado[data-color="verde"] .bca-dot{
  background:#2ecc71;box-shadow:0 0 10px rgba(46,204,113,.65);
}
#bca-estado[data-color="ambar"] .bca-dot{
  background:#f1c40f;box-shadow:0 0 10px rgba(241,196,15,.55);
}
#bca-estado[data-color="rojo"] .bca-dot{
  background:#e74c3c;box-shadow:0 0 10px rgba(231,76,60,.65);
}
#bca-estado .bca-label{opacity:.92;white-space:nowrap}
@media (max-width:640px){
  #bca-estado{top:8px;right:8px;padding:5px 10px;font-size:11px}
  #bca-estado .bca-label{max-width:110px;overflow:hidden;text-overflow:ellipsis}
}
`;
    document.head.appendChild(style);
    document.body.appendChild(el);
    return el;
  }

  async function poll() {
    const el = ensureBadge();
    try {
      const res = await fetch("/api/bca/estado", { cache: "no-store" });
      if (!res.ok) throw new Error("http " + res.status);
      const data = await res.json();
      const color = data.color || (data.necesita_intervencion ? "rojo" : "verde");
      el.dataset.color = color;
      const label = el.querySelector(".bca-label");
      if (label) label.textContent = data.etiqueta || "Estado del Sistema";
      el.title =
        "BCA: " +
        (data.bca_activo ? "activo" : "inactivo") +
        " · servidor: " +
        (data.servidor_ok ? "ok" : "caído");
    } catch (e) {
      el.dataset.color = "rojo";
      const label = el.querySelector(".bca-label");
      if (label) label.textContent = "Sin conexión";
      el.title = "No se pudo consultar el BCA";
    }
  }

  function boot() {
    ensureBadge();
    poll();
    setInterval(poll, 4000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
