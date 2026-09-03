/**
 * Guardado no destructivo de datos adicionales.
 * - No recarga en error
 * - Conserva valores del formulario
 * - Errores inline por campo
 */
(function (global) {
  function clearFieldErrors(form) {
    form.querySelectorAll(".data-field").forEach((field) => {
      field.classList.remove("is-error");
      const box = field.querySelector("[data-field-error]");
      if (box) {
        box.classList.add("d-none");
        box.innerHTML = "";
      }
    });
    const banner = form.querySelector("[data-datos-error-banner]");
    if (banner) banner.remove();
  }

  function showFieldError(form, fieldName, message) {
    const input = form.querySelector(`[name="${fieldName}"]`);
    const field = input?.closest(".data-field");
    if (!field) return;
    field.classList.add("is-error");
    let box = field.querySelector("[data-field-error]");
    if (!box) {
      box = document.createElement("div");
      box.className = "field-error";
      box.setAttribute("data-field-error", "");
      field.appendChild(box);
    }
    box.classList.remove("d-none");
    box.innerHTML = `<i class="bi bi-exclamation-circle"></i> ${escapeHtml(message)}`;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showBanner(form, text) {
    let banner = form.querySelector("[data-datos-error-banner]");
    if (!banner) {
      banner = document.createElement("div");
    banner.className = "alert alert-danger hx-datos-banner";
    banner.setAttribute("data-datos-error-banner", "1");
    const card = form.querySelector(".hx-datos-card");
    if (card) form.insertBefore(banner, card);
    else form.prepend(banner);
    }
    banner.innerHTML = `<strong><i class="bi bi-exclamation-triangle-fill"></i> ${escapeHtml(text)}</strong>`;
  }

  function clientValidate(form) {
    const errors = [];
    form.querySelectorAll("[name^='dato_']").forEach((el) => {
      if (el.disabled) return;
      const field = el.closest(".data-field, .df-field");
      if (field?.classList.contains("is-cond-disabled")) return;
      const formato = el.dataset.datoFormato || "";
      const codigo = el.dataset.datoCodigo || "";
      const val = (el.value || "").trim();
      const required =
        field?.dataset.effectiveRequired === "1" || field?.dataset.baseRequired === "1";
      const digitsOnly = val.replace(/RD\$/gi, "").replace(/[\s,$]/g, "").replace(/,/g, "");
      if (!val || digitsOnly === "") {
        if (required) errors.push({ field: el.name, message: "Este campo es obligatorio." });
        return;
      }
      if (formato === "telefono" || codigo === "telefono") {
        const digits = val.replace(/\D/g, "");
        if (digits.length < 10) {
          errors.push({
            field: el.name,
            message: "Formato inválido. Ejemplo: +1(000) 000-0000 (mín. 10 dígitos).",
          });
        } else if (digits.length > 15) {
          errors.push({ field: el.name, message: "El teléfono no puede superar 15 dígitos." });
        }
      }
      if (codigo === "numero" || codigo === "moneda" || formato === "numero" || formato === "moneda") {
        const normalized = digitsOnly.replace(/\.0+$/, "");
        if (!/^-?\d+$/.test(normalized)) {
          errors.push({ field: el.name, message: "Solo se permiten números enteros (sin decimales)." });
        }
      }
      if (
        codigo === "numero_decimal" ||
        codigo === "moneda_decimal" ||
        formato === "numero_decimal" ||
        formato === "moneda_decimal"
      ) {
        if (!/^-?\d+(\.\d+)?$/.test(digitsOnly)) {
          errors.push({ field: el.name, message: "Valor numérico inválido." });
        }
      }
    });
    return errors;
  }

  function validateField(el) {
    if (!el?.name?.startsWith("dato_")) return null;
    const wrap = document.createElement("form");
    wrap.appendChild(el.cloneNode(true));
    const errs = clientValidate(wrap);
    return errs[0] || null;
  }

  function focusFirstError(form, errors) {
    if (!errors?.length) return;
    const first = errors[0];
    const input = form.querySelector(`[name="${first.field}"]`);
    const field = input?.closest(".data-field") || input;
    if (field?.scrollIntoView) field.scrollIntoView({ behavior: "smooth", block: "center" });
    try {
      input?.focus({ preventScroll: true });
    } catch (_) {
      input?.focus();
    }
  }

  function applyErrors(form, errors) {
    clearFieldErrors(form);
    if (!errors?.length) return;
    showBanner(form, "Corrija los campos marcados. Sus datos se conservaron.");
    errors.forEach((e) => {
      if (e.field && e.field !== "_form") showFieldError(form, e.field, e.message);
    });
    focusFirstError(form, errors);
  }

  async function submitAjax(form) {
    const btn = form.querySelector('[type="submit"]');
    const prev = btn?.innerHTML;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';
    }

    const localErrors = clientValidate(form);
    if (localErrors.length) {
      applyErrors(form, localErrors);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = prev;
      }
      return;
    }

    try {
      const body = new FormData(form);
      const res = await fetch(form.action, {
        method: "POST",
        body,
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      let json = null;
      try {
        json = await res.json();
      } catch (_) {
        // Si el backend no devolvió JSON, no recargar: mostrar error genérico
        applyErrors(form, [{ field: "_form", message: "No se pudo guardar. Intente de nuevo." }]);
        return;
      }

      if (!json.success) {
        // Conservar valores actuales del DOM (no tocar inputs)
        applyErrors(form, json.errors || [{ field: "_form", message: "Error de validación." }]);
        return;
      }

      clearFieldErrors(form);
      if (json.redirect) {
        window.location.href = json.redirect;
        return;
      }
      window.location.reload();
    } catch (err) {
      applyErrors(form, [{ field: "_form", message: err.message || "Error de red." }]);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = prev;
      }
    }
  }

  function bindForm(form) {
    if (!form || form.dataset.datosAjaxBound) return;
    form.dataset.datosAjaxBound = "1";
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      submitAjax(form);
    });
    // Limpiar error del campo al editar; validación ligera al salir del campo
    form.addEventListener("input", (ev) => {
      const field = ev.target?.closest?.(".data-field");
      if (!field) return;
      field.classList.remove("is-error");
      const box = field.querySelector("[data-field-error]");
      if (box) {
        box.classList.add("d-none");
        box.innerHTML = "";
      }
    });
    form.addEventListener("focusout", (ev) => {
      const el = ev.target;
      if (!el?.name?.startsWith("dato_") || !(el.value || "").trim()) return;
      const err = validateField(el);
      if (err) showFieldError(form, el.name, err.message);
    });
  }

  function bindAll(root) {
    (root || document).querySelectorAll("form.js-datos-ajax, #formDatosAdicionales, #seccion-datos form").forEach(bindForm);
  }

  global.HeliosDatosForm = { bindAll, bindForm, applyErrors };
  document.addEventListener("DOMContentLoaded", () => bindAll(document));
})(window);
