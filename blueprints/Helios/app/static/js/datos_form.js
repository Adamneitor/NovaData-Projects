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

  function isSiNo(val) {
    return /^(si|sí|no|true|false|yes|s|n)$/i.test(String(val || "").trim());
  }

  function digitsOf(val) {
    return String(val || "")
      .replace(/RD\s*\$/gi, "")
      .replace(/[\s\u00a0\u202f\u2007,$]/g, "")
      .replace(/,/g, "");
  }

  function clientValidate(form) {
    const errors = [];
    form.querySelectorAll("[name^='dato_']").forEach((el) => {
      if (el.type === "hidden") return;
      if (el.disabled) return;
      const field = el.closest(".data-field, .df-field");
      if (field?.classList.contains("is-cond-disabled")) return;
      const formato = el.dataset.datoFormato || field?.dataset.datoFormato || "";
      const codigo = el.dataset.datoCodigo || field?.dataset.datoCodigo || "";
      const val = (el.value || "").trim();
      const required =
        field?.dataset.effectiveRequired === "1" || field?.dataset.baseRequired === "1";
      const isSelect = el.tagName === "SELECT" || codigo === "booleano" || codigo === "lista";
      if (!val) {
        if (required) errors.push({ field: el.name, message: "Este campo es obligatorio." });
        return;
      }
      if (isSelect || isSiNo(val)) return;
      /* No bloquear el POST por máscara de moneda/número: el servidor normaliza. */
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
        return;
      }
    });
    return errors;
  }

  function collectPayload(form) {
    const payload = { return_to: "form" };
    const ret = form.querySelector('[name="return_to"]');
    if (ret) payload.return_to = ret.value || "form";
    form.querySelectorAll("[name^='dato_']").forEach((el) => {
      if (el.type === "hidden" && !el.name.startsWith("dato_")) return;
      payload[el.name] = el.value || "";
    });
    return payload;
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
    const fieldErrors = errors.filter((e) => e.field && e.field !== "_form");
    const formError = errors.find((e) => !e.field || e.field === "_form");
    const message = formError?.message || (
      fieldErrors.length === 1
        ? "Revise el campo marcado. El valor ingresado se conserva."
        : `Revise los ${fieldErrors.length} campos marcados. Los valores ingresados se conservan.`
    );
    global.HeliosToast?.show(message, "danger", { duration: 60000 });
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
      const res = await fetch(form.getAttribute("action") || window.location.pathname, {
        method: "POST",
        body: JSON.stringify(collectPayload(form)),
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
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
      try {
        sessionStorage.setItem(
          "helios-pending-toast",
          JSON.stringify({ message: json.message || "Datos guardados.", level: "success" })
        );
      } catch (_) {}
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
