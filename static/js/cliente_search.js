/**
 * Autocomplete de clientes Helios — debounce + paginación ligera.
 * Uso:
 *   HeliosClienteSearch.mount('#wrap', {
 *     inputName: 'cliente_id',
 *     required: true,
 *     preselect: { id, label } | null,
 *     onSelect: (item) => {}
 *   });
 */
window.HeliosClienteSearch = (function () {
  const API = '/catalogos/api/clientes/buscar';

  function mount(rootSel, opts = {}) {
    const root = typeof rootSel === 'string' ? document.querySelector(rootSel) : rootSel;
    if (!root) return;

    const required = !!opts.required;
    const inputName = opts.inputName || 'cliente_id';
    const minChars = opts.minChars || 2;

    root.innerHTML = `
      <div class="helios-cli-search position-relative">
        <label class="form-label">${opts.label || 'Cliente'}${required ? ' <span class="text-danger">*</span>' : ''}</label>
        <div class="input-group">
          <span class="input-group-text"><i class="bi bi-search"></i></span>
          <input type="text" class="form-control helios-cli-q" placeholder="Buscar por nombre, cédula/RNC, teléfono o correo..." autocomplete="off">
          <button type="button" class="btn btn-outline-secondary helios-cli-clear" title="Limpiar">&times;</button>
        </div>
        <input type="hidden" class="helios-cli-id" name="${inputName}" ${required ? 'required' : ''} value="">
        <div class="helios-cli-panel list-group shadow-sm d-none" style="position:absolute; z-index:1050; left:0; right:0; max-height:280px; overflow:auto;"></div>
        <div class="form-text helios-cli-hint">Escriba al menos ${minChars} caracteres. No use listas desplegables con todos los clientes.</div>
        <div class="helios-cli-selected small mt-1 text-success d-none"></div>
      </div>
    `;

    const q = root.querySelector('.helios-cli-q');
    const hid = root.querySelector('.helios-cli-id');
    const panel = root.querySelector('.helios-cli-panel');
    const selected = root.querySelector('.helios-cli-selected');
    const clearBtn = root.querySelector('.helios-cli-clear');
    let timer = null;
    let seq = 0;

    function setSelected(item) {
      if (!item) {
        hid.value = '';
        selected.classList.add('d-none');
        selected.innerHTML = '';
        q.value = '';
        return;
      }
      hid.value = item.id;
      q.value = item.label || `${item.nombre_completo} · ${item.identificacion}`;
      selected.classList.remove('d-none');
      selected.innerHTML = `<i class="bi bi-person-check me-1"></i><strong>${item.nombre_completo}</strong>
        <span class="text-muted"> · ${item.tipo_identificacion}: ${item.identificacion}</span>
        ${item.telefono ? ` · ${item.telefono}` : ''}
        ${opts.linkDetalle !== false ? ` · <a href="/catalogos/clientes/${item.id}">Ver ficha</a>` : ''}`;
      if (typeof opts.onSelect === 'function') opts.onSelect(item);
    }

    function hidePanel() { panel.classList.add('d-none'); panel.innerHTML = ''; }

    async function search(term) {
      const my = ++seq;
      panel.classList.remove('d-none');
      panel.innerHTML = `<div class="list-group-item text-muted small">Buscando…</div>`;
      try {
        const url = `${API}?q=${encodeURIComponent(term)}&page=1&page_size=15`;
        const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
        const data = await res.json();
        if (my !== seq) return;
        if (!data.items || !data.items.length) {
          panel.innerHTML = `<div class="list-group-item text-muted small">Sin resultados para “${term}”.</div>`;
          return;
        }
        panel.innerHTML = data.items.map(it => `
          <button type="button" class="list-group-item list-group-item-action py-2" data-id="${it.id}">
            <div class="fw-semibold">${escapeHtml(it.nombre_completo)}</div>
            <div class="small text-muted">${escapeHtml(it.tipo_identificacion)}: ${escapeHtml(it.identificacion)}
              ${it.telefono ? ' · ' + escapeHtml(it.telefono) : ''}
              ${it.correo ? ' · ' + escapeHtml(it.correo) : ''}
            </div>
          </button>
        `).join('') + (data.total > data.items.length
          ? `<div class="list-group-item small text-muted">Mostrando ${data.items.length} de ${data.total}. Refine la búsqueda.</div>`
          : '');
        panel.querySelectorAll('[data-id]').forEach(btn => {
          btn.addEventListener('click', () => {
            const item = data.items.find(x => String(x.id) === btn.getAttribute('data-id'));
            setSelected(item);
            hidePanel();
          });
        });
      } catch (e) {
        panel.innerHTML = `<div class="list-group-item text-danger small">Error de búsqueda.</div>`;
      }
    }

    q.addEventListener('input', () => {
      hid.value = '';
      selected.classList.add('d-none');
      const term = q.value.trim();
      clearTimeout(timer);
      if (term.length < minChars) { hidePanel(); return; }
      timer = setTimeout(() => search(term), 280);
    });

    q.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') hidePanel();
    });

    clearBtn.addEventListener('click', () => { setSelected(null); hidePanel(); q.focus(); });
    document.addEventListener('click', (ev) => { if (!root.contains(ev.target)) hidePanel(); });

    if (opts.preselect && opts.preselect.id) setSelected(opts.preselect);
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  return { mount };
})();
