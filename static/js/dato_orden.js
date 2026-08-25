/**
 * Orden de datos adicionales: autoíndice al seleccionar + swap + secuencia 1..N.
 * Todo elemento seleccionado tiene orden (nunca null).
 */
(function (global) {
  function parseOrden(v) {
    if (v === "" || v === null || v === undefined) return null;
    const n = parseInt(v, 10);
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  function siguienteDisponible(items) {
    const usados = items.map((i) => i.orden).filter((n) => n != null);
    return usados.length ? Math.max(...usados) + 1 : 1;
  }

  function compactar(items) {
    const rows = items.map((i) => ({ ...i }));
    const ranked = rows
      .slice()
      .sort((a, b) => {
        const aNull = a.orden == null;
        const bNull = b.orden == null;
        if (aNull !== bNull) return aNull ? 1 : -1;
        return (a.orden || 0) - (b.orden || 0) || a.id - b.id;
      });
    ranked.forEach((item, idx) => {
      item.orden = idx + 1;
    });
    return ranked;
  }

  function aplicarCambio(items, id, nuevoOrden) {
    const rows = items.map((i) => ({ ...i }));
    const target = rows.find((r) => String(r.id) === String(id));
    if (!target) return compactar(rows);

    const next = parseOrden(nuevoOrden);
    if (next == null) {
      // No nulos: enviar al final
      target.orden = siguienteDisponible(rows) + 1000;
      return compactar(rows);
    }

    const other = rows.find((r) => String(r.id) !== String(id) && r.orden === next);
    if (other) {
      other.orden = target.orden;
      target.orden = next;
    } else {
      target.orden = next;
    }
    return compactar(rows);
  }

  function asignarAlSeleccionar(items, id, obligatorio) {
    const rows = items.map((i) => ({ ...i }));
    const existing = rows.find((r) => String(r.id) === String(id));
    const nxt = siguienteDisponible(rows);
    if (!existing) {
      rows.push({ id, obligatorio: !!obligatorio, orden: nxt });
    } else if (existing.orden == null) {
      existing.orden = nxt;
    }
    return compactar(rows);
  }

  global.HeliosDatoOrden = {
    parseOrden,
    compactar,
    aplicarCambio,
    siguienteDisponible,
    asignarAlSeleccionar,
  };
})(window);
