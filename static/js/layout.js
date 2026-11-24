// layout.js — app chrome, CSRF-aware fetch helpers, toasts, confirm dialogs.
(function () {
  "use strict";

  // ---- Mobile nav toggle -------------------------------------------------
  const navToggle = document.getElementById("navToggle");
  const nav = document.getElementById("nav");
  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  // ---- CSRF helpers ------------------------------------------------------
  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  async function post(url, body) {
    const form = new URLSearchParams();
    if (body) for (const [k, v] of Object.entries(body)) form.append(k, v);
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRF-Token": csrfToken(),
        Accept: "application/json",
      },
      body: form.toString(),
      credentials: "same-origin",
    });
    let data = null;
    try {
      data = await resp.json();
    } catch (e) {
      data = null;
    }
    return { ok: resp.ok, status: resp.status, data };
  }

  // ---- Toasts ------------------------------------------------------------
  function toast(message, kind) {
    const host = document.getElementById("toasts");
    if (!host) return;
    const el = document.createElement("div");
    el.className = "toast" + (kind ? " " + kind : "");
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity .3s";
      setTimeout(() => el.remove(), 320);
    }, 4200);
  }

  // ---- Confirm dialog (native <dialog>) ---------------------------------
  function confirmDialog(opts) {
    return new Promise((resolve) => {
      const dlg = document.createElement("dialog");
      dlg.className = "modal";
      dlg.innerHTML =
        '<form method="dialog" class="modal-body">' +
        '<div class="modal-title">' +
        (opts.danger ? "&#9888; " : "") +
        "<h3>" +
        (opts.title || "") +
        "</h3></div>" +
        '<p class="muted">' +
        (opts.message || "") +
        "</p>" +
        '<div class="modal-actions">' +
        '<button class="btn btn-ghost" value="cancel">' +
        (opts.cancelLabel || "Cancel") +
        "</button>" +
        '<button class="btn ' +
        (opts.danger ? "btn-danger" : "btn-primary") +
        '" value="ok">' +
        (opts.confirmLabel || "OK") +
        "</button>" +
        "</div></form>";
      document.body.appendChild(dlg);
      dlg.addEventListener("close", () => {
        resolve(dlg.returnValue === "ok");
        dlg.remove();
      });
      dlg.showModal();
    });
  }

  window.MG = { post, toast, confirmDialog, csrfToken };

  // Auto-wire forms carrying data-confirm before submit.
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    const msg = form.getAttribute("data-confirm");
    if (msg) {
      const label = form.getAttribute("data-confirm-label") || "Confirm Job Deletion";
      const ok = await confirmDialog({
        title: msg,
        message: form.getAttribute("data-confirm-message") || "",
        confirmLabel: label,
        danger: form.getAttribute("data-confirm-danger") !== "false",
        cancelLabel: "Cancel",
      });
      if (!ok) e.preventDefault();
    }
  });
})();
