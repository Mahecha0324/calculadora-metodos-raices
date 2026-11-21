/* Lógica de la página: formulario, llamadas a la API, tabla, gráficas, procedimiento y exportación. */
'use strict';

const $ = (id) => document.getElementById(id);

const EJEMPLOS = [
  { nombre: 'x³ − x − 1 (polinomio cúbico)', funcion: 'x^3 - x - 1', a: '0', b: '2', x0: '1.5' },
  { nombre: 'cos(x) − x', funcion: 'cos(x) - x', a: '0', b: '1', x0: '1' },
  { nombre: 'e^(−x) − x', funcion: 'exp(-x) - x', a: '0', b: '1', x0: '0' },
  { nombre: 'x² − 2 (calcula √2)', funcion: 'x^2 - 2', a: '1', b: '2', x0: '1' },
  { nombre: 'ln(x) + x − 2', funcion: 'ln(x) + x - 2', a: '1', b: '2', x0: '1' },
  { nombre: 'x·sen(x) − 1', funcion: 'x*sin(x) - 1', a: '0', b: '2', x0: '1' },
  { nombre: 'x³ − 2x + 2 (Newton entra en ciclo con x₀ = 0)', funcion: 'x^3 - 2*x + 2', a: '-2', b: '-1', x0: '0' },
  { nombre: 'x² − 1 con x₀ = 0 (derivada cero)', funcion: 'x^2 - 1', a: '0', b: '3', x0: '0' },
];

const estado = { resultado: null, datos: null, pestana: 'tabla' };

/* ---------------------------------------------------------------- utilidades */

function fmt(v, d) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'string') return v;
  if (v === 0) return (0).toFixed(d);
  if (Math.abs(v) < Math.pow(10, -d) || Math.abs(v) >= 1e10) return v.toExponential(Math.max(d - 2, 2));
  return v.toFixed(d);
}

/** Dibuja LaTeX con KaTeX; si KaTeX no cargó (sin internet) muestra el texto plano. */
function tex(el, latex, textoPlano, bloque = false) {
  if (latex && window.katex) {
    try {
      window.katex.render(latex, el, { throwOnError: false, displayMode: bloque });
      return;
    } catch (e) { /* se usa el texto plano */ }
  }
  el.textContent = textoPlano || latex || '';
  if (latex) el.classList.add('texto-plano');
}

function crear(tag, clase, texto) {
  const el = document.createElement(tag);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

function colorVar(nombre) {
  return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
}

function metodoSeleccionado() {
  return document.querySelector('input[name="metodo"]:checked').value;
}

/* ---------------------------------------------------------------- formulario */

function leerFormulario() {
  const metodo = metodoSeleccionado();
  const datos = {
    metodo,
    funcion: $('funcion').value.trim(),
    tolerancia: $('tolerancia').value.trim(),
    max_iter: $('max_iter').value.trim(),
    criterio: $('criterio').value,
    decimales: $('decimales').value.trim(),
  };
  if (metodo === 'falsa_posicion') {
    datos.a = $('a').value.trim();
    datos.b = $('b').value.trim();
  } else {
    datos.x0 = $('x0').value.trim();
  }
  return datos;
}

/** Validación rápida en el navegador; el servidor vuelve a validar todo. */
function validarCliente(d) {
  const errores = {};
  const nombres = { funcion: 'la función f(x)', a: 'el límite inferior (a)', b: 'el límite superior (b)',
    x0: 'el valor inicial (x₀)', tolerancia: 'la tolerancia', max_iter: 'el máximo de iteraciones' };
  for (const campo of Object.keys(nombres)) {
    if (campo in d && d[campo] === '') errores[campo] = `Ingrese ${nombres[campo]}.`;
  }
  if (d.max_iter && !/^\d+$/.test(d.max_iter)) errores.max_iter = 'Debe ser un número entero positivo.';
  const tol = Number(d.tolerancia.replace(',', '.'));
  if (d.tolerancia && !Number.isNaN(tol) && tol <= 0) errores.tolerancia = 'La tolerancia debe ser mayor que 0.';
  return errores;
}

function limpiarErrores() {
  document.querySelectorAll('.error-campo').forEach((p) => { p.textContent = ''; });
  document.querySelectorAll('input.invalido').forEach((i) => i.classList.remove('invalido'));
  $('error-general').hidden = true;
  $('error-general').textContent = '';
}

function mostrarErrores(errores) {
  limpiarErrores();
  const generales = [];
  for (const [campo, mensaje] of Object.entries(errores)) {
    const p = document.querySelector(`.error-campo[data-error="${campo}"]`);
    const input = $(campo);
    if (p) {
      p.textContent = mensaje;
      if (input) input.classList.add('invalido');
    } else {
      generales.push(mensaje);
      if (campo === 'intervalo') { $('a').classList.add('invalido'); $('b').classList.add('invalido'); }
    }
  }
  if (generales.length) {
    $('error-general').textContent = generales.join(' ');
    $('error-general').hidden = false;
  }
  const primero = document.querySelector('input.invalido');
  if (primero) primero.focus();
}

function alternarCamposMetodo() {
  const metodo = metodoSeleccionado();
  document.querySelectorAll('[data-metodo]').forEach((el) => {
    el.hidden = el.dataset.metodo !== metodo;
  });
}

function actualizarEtiquetaTolerancia() {
  $('etiqueta-tolerancia').textContent = $('criterio').value === 'relativo' ? 'Tolerancia (ε %):' : 'Tolerancia (ε):';
}

/* ---------------------------------------------------------------- vista previa de f(x) */

let temporizadorVista = null;
let peticionVista = 0;

function programarVistaPrevia() {
  clearTimeout(temporizadorVista);
  temporizadorVista = setTimeout(vistaPrevia, 350);
}

async function vistaPrevia() {
  const contenedor = $('vista-previa');
  const texto = $('funcion').value.trim();
  if (!texto) { contenedor.textContent = ''; return; }
  const id = ++peticionVista;
  try {
    const resp = await fetch('/api/vista-previa', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ funcion: texto }),
    });
    const datos = await resp.json();
    if (id !== peticionVista) return;
    contenedor.textContent = '';
    if (!datos.ok) {
      contenedor.append(crear('span', 'error-campo', datos.error));
      return;
    }
    const f = crear('div');
    const df = crear('div');
    tex(f, `f(x) = ${datos.latex}`, `f(x) = ${datos.texto}`);
    tex(df, `f'(x) = ${datos.derivada_latex}`, `f'(x) = ${datos.derivada}`);
    contenedor.append(f, df);
  } catch (e) {
    contenedor.textContent = '';
  }
}

/* ---------------------------------------------------------------- resolver */

async function resolver(evento) {
  if (evento) evento.preventDefault();
  const datos = leerFormulario();
  const erroresCliente = validarCliente(datos);
  if (Object.keys(erroresCliente).length) { mostrarErrores(erroresCliente); return; }

  const boton = $('btn-resolver');
  boton.disabled = true;
  try {
    const resp = await fetch('/api/resolver', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos),
    });
    const json = await resp.json();
    if (!json.ok) { mostrarErrores(json.errores || { general: json.error || 'Error desconocido.' }); return; }
    limpiarErrores();
    estado.resultado = json.resultado;
    estado.datos = datos;
    renderizar(json.resultado);
  } catch (e) {
    mostrarErrores({ general: 'No se pudo conectar con el servidor. ¿Está ejecutándose app.py?' });
  } finally {
    boton.disabled = false;
  }
}

function renderizar(r) {
  $('estado-vacio').hidden = true;
  $('btn-pdf').disabled = false;
  $('btn-excel').disabled = false;
  renderTabla(r);
  renderGraficas(r);
  renderProcedimiento(r);
  renderResumen(r);
  mostrarPestana(estado.pestana);
}

/* ---------------------------------------------------------------- tabla */

function renderTabla(r) {
  const d = r.decimales;
  $('titulo-tabla').textContent = `Iteraciones (${r.nombre_metodo})`;
  const tabla = $('tabla');
  tabla.textContent = '';
  const thead = crear('thead');
  const filaEnc = crear('tr');
  for (const c of r.columnas) {
    const th = crear('th');
    tex(th, c.latex, c.titulo);
    filaEnc.append(th);
  }
  thead.append(filaEnc);

  const tbody = crear('tbody');
  if (!r.iteraciones.length) {
    const tr = crear('tr');
    const td = crear('td', 'texto', 'No se realizaron iteraciones. ' + r.mensaje);
    td.colSpan = r.columnas.length;
    tr.append(td);
    tbody.append(tr);
  }
  r.iteraciones.forEach((it, i) => {
    const tr = crear('tr');
    if (r.estado === 'convergio' && i === r.iteraciones.length - 1) tr.className = 'final';
    for (const c of r.columnas) {
      const v = it[c.clave];
      const texto = c.clave === 'iteracion' ? String(v) : fmt(v, d);
      tr.append(crear('td', typeof v === 'string' ? 'texto' : '', texto));
    }
    tbody.append(tr);
  });
  tabla.append(thead, tbody);
}

/* ---------------------------------------------------------------- gráficas */

function layoutBase() {
  const texto = colorVar('--texto');
  const borde = colorVar('--borde');
  const eje = { gridcolor: borde, zerolinecolor: colorVar('--tenue'), zerolinewidth: 1.5, linecolor: borde, automargin: true };
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: texto, family: 'Segoe UI, system-ui, sans-serif', size: 12 },
    margin: { l: 55, r: 15, t: 30, b: 45 },
    xaxis: { ...eje },
    yaxis: { ...eje },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.01, x: 0, bgcolor: 'rgba(0,0,0,0)' },
    hovermode: 'closest',
  };
}

const CONFIG_PLOTLY = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };

function renderGraficas(r) {
  const g = r.grafica;
  const d = r.decimales;
  const trazas = [];

  // Rectas secantes (Falsa Posición) o tangentes (Newton): un solo trazo con cortes (null)
  if (g.segmentos.length) {
    const xs = [], ys = [];
    for (const s of g.segmentos) { xs.push(s.x0, s.x1, null); ys.push(s.y0, s.y1, null); }
    trazas.push({
      x: xs, y: ys, mode: 'lines', name: g.nombre_segmentos, hoverinfo: 'skip',
      line: { color: colorVar('--tenue'), width: 1, dash: 'dash' }, opacity: 0.8,
    });
  }
  trazas.push({
    x: g.x, y: g.y, mode: 'lines', name: `f(x) = ${r.funcion}`,
    line: { color: colorVar('--curva'), width: 2.5 },
    hovertemplate: 'x = %{x:.4f}<br>f(x) = %{y:.4f}<extra></extra>',
  });
  if (g.puntos.length) {
    trazas.push({
      x: g.puntos.map((p) => p.x), y: g.puntos.map((p) => p.y), customdata: g.puntos.map((p) => p.n),
      mode: 'markers', name: 'Aproximaciones',
      marker: { color: colorVar('--punto'), size: 8, line: { color: '#ffffff', width: 1 } },
      hovertemplate: `Aproximación %{customdata}<br>x = %{x:.${d}f}<br>f(x) = %{y:.${d}f}<extra></extra>`,
    });
  }
  if (g.raiz) {
    trazas.push({
      x: [g.raiz.x], y: [g.raiz.y], mode: 'markers', name: `Raíz ≈ ${fmt(g.raiz.x, d)}`,
      marker: { color: colorVar('--raiz'), size: 13, symbol: 'circle', line: { color: '#ffffff', width: 2 } },
      hovertemplate: `Raíz aproximada<br>x = %{x:.${d}f}<br>f(x) = %{y:.2e}<extra></extra>`,
    });
  }

  const layout = layoutBase();
  layout.xaxis.range = g.rango_x;
  layout.xaxis.title = { text: 'x' };
  layout.yaxis.range = g.rango_y;
  layout.yaxis.title = { text: 'f(x)' };
  if (g.intervalo) {
    layout.shapes = [{
      type: 'rect', xref: 'x', yref: 'paper', x0: g.intervalo[0], x1: g.intervalo[1], y0: 0, y1: 1,
      fillcolor: colorVar('--curva'), opacity: 0.07, line: { width: 0 }, layer: 'below',
    }];
  }
  Plotly.react('grafica-funcion', trazas, layout,
    { ...CONFIG_PLOTLY, toImageButtonOptions: { filename: `grafica_${r.metodo}`, scale: 2 } });

  // Convergencia del error (según el criterio elegido)
  const relativo = r.parametros.criterio === 'relativo';
  const errores = g.errores.filter((e) => (relativo ? e.er : e.ea) > 0);
  $('sin-error').hidden = errores.length >= 2;
  $('grafica-error').hidden = errores.length < 2;
  if (errores.length >= 2) {
    const tol = r.parametros.tolerancia;
    const n = errores.map((e) => e.n);
    const layoutE = layoutBase();
    layoutE.yaxis.type = 'log';
    layoutE.yaxis.title = { text: relativo ? 'Error relativo (%)' : 'Error absoluto' };
    layoutE.yaxis.exponentformat = 'power';
    layoutE.xaxis.title = { text: 'Iteración' };
    layoutE.xaxis.dtick = n.length > 20 ? undefined : 1;
    Plotly.react('grafica-error', [
      {
        x: n, y: errores.map((e) => (relativo ? e.er : e.ea)), mode: 'lines+markers', name: 'Error',
        line: { color: colorVar('--curva'), width: 2 }, marker: { size: 7 },
        hovertemplate: 'Iteración %{x}<br>Error = %{y:.3e}<extra></extra>',
      },
      {
        x: [Math.min(...n), Math.max(...n)], y: [tol, tol], mode: 'lines', name: `Tolerancia ε = ${tol}`,
        line: { color: colorVar('--raiz'), dash: 'dash', width: 1.5 }, hoverinfo: 'skip',
      },
    ], layoutE, { ...CONFIG_PLOTLY, toImageButtonOptions: { filename: `error_${r.metodo}`, scale: 2 } });
  }
}

/* ---------------------------------------------------------------- procedimiento */

function renderProcedimiento(r) {
  const cont = $('procedimiento');
  cont.textContent = '';

  const cab = crear('div', 'controles-pasos');
  cab.append(crear('h3', '', `Procedimiento paso a paso — ${r.nombre_metodo}`));
  cont.append(cab);

  const formula = crear('div', 'formula-general');
  tex(formula, `\\displaystyle ${r.formula.latex}`, r.formula.texto, true);
  cont.append(formula);

  r.pasos.forEach((paso, i) => {
    const caja = crear('div', 'paso');
    if (i === r.pasos.length - 1 && r.estado === 'convergio') caja.classList.add('final');
    caja.append(crear('h4', '', paso.titulo));
    for (const linea of paso.lineas) {
      const div = crear('div', 'linea');
      tex(div, linea.latex ? `\\displaystyle ${linea.latex}` : null, linea.texto);
      caja.append(div);
    }
    cont.append(caja);
  });

  const conclusion = crear('div', 'paso final');
  conclusion.append(crear('h4', '', 'Conclusión'));
  conclusion.append(crear('div', 'linea', r.mensaje));
  cont.append(conclusion);
}

/* ---------------------------------------------------------------- resumen */

function renderResumen(r) {
  const d = r.decimales;
  const relativo = r.parametros.criterio === 'relativo';
  const caja = $('resumen');
  caja.hidden = false;
  caja.className = `tarjeta resumen ${r.estado}`;
  $('r-metodo').textContent = r.nombre_metodo;
  $('r-raiz').textContent = r.raiz === null ? '—' : `x ≈ ${fmt(r.raiz, d)}`;
  $('r-error').textContent = fmt(r.error, d) + (relativo && r.error !== null ? ' %' : '');
  $('r-iter').textContent = r.n_iteraciones;
  $('r-estado').textContent = r.etiqueta_estado;
  $('r-estado').className = `insignia ${r.estado}`;
  $('r-mensaje').textContent = r.mensaje;

  // Pestaña "Resumen" con el detalle completo
  const p = r.parametros;
  const filas = [
    ['Método', r.nombre_metodo + (r.metodo === 'falsa_posicion' ? ' (método cerrado)' : ' (método abierto)')],
    ['Función', { latex: `f(x) = ${r.funcion_latex}`, texto: `f(x) = ${r.funcion}` }],
  ];
  if (r.derivada) filas.push(['Derivada', { latex: `f'(x) = ${r.derivada_latex}`, texto: `f'(x) = ${r.derivada}` }]);
  filas.push(['Fórmula', { latex: r.formula.latex, texto: r.formula.texto }]);
  if (r.metodo === 'falsa_posicion') filas.push(['Intervalo inicial [a, b]', `[${fmt(p.a, d)}, ${fmt(p.b, d)}]`]);
  else filas.push(['Valor inicial x₀', fmt(p.x0, d)]);
  filas.push(
    ['Tolerancia (ε)', `${p.tolerancia}${relativo ? ' %' : ''}`],
    ['Máximo de iteraciones', String(p.max_iter)],
    ['Criterio de parada', r.criterio_texto],
    ['Raíz aproximada', r.raiz === null ? '—' : fmt(r.raiz, d)],
    ['f(raíz)', fmt(r.f_raiz, d)],
    ['Error aproximado', fmt(r.error, d) + (relativo && r.error !== null ? ' %' : '')],
    ['Iteraciones realizadas', String(r.n_iteraciones)],
    ['Estado', r.etiqueta_estado],
    ['Mensaje', r.mensaje],
  );

  const tabla = crear('table', 'tabla-resumen');
  for (const [clave, valor] of filas) {
    const tr = crear('tr');
    tr.append(crear('th', '', clave));
    const td = crear('td');
    if (typeof valor === 'object') tex(td, valor.latex, valor.texto); else td.textContent = valor;
    tr.append(td);
    tabla.append(tr);
  }
  const cont = $('resumen-detallado');
  cont.textContent = '';
  cont.append(crear('h3', '', 'Resumen detallado'), tabla);
}

/* ---------------------------------------------------------------- pestañas */

function mostrarPestana(nombre) {
  estado.pestana = nombre;
  document.querySelectorAll('.pestana').forEach((b) => {
    const activa = b.dataset.tab === nombre;
    b.classList.toggle('activa', activa);
    b.setAttribute('aria-selected', String(activa));
  });
  if (!estado.resultado) return;
  document.querySelectorAll('.panel-tab').forEach((p) => { p.hidden = p.id !== `tab-${nombre}`; });
  if (nombre === 'grafica') {
    requestAnimationFrame(() => {
      Plotly.Plots.resize('grafica-funcion');
      if (!$('grafica-error').hidden) Plotly.Plots.resize('grafica-error');
    });
  }
}

/* ---------------------------------------------------------------- exportar */

async function exportar(formato) {
  if (!estado.datos) return;
  const boton = $(formato === 'pdf' ? 'btn-pdf' : 'btn-excel');
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.textContent = 'Generando…';
  try {
    const resp = await fetch(`/api/exportar/${formato}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(estado.datos),
    });
    if (!resp.ok) throw new Error('No se pudo generar el archivo.');
    const blob = await resp.blob();
    const disp = resp.headers.get('Content-Disposition') || '';
    const nombre = (disp.match(/filename="?([^";]+)"?/) || [])[1] || `reporte.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
    const url = URL.createObjectURL(blob);
    const a = crear('a');
    a.href = url;
    a.download = nombre;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (e) {
    mostrarErrores({ general: e.message });
  } finally {
    boton.disabled = false;
    boton.innerHTML = original;
  }
}

/* ---------------------------------------------------------------- tema */

function alternarTema() {
  const raiz = document.documentElement;
  const oscuroActual = raiz.dataset.theme
    ? raiz.dataset.theme === 'dark'
    : window.matchMedia('(prefers-color-scheme: dark)').matches;
  raiz.dataset.theme = oscuroActual ? 'light' : 'dark';
  try { localStorage.setItem('tema', raiz.dataset.theme); } catch (e) { /* sin almacenamiento */ }
  if (estado.resultado) renderGraficas(estado.resultado);
}

/* ---------------------------------------------------------------- inicio */

function cargarEjemplo() {
  const ej = EJEMPLOS[Number($('ejemplos').value)];
  if (!ej) return;
  $('funcion').value = ej.funcion;
  $('a').value = ej.a;
  $('b').value = ej.b;
  $('x0').value = ej.x0;
  $('ejemplos').value = '';
  limpiarErrores();
  vistaPrevia();
}

function limpiar() {
  $('formulario').reset();
  alternarCamposMetodo();
  actualizarEtiquetaTolerancia();
  limpiarErrores();
  estado.resultado = null;
  estado.datos = null;
  $('estado-vacio').hidden = false;
  document.querySelectorAll('.panel-tab').forEach((p) => { p.hidden = true; });
  $('resumen').hidden = true;
  $('btn-pdf').disabled = true;
  $('btn-excel').disabled = true;
  vistaPrevia();
}

function iniciar() {
  EJEMPLOS.forEach((ej, i) => $('ejemplos').append(new Option(ej.nombre, String(i))));
  $('formulario').addEventListener('submit', resolver);
  $('btn-limpiar').addEventListener('click', limpiar);
  $('ejemplos').addEventListener('change', cargarEjemplo);
  $('funcion').addEventListener('input', programarVistaPrevia);
  $('criterio').addEventListener('change', actualizarEtiquetaTolerancia);
  document.querySelectorAll('input[name="metodo"]').forEach((r) => r.addEventListener('change', () => {
    alternarCamposMetodo();
    limpiarErrores();
  }));
  document.querySelectorAll('.pestana').forEach((b) => b.addEventListener('click', () => mostrarPestana(b.dataset.tab)));
  document.querySelectorAll('input').forEach((i) => i.addEventListener('input', () => i.classList.remove('invalido')));
  $('btn-pdf').addEventListener('click', () => exportar('pdf'));
  $('btn-excel').addEventListener('click', () => exportar('excel'));
  $('btn-tema').addEventListener('click', alternarTema);
  alternarCamposMetodo();
  actualizarEtiquetaTolerancia();
  vistaPrevia();
  // KaTeX se carga en diferido: cuando termine, se vuelven a dibujar las fórmulas
  window.addEventListener('load', () => {
    vistaPrevia();
    if (estado.resultado) renderizar(estado.resultado);
  });
}

iniciar();
