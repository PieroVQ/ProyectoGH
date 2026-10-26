const r = $('Obtener resultados').first().json;
const ia = ($input.first().json.output) || {};
let fig = null;
try {
  const f = $('Figura en base64').first().json;
  if (f && f.figura_b64) fig = { b64: f.figura_b64, mime: $('Identificar archivos de la consulta').first().json.figura_mime || 'image/png' };
} catch (e) { fig = null; }

function esc(v) {
  return String(v === null || v === undefined ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function val(v) {
  if (v === null || v === undefined || v === '') return '<span class="na">— (no aplica / vacío)</span>';
  if (typeof v === 'object') return esc(JSON.stringify(v));
  return esc(v);
}
function parrafos(t) {
  const s = String(t || '').trim();
  if (!s) return '<p class="na">Sin contenido.</p>';
  return s.split(/\n\s*\n/).map(function (p) { return '<p>' + esc(p.trim()) + '</p>'; }).join('');
}
function tablaKV(obj, unidades, cab1, cab2) {
  const u = unidades || {};
  const keys = obj && typeof obj === 'object' ? Object.keys(obj) : [];
  if (!keys.length) return '<p class="na">No se proporcionaron datos.</p>';
  let h = '<table><thead><tr><th style="width:30%">' + esc(cab1) + '</th><th style="width:50%">' + esc(cab2) + '</th><th style="width:20%">Unidad</th></tr></thead><tbody>';
  keys.forEach(function (k) { h += '<tr><td>' + esc(k) + '</td><td>' + val(obj[k]) + '</td><td>' + esc(u[k] || '') + '</td></tr>'; });
  return h + '</tbody></table>';
}

const preds = Array.isArray(r.predicciones) ? r.predicciones : [];
let tPred = '<table><caption>Tabla 6.1. Predicciones del modelo para la consulta (valores tal como los entrega el programa).</caption><thead><tr><th style="width:8%">N.º</th><th style="width:50%">Respuesta</th><th style="width:27%">Valor predicho</th><th style="width:15%">Unidad</th></tr></thead><tbody>';
preds.forEach(function (p, i) { tPred += '<tr><td>' + (i + 1) + '</td><td>' + esc(p.nombre) + '</td><td class="num">' + val(p.valor) + '</td><td>' + esc(p.unidad || 'adimensional') + '</td></tr>'; });
tPred += '</tbody></table>';
if (preds.length !== 8) tPred += '<p class="aviso">Advertencia: el servicio devolvió ' + preds.length + ' predicciones en lugar de 8.</p>';

const ent = Array.isArray(r.entradas_107) ? r.entradas_107 : [];
let tEnt = '<table class="anexo"><caption>Tabla A.1. Entradas del modelo en el orden requerido (' + ent.length + ' entradas).</caption><thead><tr><th style="width:8%">N.º</th><th style="width:52%">Variable</th><th style="width:25%">Valor</th><th style="width:15%">Unidad</th></tr></thead><tbody>';
ent.forEach(function (e, i) { tEnt += '<tr><td>' + (i + 1) + '</td><td>' + esc(e.nombre) + '</td><td class="num">' + val(e.valor) + '</td><td>' + esc(e.unidad || '') + '</td></tr>'; });
tEnt += '</tbody></table>';

const m = r.modelo || {};
const tModelo = '<table><thead><tr><th>Campo</th><th>Valor</th></tr></thead><tbody>' +
  '<tr><td>Modelo de predicción</td><td>' + val(m.id) + '</td></tr>' +
  '<tr><td>Versión</td><td>' + val(m.version) + '</td></tr>' +
  '<tr><td>Archivo</td><td>' + val(m.archivo) + '</td></tr></tbody></table>';

let tMetricas = '';
if (r.metricas_originales && typeof r.metricas_originales === 'object' && Object.keys(r.metricas_originales).length) {
  tMetricas = '<h3>5.2 Métricas originales del modelo de evaluación</h3><p class="nota">Estas métricas describen el desempeño global del modelo de evaluación sobre los datos originales. No representan el error de esta consulta.</p>' + tablaKV(r.metricas_originales, {}, 'Métrica', 'Valor');
}

const refs = Array.isArray(r.referencias_verificadas) ? r.referencias_verificadas : [];
let tRefs = '<p class="na">No se proporcionaron referencias verificadas.</p>';
if (refs.length) {
  tRefs = '<ol class="refs">' + refs.map(function (x) {
    if (typeof x === 'string') return '<li>' + esc(x) + '</li>';
    return '<li>' + esc(x.texto || x.titulo || JSON.stringify(x)) + (x.url ? ' <span class="url">' + esc(x.url) + '</span>' : '') + '</li>';
  }).join('') + '</ol>';
}

const figHtml = fig
  ? '<figure><img src="data:' + esc(fig.mime) + ';base64,' + fig.b64 + '" alt="Geometría 3D"/><figcaption>Figura 4.1. Vista estática de la geometría 3D generada por el programa (dimensiones en cm).</figcaption></figure>'
  : '<p class="na">No se dispone de una figura estática de la geometría para esta consulta.</p>';

const etiquetaOrigen = r.origen_datos === 'prueba_sintetica' ? '<p class="aviso"><b>PRUEBA TÉCNICA - DATOS SINTÉTICOS. Sin validación científica.</b></p>' : '';
const fecha = new Date().toISOString().slice(0, 10);
const css = '@page{size:A4;margin:22mm 18mm 20mm 18mm}body{font-family:"Times New Roman",Georgia,serif;font-size:11pt;line-height:1.45;color:#111}' +
  'h1{font-size:18pt;text-align:center;margin:0 0 4mm}h2{font-size:13pt;margin:7mm 0 2mm;border-bottom:1px solid #444;page-break-after:avoid}h3{font-size:11.5pt;margin:4mm 0 2mm;page-break-after:avoid}' +
  '.sub{text-align:center;font-size:10pt;color:#333}.etiqueta{text-align:center;font-weight:bold;border:1px solid #333;padding:2mm;margin:4mm 0}' +
  'p{text-align:justify;margin:0 0 2.5mm}table{width:100%;border-collapse:collapse;margin:3mm 0;font-size:9.5pt;page-break-inside:auto}thead{display:table-header-group}tr{page-break-inside:avoid}' +
  'th,td{border:1px solid #777;padding:1.2mm 2mm;text-align:left;vertical-align:top}th{background:#e8e8e8}td.num{text-align:right;font-family:"Courier New",monospace}caption{caption-side:top;font-style:italic;text-align:left;margin-bottom:1mm}' +
  'figure{text-align:center;margin:4mm 0;page-break-inside:avoid}figure img{max-width:100%;max-height:150mm}figcaption{font-style:italic;font-size:9.5pt}.na{color:#555;font-style:italic}.nota,.aviso{font-size:9.5pt;color:#333}.anexo{font-size:8.5pt}.saltar{page-break-before:always}.url{word-break:break-all;font-size:9pt}';

const html = '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>' + esc(ia.titulo || 'Informe de predicciones') + '</title><style>' + css + '</style></head><body>' +
  '<h1>' + esc(ia.titulo || 'Informe de predicciones') + '</h1>' +
  '<div class="sub">Consulta ' + esc(r.consulta_id) + ' · Fecha de emisión ' + esc(fecha) + '</div>' +
  '<div class="etiqueta">Informe de predicciones bajo las hipótesis del proyecto. No constituye un diseño ni una verificación normativa.</div>' +
  etiquetaOrigen + '<h2>1. Identificación de la consulta</h2>' + tablaKV({ consulta_id: r.consulta_id, modelo_prediccion: m.id, version_modelo: m.version, unidades_proyecto: 'cm, kgf, s' }, {}, 'Campo', 'Valor') +
  '<h2>2. Resumen</h2>' + parrafos(ia.resumen) +
  '<h2>3. Descripción de la estructura</h2>' + parrafos(ia.descripcion_estructura) +
  '<h3>3.1 Parámetros confirmados</h3>' + tablaKV(r.parametros_confirmados, r.unidades, 'Parámetro', 'Valor') +
  '<h3>3.2 Supuestos aceptados por el usuario</h3>' + (Array.isArray(r.supuestos_aceptados) && r.supuestos_aceptados.length ? '<ul>' + r.supuestos_aceptados.map(function (s) { return '<li>' + val(s) + '</li>'; }).join('') + '</ul>' : '<p class="na">Ninguno.</p>') +
  '<h3>3.3 Propiedades calculadas por el programa</h3>' + tablaKV(r.propiedades_calculadas, r.unidades_propiedades, 'Propiedad', 'Valor') +
  '<h2>4. Representación de la estructura</h2>' + figHtml + parrafos(ia.representacion_estructura) +
  '<h2>5. Metodología y modelo utilizado</h2>' + parrafos(ia.metodologia) + '<h3>5.1 Identificación del modelo de predicción</h3>' + tModelo + tMetricas +
  '<h2>6. Predicciones</h2>' + tPred +
  '<h2>7. Discusión de los resultados</h2>' + parrafos(ia.discusion) +
  '<h2>8. Alcance y limitaciones</h2>' + parrafos(ia.alcance_limitaciones) +
  '<h2>9. Conclusiones</h2>' + parrafos(ia.conclusiones) +
  '<h2>10. Referencias</h2>' + tRefs +
  '<h2 class="saltar">11. Anexo: entradas del modelo</h2>' + tEnt +
  '</body></html>';

const footer = '<html><head><style>body{font-family:Georgia,serif;font-size:8pt;color:#444;width:100%;text-align:center;margin:0 18mm}</style></head><body>Consulta ' + esc(r.consulta_id) + ' · Página <span class="pageNumber"></span> de <span class="totalPages"></span></body></html>';

return [{
  json: { consulta_id: r.consulta_id, nombre_pdf: 'informe_' + String(r.consulta_id).replace(/[^A-Za-z0-9_-]/g, '_') + '.pdf' },
  binary: {
    index_html: { data: Buffer.from(html, 'utf8').toString('base64'), mimeType: 'text/html', fileName: 'index.html', fileExtension: 'html' },
    footer_html: { data: Buffer.from(footer, 'utf8').toString('base64'), mimeType: 'text/html', fileName: 'footer.html', fileExtension: 'html' },
  },
}];