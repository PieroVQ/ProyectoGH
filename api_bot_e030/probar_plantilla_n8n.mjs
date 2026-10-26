import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url));
const out = process.env.RC_BOT_OUTPUT_DIR || path.resolve(root, '../outputs/pruebas_tecnicas');
const code = await fs.readFile(path.join(root,'plantilla_informe.js'),'utf8');
const result = JSON.parse(await fs.readFile(path.join(out,'resultado_sintetico.json'),'utf8'));
const geometry = await fs.readFile(path.join(out,'geometria.png'));
const syntheticText = 'Prueba técnica con datos sintéticos generados. No se ha realizado una validación científica ni un análisis normativo.';
const narrative = Object.fromEntries(['resumen','descripcion_estructura','representacion_estructura','metodologia','discusion','alcance_limitaciones','conclusiones'].map(k=>[k,syntheticText]));
narrative.titulo='PRUEBA TÉCNICA - DATOS SINTÉTICOS';
const store = {
 'Obtener resultados':result,
 'Figura en base64':{figura_b64:geometry.toString('base64')},
 'Identificar archivos de la consulta':{figura_mime:'image/png'},
};
const $ = name=>({first:()=>({json:store[name]})});
const $input={first:()=>({json:{output:narrative}})};
const output = new Function('$','$input',code)($,$input);
for (const [field,name] of [['index_html','index.html'],['footer_html','footer.html']]) {
 const binary=output[0].binary[field];
 if (binary.fileName!==name) throw new Error('Nombre multipart inesperado');
 await fs.writeFile(path.join(out,name),Buffer.from(binary.data,'base64'));
}
console.log('Plantilla n8n ejecutada: index.html y footer.html; narrativa fija sintética, sin LLM.');
