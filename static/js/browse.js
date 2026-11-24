// browse.js — lazy directory picker using /api/tree (one level at a time).
(function () {
  "use strict";

  let dialog = null;
  let current = "/";
  let targetInput = null;

  function ensureDialog() {
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.className = "modal browse-modal";
    dialog.innerHTML =
      '<div class="modal-body">' +
      '<div class="modal-title"><h3>Browse</h3><span class="spacer"></span>' +
      '<button class="btn btn-ghost btn-sm" data-close type="button">Cancel</button></div>' +
      '<div class="browse-crumb" style="margin-bottom:10px"></div>' +
      '<div class="tree browse-list" style="max-height:48vh;overflow:auto" role="tree"></div>' +
      '<div class="modal-actions">' +
      '<button class="btn btn-ghost" data-up type="button">Up</button>' +
      '<button class="btn btn-primary" data-select type="button">Select this folder</button>' +
      "</div></div>";
    document.body.appendChild(dialog);
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog || e.target.closest("[data-close]")) dialog.close();
      if (e.target.closest("[data-up]")) go(upOne(current));
    });
    dialog.querySelector("[data-select]").addEventListener("click", () => {
      if (targetInput) {
        targetInput.value = current;
        targetInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
      dialog.close();
    });
    return dialog;
  }

  function upOne(p) {
    const trimmed = p.replace(/\/+$/, "");
    if (!trimmed || trimmed === "/") return "/";
    const idx = trimmed.lastIndexOf("/");
    return idx <= 0 ? "/" : trimmed.slice(0, idx);
  }

  async function go(path) {
    const dlg = ensureDialog();
    const list = dlg.querySelector(".browse-list");
    const crumb = dlg.querySelector(".browse-crumb");
    list.innerHTML =
      '<div class="tree-node"><div class="skeleton" style="width:60%"></div></div>' +
      '<div class="tree-node"><div class="skeleton" style="width:40%"></div></div>';
    crumb.textContent = path;
    try {
      const resp = await fetch("/api/tree?path=" + encodeURIComponent(path), {
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!resp.ok) {
        current = path;
        list.innerHTML = '<div class="tree-node"><span class="tname">' + (data.error || "Cannot list") + "</span></div>";
        return;
      }
      current = data.path;
      crumb.textContent = data.path;
      list.innerHTML = "";
      const dirs = (data.children || []).filter((c) => c.kind === "dir" || c.kind === "symlink");
      if (!dirs.length) {
        list.innerHTML = '<div class="tree-node"><span class="tname muted">(no folders)</span></div>';
      }
      dirs.forEach((d) => {
        const row = document.createElement("div");
        row.className = "tree-node";
        row.setAttribute("role", "treeitem");
        row.innerHTML =
          '<span class="twisty"></span><span class="ticon folder"></span>' +
          '<span class="tname"></span>';
        row.querySelector(".ticon").appendChild(
          svgIcon("folder")
        );
        row.querySelector(".tname").textContent = d.name;
        row.addEventListener("click", () => go(d.path));
        list.appendChild(row);
      });
    } catch (err) {
      list.innerHTML = '<div class="tree-node"><span class="tname">Browse failed</span></div>';
    }
  }

  function svgIcon() {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("width", "16");
    s.setAttribute("height", "16");
    s.setAttribute("fill", "none");
    s.setAttribute("stroke", "currentColor");
    s.setAttribute("stroke-width", "1.5");
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z");
    s.appendChild(p);
    return s;
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-browse]");
    if (!btn) return;
    targetInput = document.querySelector(btn.getAttribute("data-target"));
    const start = btn.getAttribute("data-start") || (targetInput && targetInput.value) || "/";
    const dlg = ensureDialog();
    dlg.querySelector(".modal-title h3").textContent =
      btn.getAttribute("data-kind") === "source" ? "Browse Source" : "Browse Destination";
    dlg.showModal();
    go(start && start !== "" ? start : "/");
  });

  window.MGBrowse = { go };
})();
