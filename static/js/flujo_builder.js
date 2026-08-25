/**
 * Helios Flow Builder — estado staging + guardado unificado.
 */
(function (global) {
  const DRAFT_TTL_MS = 12 * 60 * 60 * 1000;

  function uid(prefix) {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  }

  function deepClone(o) {
    return JSON.parse(JSON.stringify(o));
  }

  function normalizeSnapshot(raw) {
    const data = deepClone(raw || { flujo: {}, etapas: [] });
    data.flujo = data.flujo || {};
    data.etapas = (data.etapas || []).map((e, i) => {
      const key = String(e.key || e.id || uid("temp-e"));
      return {
        id: e.id ?? null,
        key,
        nombre: e.nombre || `Etapa ${i + 1}`,
        descripcion: e.descripcion || "",
        orden: e.orden || i + 1,
        permite_retroceso: !!e.permite_retroceso,
        es_final: !!e.es_final,
        solicita_documentacion: !!e.solicita_documentacion,
        grupo_ids: e.grupo_ids || [],
        documentos: e.documentos || [],
        datos: (e.datos || []).map((d) => ({
          dato_id:
            d.dato_id != null && d.dato_id !== ""
              ? Number(d.dato_id)
              : d.id != null && d.id !== ""
                ? Number(d.id)
                : null,
          obligatorio: !!d.obligatorio,
          orden: d.orden != null && Number(d.orden) > 0 ? Number(d.orden) : null,
          depends_on: d.depends_on != null && d.depends_on !== "" ? Number(d.depends_on) : null,
          condition: d.condition || "true",
          required_when: !!d.required_when,
          disable_when_false: !!d.disable_when_false,
        })),
        estados: (e.estados || []).map((s, si) => ({
          id: s.id ?? null,
          key: String(s.key || s.id || uid("temp-s")),
          nombre: s.nombre || `Estado ${si + 1}`,
          es_inicial: !!s.es_inicial,
          cierra_etapa: !!s.cierra_etapa,
          api_call_id: s.api_call_id || null,
          transiciones: (s.transiciones || []).map((t) => ({
            id: t.id ?? null,
            estado_destino_key: String(t.estado_destino_key || t.estado_destino_id || ""),
          })),
          reglas: (s.reglas || []).map((r) => {
            let condiciones = (r.condiciones || []).map((c) => ({
              id: c.id ?? null,
              output_id: c.output_id != null && c.output_id !== "" ? Number(c.output_id) : null,
              operador: c.operador || "=",
              valor: c.valor != null ? String(c.valor) : "",
            }));
            if (!condiciones.length && r.output_id) {
              condiciones = [
                {
                  id: null,
                  output_id: Number(r.output_id),
                  operador: r.operador || "=",
                  valor: r.valor != null ? String(r.valor) : "",
                },
              ];
            }
            const c0 = condiciones[0] || {};
            return {
              id: r.id ?? null,
              nombre: r.nombre || "",
              logica: (r.logica || "AND").toUpperCase() === "OR" ? "OR" : "AND",
              modo_ejecucion:
                (r.modo_ejecucion || "AUTO").toUpperCase() === "MANUAL" ? "MANUAL" : "AUTO",
              prioridad: r.prioridad || 1,
              estado_destino_key: String(r.estado_destino_key || r.estado_destino_id || ""),
              condiciones,
              output_id: c0.output_id ?? r.output_id ?? null,
              operador: c0.operador || r.operador || "=",
              valor: c0.valor != null ? String(c0.valor) : r.valor || "",
            };
          }),
          reglas_datos: (s.reglas_datos || []).map((r) => ({
            id: r.id ?? null,
            nombre: r.nombre || "",
            logica: (r.logica || "AND").toUpperCase() === "OR" ? "OR" : "AND",
            prioridad: r.prioridad || 1,
            es_default: !!r.es_default,
            estado_destino_key: String(r.estado_destino_key || r.estado_destino_id || ""),
            condiciones: (r.condiciones || []).map((c) => ({
              id: c.id ?? null,
              dato_id: c.dato_id != null && c.dato_id !== "" ? Number(c.dato_id) : null,
              operador: c.operador || "==",
              valor: c.valor != null ? String(c.valor) : "",
              valor_hasta: c.valor_hasta != null ? String(c.valor_hasta) : "",
            })),
          })),
          mapeos_input: (s.mapeos_input || []).map((m) => ({
            id: m.id ?? null,
            parametro_id: m.parametro_id != null ? Number(m.parametro_id) : null,
            origen: m.origen || "fijo",
            valor_fijo: m.valor_fijo != null ? String(m.valor_fijo) : "",
            dato_id: m.dato_id != null && m.dato_id !== "" ? Number(m.dato_id) : null,
            campo_caso: m.campo_caso || "",
          })),
          mapeos_output: (s.mapeos_output || []).map((m) => ({
            id: m.id ?? null,
            output_id: m.output_id != null ? Number(m.output_id) : null,
            dato_id: m.dato_id != null && m.dato_id !== "" ? Number(m.dato_id) : null,
          })),
        })),
      };
    });
    data.etapas.forEach((e) => {
      if (!e.estados.length) {
        e.estados.push({
          id: null,
          key: uid("temp-s"),
          nombre: "Pendiente",
          es_inicial: true,
          cierra_etapa: false,
          api_call_id: null,
          transiciones: [],
          reglas: [],
          reglas_datos: [],
          mapeos_input: [],
          mapeos_output: [],
        });
      }
    });
    return data;
  }

  function createStore(initial, catalogos, flujoId) {
    let state = normalizeSnapshot(initial);
    let baseline = JSON.stringify(state);
    let dirty = false;
    let saving = false;
    let selectedEtapaKey = state.etapas[0]?.key || null;
    let tab = "props";
    const listeners = new Set();

    const draftKey = `helios-flow-draft-${flujoId}`;

    function seedMapeosFromApi(apiId) {
      const api = (catalogos.apis || []).find((a) => Number(a.id) === Number(apiId));
      if (!api) return { mapeos_input: [], mapeos_output: [] };
      return {
        mapeos_input: (api.parametros || []).map((p) => ({
          id: null,
          parametro_id: p.id,
          origen: p.origen || "fijo",
          valor_fijo: p.valor_fijo || "",
          dato_id: p.dato_id != null ? Number(p.dato_id) : null,
          campo_caso: p.campo_caso || "",
        })),
        mapeos_output: (api.outputs || []).map((o) => ({
          id: null,
          output_id: o.id,
          dato_id: null,
        })),
      };
    }

    // Hidratar mapeos faltantes desde el catálogo del API (sin marcar dirty)
    state.etapas.forEach((e) => {
      (e.estados || []).forEach((s) => {
        if (!s.api_call_id) return;
        const api = (catalogos.apis || []).find((a) => Number(a.id) === Number(s.api_call_id));
        if (!api) return;
        const seeded = seedMapeosFromApi(s.api_call_id);
        const haveIn = new Set((s.mapeos_input || []).map((m) => Number(m.parametro_id)));
        seeded.mapeos_input.forEach((m) => {
          if (!haveIn.has(Number(m.parametro_id))) {
            s.mapeos_input = s.mapeos_input || [];
            s.mapeos_input.push(m);
          }
        });
        const haveOut = new Set((s.mapeos_output || []).map((m) => Number(m.output_id)));
        seeded.mapeos_output.forEach((m) => {
          if (!haveOut.has(Number(m.output_id))) {
            s.mapeos_output = s.mapeos_output || [];
            s.mapeos_output.push(m);
          }
        });
      });
    });
    baseline = JSON.stringify(state);

    function emit() {
      listeners.forEach((fn) => fn(getPublic()));
    }

    function markDirty() {
      dirty = JSON.stringify(state) !== baseline;
      emit();
      saveDraft();
    }

    function saveDraft() {
      try {
        localStorage.setItem(
          draftKey,
          JSON.stringify({ ts: Date.now(), state, selectedEtapaKey, tab })
        );
      } catch (_) {}
    }

    function loadDraft() {
      try {
        const raw = localStorage.getItem(draftKey);
        if (!raw) return false;
        const parsed = JSON.parse(raw);
        if (!parsed?.ts || Date.now() - parsed.ts > DRAFT_TTL_MS) {
          localStorage.removeItem(draftKey);
          return false;
        }
        if (confirm("Hay un borrador local sin guardar de esta sesión. ¿Restaurar?")) {
          state = normalizeSnapshot(parsed.state);
          selectedEtapaKey = parsed.selectedEtapaKey || state.etapas[0]?.key || null;
          tab = parsed.tab || "props";
          dirty = true;
          emit();
          return true;
        }
        localStorage.removeItem(draftKey);
      } catch (_) {}
      return false;
    }

    function clearDraft() {
      try {
        localStorage.removeItem(draftKey);
      } catch (_) {}
    }

    function getPublic() {
      return {
        state,
        catalogos,
        dirty,
        saving,
        selectedEtapaKey,
        tab,
        selectedEtapa: state.etapas.find((e) => e.key === selectedEtapaKey) || null,
        allEstados: state.etapas.flatMap((e) =>
          e.estados.map((s) => ({
            ...s,
            etapa_key: e.key,
            etapa_nombre: e.nombre,
            label: `${e.nombre} · ${s.nombre}`,
          }))
        ),
      };
    }

    function replaceCatalogos(next) {
      if (!next || typeof next !== "object") return;
      catalogos = next;
      // Re-hidratar mapeos si el API ahora tiene parámetros/outputs nuevos
      state.etapas.forEach((e) => {
        (e.estados || []).forEach((s) => {
          if (!s.api_call_id) return;
          const api = (catalogos.apis || []).find((a) => Number(a.id) === Number(s.api_call_id));
          if (!api) return;
          const seeded = seedMapeosFromApi(s.api_call_id);
          const haveIn = new Set((s.mapeos_input || []).map((m) => Number(m.parametro_id)));
          seeded.mapeos_input.forEach((m) => {
            if (!haveIn.has(Number(m.parametro_id))) {
              s.mapeos_input = s.mapeos_input || [];
              s.mapeos_input.push(m);
            }
          });
          const haveOut = new Set((s.mapeos_output || []).map((m) => Number(m.output_id)));
          seeded.mapeos_output.forEach((m) => {
            if (!haveOut.has(Number(m.output_id))) {
              s.mapeos_output = s.mapeos_output || [];
              s.mapeos_output.push(m);
            }
          });
        });
      });
      emit();
    }

    async function refreshCatalogos() {
      const res = await fetch(`/flujos/${flujoId}/completo`, {
        headers: { Accept: "application/json" },
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "No se pudo recargar el catálogo");
      if (json.catalogos) replaceCatalogos(json.catalogos);
      return json.catalogos;
    }

    function subscribe(fn) {
      listeners.add(fn);
      fn(getPublic());
      return () => listeners.delete(fn);
    }

    function setFlowField(field, value) {
      state.flujo[field] = value;
      markDirty();
    }

    function selectEtapa(key) {
      selectedEtapaKey = key;
      emit();
    }

    function setTab(t) {
      tab = t;
      emit();
    }

    function addEtapa() {
      const key = uid("temp-e");
      state.etapas.push({
        id: null,
        key,
        nombre: `Nueva etapa ${state.etapas.length + 1}`,
        descripcion: "",
        orden: state.etapas.length + 1,
        permite_retroceso: false,
        es_final: false,
        solicita_documentacion: false,
        grupo_ids: [],
        documentos: [],
        datos: [],
        estados: [
          {
            id: null,
            key: uid("temp-s"),
            nombre: "Pendiente",
            es_inicial: true,
            cierra_etapa: false,
            api_call_id: null,
            transiciones: [],
            reglas: [],
            reglas_datos: [],
            mapeos_input: [],
            mapeos_output: [],
          },
        ],
      });
      selectedEtapaKey = key;
      tab = "props";
      markDirty();
    }

    function removeEtapa(key) {
      if (state.etapas.length <= 1) {
        alert("El flujo debe tener al menos una etapa.");
        return;
      }
      if (!confirm("¿Eliminar esta etapa del diseño? Se aplicará al guardar.")) return;
      state.etapas = state.etapas.filter((e) => e.key !== key);
      state.etapas.forEach((e, i) => (e.orden = i + 1));
      if (selectedEtapaKey === key) selectedEtapaKey = state.etapas[0]?.key || null;
      markDirty();
    }

    function updateEtapa(key, patch) {
      const e = state.etapas.find((x) => x.key === key);
      if (!e) return;
      Object.assign(e, patch);
      markDirty();
    }

    function moveEtapa(key, dir) {
      const i = state.etapas.findIndex((e) => e.key === key);
      const j = i + dir;
      if (i < 0 || j < 0 || j >= state.etapas.length) return;
      const tmp = state.etapas[i];
      state.etapas[i] = state.etapas[j];
      state.etapas[j] = tmp;
      state.etapas.forEach((e, idx) => (e.orden = idx + 1));
      markDirty();
    }

    function addEstado(etapaKey) {
      const e = state.etapas.find((x) => x.key === etapaKey);
      if (!e) return;
      e.estados.push({
        id: null,
        key: uid("temp-s"),
        nombre: `Estado ${e.estados.length + 1}`,
        es_inicial: e.estados.length === 0,
        cierra_etapa: false,
        api_call_id: null,
        transiciones: [],
        reglas: [],
        reglas_datos: [],
        mapeos_input: [],
        mapeos_output: [],
      });
      markDirty();
    }

    function updateEstado(etapaKey, estadoKey, patch) {
      const e = state.etapas.find((x) => x.key === etapaKey);
      const s = e?.estados.find((x) => x.key === estadoKey);
      if (!s) return;
      const changingApi = Object.prototype.hasOwnProperty.call(patch, "api_call_id");
      const prevApi = s.api_call_id;
      Object.assign(s, patch);
      if (patch.es_inicial) {
        e.estados.forEach((x) => {
          if (x.key !== estadoKey) x.es_inicial = false;
        });
      }
      if (changingApi && Number(patch.api_call_id || 0) !== Number(prevApi || 0)) {
        if (!patch.api_call_id) {
          s.mapeos_input = [];
          s.mapeos_output = [];
          s.reglas = [];
        } else {
          const seeded = seedMapeosFromApi(patch.api_call_id);
          s.mapeos_input = seeded.mapeos_input;
          s.mapeos_output = seeded.mapeos_output;
          s.reglas = [];
        }
      }
      markDirty();
    }

    function removeEstado(etapaKey, estadoKey) {
      const e = state.etapas.find((x) => x.key === etapaKey);
      if (!e || e.estados.length <= 1) {
        alert("Cada etapa necesita al menos un estado.");
        return;
      }
      e.estados = e.estados.filter((s) => s.key !== estadoKey);
      if (!e.estados.some((s) => s.es_inicial)) e.estados[0].es_inicial = true;
      // limpiar referencias
      state.etapas.forEach((et) => {
        et.estados.forEach((st) => {
          st.transiciones = st.transiciones.filter((t) => t.estado_destino_key !== estadoKey);
          st.reglas = st.reglas.filter((r) => r.estado_destino_key !== estadoKey);
        });
      });
      markDirty();
    }

    function payload() {
      return deepClone(state);
    }

    async function save() {
      if (saving) return { ok: false, error: "Ya se está guardando…" };
      saving = true;
      emit();
      try {
        const res = await fetch(`/flujos/${flujoId}/guardar-completo`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload()),
        });
        const json = await res.json();
        if (!json.ok) throw new Error(json.error || "Error al guardar");
        state = normalizeSnapshot(json.data);
        baseline = JSON.stringify(state);
        dirty = false;
        if (!state.etapas.find((e) => e.key === selectedEtapaKey)) {
          selectedEtapaKey = state.etapas[0]?.key || null;
        }
        clearDraft();
        saving = false;
        emit();
        return { ok: true, message: json.message || "Guardado" };
      } catch (err) {
        saving = false;
        emit();
        return { ok: false, error: err.message || String(err) };
      }
    }

    return {
      subscribe,
      getPublic,
      setFlowField,
      selectEtapa,
      setTab,
      addEtapa,
      removeEtapa,
      updateEtapa,
      moveEtapa,
      addEstado,
      updateEstado,
      removeEstado,
      replaceCatalogos,
      refreshCatalogos,
      markDirty,
      save,
      loadDraft,
      payload,
    };
  }

  global.HeliosFlowBuilder = { createStore, normalizeSnapshot, uid };
})(window);
