// schedule.js — show only the controls relevant to the chosen schedule mode,
// and render a plain-English preview of the interval ("Every 2 days at 9:00 AM").
(function () {
  "use strict";

  const form = document.getElementById("saveform");
  if (!form) return;

  const group = form.querySelector('[data-group="interval"]');
  const radios = form.querySelectorAll('input[name="schedule_kind"]');
  const dateEl = form.querySelector('input[name="schedule_start_date"]');
  const timeEl = form.querySelector('input[name="schedule_run_time"]');
  const valueEl = form.querySelector('input[name="schedule_interval_value"]');
  const unitEl = form.querySelector('select[name="schedule_interval_unit"]');
  const preview = document.getElementById("schedulePreview");

  function current() {
    const r = form.querySelector('input[name="schedule_kind"]:checked');
    return r ? r.value : "none";
  }

  function clock24to12(hhmm) {
    if (!hhmm) return "";
    const [h, m] = hhmm.split(":").map(Number);
    const suffix = h < 12 ? "AM" : "PM";
    const h12 = h % 12 || 12;
    return h12 + ":" + String(m).padStart(2, "0") + " " + suffix;
  }

  function render() {
    const scheduled = current() === "interval";
    if (group) group.hidden = !scheduled;
    if (preview && scheduled) {
      const n = parseInt(valueEl && valueEl.value, 10);
      const unit = unitEl ? unitEl.value : "days";
      const word = n === 1 ? unit.replace(/s$/, "") : unit;
      const parts = [];
      if (n >= 1) parts.push("Every " + n + " " + word);
      const t = clock24to12(timeEl && timeEl.value);
      if (t) parts.push("at " + t);
      preview.textContent = parts.join(" ");
    } else if (preview) {
      preview.textContent = "";
    }
  }

  radios.forEach((r) => r.addEventListener("change", render));
  [dateEl, timeEl, valueEl, unitEl].forEach((el) => {
    if (el) el.addEventListener("input", render);
  });

  render();
})();
