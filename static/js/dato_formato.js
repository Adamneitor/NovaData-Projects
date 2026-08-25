/**
 * Máscaras ligeras para datos complementarios.
 * El valor enviado al servidor puede ir formateado; el backend lo normaliza a RAW.
 */
(function (global) {
  function onlyDigits(s) {
    return String(s || "").replace(/\D/g, "");
  }

  function formatPhone(digits) {
    if (digits.length === 11 && digits[0] === "1") {
      return `+${digits[0]}(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
    }
    if (digits.length === 10) {
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
    }
    if (digits.length > 1) return `+${digits}`;
    return digits;
  }

  function formatMoney(raw, decimals, withSymbol) {
    const cleaned = String(raw || "").replace(/[^\d.-]/g, "");
    if (!cleaned || cleaned === "-" || cleaned === ".") return cleaned;
    const neg = cleaned.startsWith("-");
    const parts = cleaned.replace("-", "").split(".");
    let whole = parts[0].replace(/^0+(?=\d)/, "") || "0";
    let frac = (parts[1] || "").slice(0, decimals);
    whole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    let body = decimals > 0 && (cleaned.includes(".") || frac) ? `${whole}.${frac}` : whole;
    if (withSymbol) body = `$${body}`;
    return neg ? `-${body}` : body;
  }

  function applyMask(input) {
    const formato = input.dataset.datoFormato || "texto";
    const dec = parseInt(input.dataset.datoDecimales || "2", 10);
    const start = input.selectionStart;
    const before = input.value;
    let next = before;

    if (formato === "telefono") {
      next = formatPhone(onlyDigits(before).slice(0, 15));
    } else if (formato === "moneda" || formato === "numero") {
      next = formatMoney(before, 0, formato === "moneda");
    } else if (formato === "moneda_decimal" || formato === "numero_decimal") {
      next = formatMoney(before, dec, formato === "moneda_decimal");
    }

    if (next !== before) {
      input.value = next;
      try {
        const delta = next.length - before.length;
        const pos = Math.max(0, (start || 0) + delta);
        input.setSelectionRange(pos, pos);
      } catch (_) {}
    }
  }

  function bind(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-dato-formato]").forEach((el) => {
      if (el.dataset.maskBound) return;
      el.dataset.maskBound = "1";
      el.addEventListener("input", () => applyMask(el));
      el.addEventListener("blur", () => applyMask(el));
      if (el.value) applyMask(el);
    });
  }

  global.HeliosDatoFormato = { bind, applyMask };
  document.addEventListener("DOMContentLoaded", () => bind(document));
})(window);
