// log.js — "Refresh Logs" re-fetches the plain-text log and re-renders lines.
(function () {
  "use strict";
  function classify(line) {
    const low = line.toLowerCase();
    if (line.startsWith("$ ")) return "cmd";
    if (low.startsWith("rsync:") || low.includes("error")) return "stderr";
    if (/^(number of|total|sent|speedup|file list)/.test(low)) return "stat";
    return "";
  }
  function renderLines(body, text) {
    body.innerHTML = "";
    const lines = text.split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    lines.forEach((line, i) => {
      const row = document.createElement("div");
      row.className = "log-line " + classify(line);
      const ln = document.createElement("span");
      ln.className = "ln";
      ln.textContent = String(i + 1);
      const lc = document.createElement("span");
      lc.className = "lc";
      lc.textContent = line;
      row.appendChild(ln);
      row.appendChild(lc);
      body.appendChild(row);
    });
  }
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-refresh-log]");
    if (!btn) return;
    const url = btn.getAttribute("data-refresh-log");
    const panel = btn.closest(".log-panel");
    const body = panel && panel.querySelector(".log-body");
    try {
      const resp = await fetch(url, { credentials: "same-origin" });
      const text = await resp.text();
      if (body) renderLines(body, text);
    } catch (err) {
      /* network error: leave last content in place */
    }
  });
})();
