// main.js — Búsqueda AJAX en vivo para formularios GET con [data-live="search"]
// Reemplaza: <tbody id="list-body">, <nav id="list-pagination"> y <small id="list-pagination-label">
// Funciona con input (q), selects, paginación y submit. Si falla AJAX, el form sigue funcionando normal.

(function () {
  // ---- Config ----
  const DEBUG_LIVE = false; // <- pon true si quieres ver logs en consola

  // ---- Utils ----
  function log() {
    if (!DEBUG_LIVE) return;
    try { console.log.apply(console, arguments); } catch (_) {}
  }
  function isAbort(err) {
    return err && (err.name === "AbortError" ||
                   String(err).includes("AbortError") ||
                   String(err).includes("signal is aborted"));
  }

  // Evita respuestas que llegan desordenadas
  let currentAbort = null;

  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function serializeForm(form) {
    const fd = new FormData(form);
    const params = new URLSearchParams();
    for (const [k, v] of fd.entries()) {
      if (v !== null && v !== undefined) params.append(k, String(v));
    }
    return params.toString();
  }

  function extractAndSwap(htmlText, form) {
    const dom = document.createElement("html");
    dom.innerHTML = htmlText;

    const newBody  = dom.querySelector("#list-body");
    const newPagi  = dom.querySelector("#list-pagination");
    const newLabel = dom.querySelector("#list-pagination-label");

    const curBody  = document.getElementById("list-body");
    const curPagi  = document.getElementById("list-pagination");
    const curLabel = document.getElementById("list-pagination-label");

    if (newBody && curBody)   curBody.replaceWith(newBody);
    if (newPagi && curPagi)   curPagi.replaceWith(newPagi);
    if (newLabel && curLabel) curLabel.replaceWith(newLabel);

    // Re-engancha paginación
    wirePagination(form);
  }

  async function doFetch(url, form) {
    if (currentAbort) currentAbort.abort();
    const ctrl = new AbortController();
    currentAbort = ctrl;

    const headers = { "X-Requested-With": "XMLHttpRequest" };

    const resp = await fetch(url, { headers, signal: ctrl.signal, credentials: "same-origin" });
    if (!resp.ok) {
      if (resp.status >= 500) throw new Error("HTTP " + resp.status);
      // 4xx: seguimos mostrando la respuesta si existe
    }
    const html = await resp.text();
    extractAndSwap(html, form);
  }

  function refreshFromForm(form) {
    const base = form.getAttribute("action") || window.location.pathname;
    const qs   = serializeForm(form);
    const url  = qs ? `${base}?${qs}` : base;
    return doFetch(url, form);
  }

  function refreshFromURL(url, form) {
    return doFetch(url, form);
  }

  function wirePagination(form) {
    const pag = document.getElementById("list-pagination");
    if (!pag) return;

    pag.querySelectorAll("a.page-link[href]").forEach(a => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        const url = a.getAttribute("href");
        if (!url) return;
        refreshFromURL(url, form)
          .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
      }, { once: true }); // se re-engancha tras cada swap
    });
  }

  function setupLiveSearch(root) {
    root.querySelectorAll('form[method="get"][data-live="search"]').forEach(form => {
      // Submit (Enter/botón) sin recargar
      form.addEventListener("submit", (ev) => {
        ev.preventDefault();
        refreshFromForm(form)
          .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
      });

      // Input de búsqueda
      const q = form.querySelector('input[name="q"]');
      if (q) {
        // Evitar que Enter recargue la página
        q.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter") {
            ev.preventDefault();
            form.dispatchEvent(new Event("submit", { cancelable: true })); // dispara AJAX
          }
        });

        const debounced = debounce(() => {
          if (!q.value) {
            const base = form.getAttribute("action") || window.location.pathname;
            const url  = `${base}?q=`;
            refreshFromURL(url, form)
              .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
          } else {
            refreshFromForm(form)
              .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
          }
        }, 250);

        q.addEventListener("input", debounced);
        q.addEventListener("search", debounced); // cuando limpian con la “X”
      }

      // Selects / checkboxes / radio
      form.querySelectorAll("select, input[type='checkbox'], input[type='radio']").forEach(el => {
        el.addEventListener("change", () => {
          refreshFromForm(form)
            .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
        });
      });

      // Paginación inicial
      wirePagination(form);

      // Si llegamos con q vacía, cargamos lista limpia
      if (q && !q.value) {
        refreshFromForm(form)
          .catch(err => { if (!isAbort(err)) log("[live-search] error:", err?.message || err); });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupLiveSearch(document);
    log("[live-search] listo");
  });
})();
