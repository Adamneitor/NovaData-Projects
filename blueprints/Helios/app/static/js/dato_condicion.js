/**
 * Runtime: reglas condicionales de datos adicionales.
 * data-depends-on, data-required-when, data-disable-when-false en .data-field / .df-field
 */
(function (global) {
  const TRUE = new Set(["si", "sí", "true", "1", "yes", "s"]);

  function isTrue(v) {
    return TRUE.has(String(v || "").trim().toLowerCase());
  }

  function controllerValue(form, dependsOn) {
    const el = form.querySelector(`[name="dato_${dependsOn}"]`);
    return el ? el.value : "";
  }

  function applyField(field, form) {
    const dependsOn = field.dataset.dependsOn;
    if (!dependsOn) {
      field.classList.remove("is-cond-disabled");
      return;
    }
    const requiredWhen = field.dataset.requiredWhen === "1";
    const disableWhenFalse = field.dataset.disableWhenFalse === "1";
    const met = isTrue(controllerValue(form, dependsOn));
    const enabled = met || !disableWhenFalse;
    const required = enabled && (requiredWhen ? met : field.dataset.baseRequired === "1");

    const inputs = field.querySelectorAll("input, select, textarea");
    inputs.forEach((inp) => {
      if (inp.type === "hidden") return;
      inp.disabled = !enabled || field.dataset.locked === "1";
      if (!enabled) {
        // Bonus: limpiar valor al deshabilitar
        if (inp.tagName === "SELECT") inp.selectedIndex = 0;
        else if (inp.type !== "checkbox") inp.value = "";
      }
    });

    field.classList.toggle("is-cond-disabled", !enabled);
    const reqMark = field.querySelector(".df-req, em.req-star, .df-req");
    const labelEm = field.querySelector("label .df-req, label em");
    const star = labelEm || reqMark;
    if (star) star.classList.toggle("d-none", !required);
    else if (required) {
      // ensure asterisk visible via data
    }
    field.dataset.effectiveRequired = required ? "1" : "0";

    const hint = field.querySelector("[data-cond-hint]");
    if (hint) {
      hint.classList.toggle("d-none", enabled);
    }
  }

  function refresh(form) {
    if (!form) return;
    form.querySelectorAll("[data-depends-on]").forEach((field) => applyField(field, form));
  }

  function bind(form) {
    if (!form || form.dataset.condBound) return;
    form.dataset.condBound = "1";
    form.addEventListener("change", (ev) => {
      const name = ev.target?.name || "";
      if (!name.startsWith("dato_")) return;
      refresh(form);
    });
    refresh(form);
  }

  function bindAll(root) {
    (root || document)
      .querySelectorAll("form.js-datos-ajax, #formDatosAdicionales, #formDatosInline, #seccion-datos form")
      .forEach(bind);
  }

  global.HeliosDatoCondicion = { bind, bindAll, refresh, isTrue };
  document.addEventListener("DOMContentLoaded", () => bindAll(document));
})(window);
