from pathlib import Path
import json
import hashlib
import platform
import importlib.metadata
import time
import numpy as np
from .geometria import validar_config,generar_familia,alternativa,ajustar_losas,dimensionar
from .analisis import analizar,gravedad
from .datos import a_fila,exportar,diccionario

def preparar(b,c):
    if any(sec[1]>c['peralte_viga_max_cm'] for v in b['vigas'] for sec in v.values()):
        raise ValueError('Peralte de viga excede límite del estudio')
    for it in range(c['max_iteraciones_predim']):
        old=(b['t_maciza'],b['t_aligerada'])
        ajustar_losas(b)
        changed=dimensionar(b,c)
        ax,error=gravedad(b)
        if error>c['tolerancia_equilibrio']: raise RuntimeError('Desequilibrio de gravedad')
        changed=dimensionar(b,c,ax) or changed
        if not changed and old==(b['t_maciza'],b['t_aligerada']):
            b['iteraciones']=it+1
            return b
    raise ValueError('Secciones no convergentes en iteraciones permitidas')

def guardar_json(path,obj):
    temp=path.with_suffix('.tmp'); temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def ejecutar(c,output,reanudar=False):
    validar_config(c); folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    checkpoint=folder/'estado.json'; excel=folder/'estructuras.xlsx'; log=folder/'registro.jsonl'
    signature={k:v for k,v in c.items() if k not in ('cantidad','max_intentos','guardar_cada','salida')}
    signature['codigo_sha256']=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
    digest=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    rows=[];familia=1;attempts=0;next_variant=0
    if checkpoint.exists():
        if not reanudar: raise ValueError('La carpeta ya contiene una ejecución. Use --reanudar o elija --salida distinta.')
        state=json.loads(checkpoint.read_text(encoding='utf-8'))
        if state['firma']!=digest: raise ValueError('Configuración o código diferente: no es seguro reanudar')
        rows=state['filas'];familia=state['siguiente_familia'];attempts=state['intentos']
        next_variant=state.get('siguiente_variante',0)
        if len(rows)>c['cantidad']: raise ValueError('No se reduce una ejecución existente al reanudar')
    start=time.monotonic()
    versions={p:importlib.metadata.version(p) for p in ('numpy','openseespy','openpyxl','plotly')}
    guardar_json(folder/'configuracion_ejecutada.json',{'config':c,'versiones':versions,'python':platform.python_version(),'firma':digest})
    last_export=len(rows)
    def save(force=False):
        nonlocal last_export
        guardar_json(checkpoint,{'firma':digest,'siguiente_familia':familia,'siguiente_variante':next_variant,'intentos':attempts,'filas':rows})
        if force or len(rows)-last_export>=max(1,c['guardar_cada']):
            exportar(rows,excel)
            diccionario(rows,folder/'diccionario_columnas.json')
            last_export=len(rows)
    with log.open('a',encoding='utf-8') as journal:
        def event(obj): journal.write(json.dumps(obj,ensure_ascii=False)+'\n');journal.flush()
        while len(rows)<c['cantidad'] and attempts<c['max_intentos']:
            f=familia;familia+=1;start_variant=next_variant;next_variant=0
            try: base=preparar(generar_familia(c,f),c)
            except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:
                attempts+=1;event({'familia':f,'estado':'predimensionamiento_descartado','motivo':str(exc)})
                if attempts%25==0: print(f'Intentos {attempts}; exportables {len(rows)}',flush=True)
                if attempts%25==0: save()
                continue
            for variant in range(start_variant,c['variantes_por_familia']):
                if len(rows)>=c['cantidad'] or attempts>=c['max_intentos']:
                    familia=f;next_variant=variant
                    break
                attempts+=1
                try:
                    b=base if variant==0 else preparar(alternativa(base,variant),c)
                    a=analizar(b)
                    if not a['regularidad_evaluable']:
                        event({'familia':f,'alternativa':variant,'estado':'irregularidad_detectada','modelo':b,'piso_blando':a['piso_blando'],'torsion':a['torsion'].tolist(),'masa':bool(a['irregular_masa']),
                               'Tx_s':a['Tx'],'Ty_s':a['Ty'],'deriva_max_X':float(a['deriva_normativa'][:,0,:4].max()),'deriva_max_Y':float(a['deriva_normativa'][:,1,:4].max())})
                        continue
                    row=a_fila(b,a,len(rows)+1);rows.append(row)
                    event({'ID':row['ID_estructura'],'familia':f,'alternativa':variant,'estado':'exportado','cumple_deriva':row['cumple_deriva_X'] and row['cumple_deriva_Y']})
                    print(f"{len(rows)}/{c['cantidad']} · familia {f} · alternativa {variant} · Tx={a['Tx']:.3f}s Ty={a['Ty']:.3f}s",flush=True)
                except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:
                    event({'familia':f,'alternativa':variant,'estado':'fallo_modelo','motivo':str(exc)})
            save() # punto de recuperación al completar cada familia
    save(True)
    summary={'solicitadas':c['cantidad'],'exportadas':len(rows),'familias':len(set(r['ID_familia'] for r in rows)),
             'intentos':attempts,'segundos_esta_ejecucion':round(time.monotonic()-start,2),'archivo':str(excel),
             'regularidad_por_resistencia':'NO_VERIFICADA','segundo_orden':'NO_INCLUIDO_MODELO_LINEAL',
             'cumplen_deriva_ambas':sum(r['cumple_deriva_X'] and r['cumple_deriva_Y'] for r in rows)}
    guardar_json(folder/'resumen_ejecucion.json',summary)
    return summary
