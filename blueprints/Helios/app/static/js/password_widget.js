/**
 * Widget de contraseña Helios: show/hide, evaluación en vivo via /api/password/evaluar
 */
window.HeliosPassword = (function () {
  const labels = { debil: 'Débil', media: 'Media', fuerte: 'Fuerte' };
  const colors = { debil: 'bg-danger', media: 'bg-warning', fuerte: 'bg-success' };

  async function evaluar(password) {
    const res = await fetch('/api/password/evaluar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    return res.json();
  }

  function renderChecklist(el, data, pol) {
    if (!el) return;
    const items = [
      [`Al menos ${pol.longitud_minima} caracteres`, data.reglas.longitud_ok],
      ['Mayúsculas según política', data.reglas.mayusculas_ok],
      ['Número', data.reglas.numero_ok],
      ['Carácter especial', data.reglas.especial_ok],
      ['Sin repeticiones excesivas', data.reglas.repetidos_ok],
      ['Espacios válidos', data.reglas.espacios_ok],
    ];
    el.innerHTML = items.map(([txt, ok]) =>
      `<li class="${ok ? 'text-success' : 'text-danger'}">
        <i class="bi ${ok ? 'bi-check-circle' : 'bi-x-circle'} me-1"></i>${txt}
      </li>`
    ).join('');
  }

  function bindLive(inputSel, opts) {
    const input = document.querySelector(inputSel);
    if (!input) return;
    const bar = document.querySelector(opts.bar);
    const nivel = document.querySelector(opts.nivel);
    const crack = document.querySelector(opts.crack);
    const checklist = document.querySelector(opts.checklist);
    const confirm = opts.confirm ? document.querySelector(opts.confirm) : null;
    const match = opts.match ? document.querySelector(opts.match) : null;
    const submit = opts.submit ? document.querySelector(opts.submit) : null;
    const pol = window.HELIOS_PWD_POLITICA || {};
    let timer = null;

    async function refresh() {
      const pwd = input.value || '';
      if (!pwd) {
        if (bar) { bar.style.width = '0%'; bar.className = 'progress-bar bg-danger'; }
        if (nivel) nivel.textContent = '—';
        if (crack) crack.textContent = '';
        if (checklist) checklist.innerHTML = '';
        if (submit) submit.disabled = false;
        return;
      }
      const data = await evaluar(pwd);
      if (bar) {
        bar.style.width = (data.score || 0) + '%';
        bar.className = 'progress-bar ' + (colors[data.nivel] || 'bg-danger');
      }
      if (nivel) nivel.textContent = (labels[data.nivel] || data.nivel) + ` (${data.score}/100 · ${data.entropia_bits} bits)`;
      if (crack) crack.textContent = data.crack_tiempo ? 'Crack estimado: ' + data.crack_tiempo : '';
      renderChecklist(checklist, data, pol);
      let ok = data.valida;
      if (confirm && match) {
        if (confirm.value && confirm.value !== pwd) {
          match.textContent = 'Las contraseñas no coinciden.';
          match.className = 'form-text text-danger';
          ok = false;
        } else if (confirm.value) {
          match.textContent = 'Coinciden.';
          match.className = 'form-text text-success';
        } else {
          match.textContent = '';
        }
      }
      if (submit) submit.disabled = !ok;
    }

    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(refresh, 180);
    };
    input.addEventListener('input', schedule);
    if (confirm) confirm.addEventListener('input', schedule);
  }

  function toggle(sel, btn) {
    const el = document.querySelector(sel);
    if (!el) return;
    el.type = el.type === 'password' ? 'text' : 'password';
    const icon = btn.querySelector('i');
    if (icon) icon.className = el.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
  }

  return { bindLive, toggle, evaluar };
})();
