import argparse
import json
import time
import tempfile
from pathlib import Path

def actualizar_entradas_vanos(carpeta):
    archivo=Path(carpeta)/'variables_ml.json'
    if archivo.exists():
        datos=json.loads(archivo.read_text(encoding='utf-8'))
        vanos=[f'luz_{e}_{i}_cm' for e in ('X','Y') for i in range(1,6)]
        datos['entradas_iniciales']=list(dict.fromkeys(datos['entradas_iniciales']+vanos))
        archivo.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding='utf-8')

def ejecutar_con_recuperacion(ejecutar, config, out, reanudar):
    """Reanuda desde el checkpoint ante bloqueos transitorios de estado.json.

    No ignora permisos persistentes ni modifica la firma del modelo.
    """
    for intento in range(7):
        try:
            return ejecutar(config, out, reanudar)
        except PermissionError as exc:
            nombres = {Path(str(x)).name for x in (exc.filename, getattr(exc, 'filename2', None)) if x}
            if not nombres.intersection({'estado.tmp', 'estado.json'}) or intento == 6:
                raise
            pausa = min(0.5 * 2**intento, 4.0)
            print(f'Archivo de recuperación ocupado. Reintento {intento+1}/6 en {pausa:g} s...', flush=True)
            time.sleep(pausa)
            reanudar = (Path(out) / 'estado.json').exists()


def main():
    parser=argparse.ArgumentParser(description='Generador de pórticos RC: kgf, cm, s. Sin entrenamiento ML.')
    subs=parser.add_subparsers(dest='accion',required=True)
    p=subs.add_parser('generar',help='Generar base Excel de una sola hoja')
    p.add_argument('--config',default=str(Path(__file__).with_name('config.json')))
    p.add_argument('--cantidad',type=int);p.add_argument('--semilla',type=int);p.add_argument('--salida')
    p.add_argument('--reanudar',action='store_true')
    p.add_argument('--reemplazar',action='store_true',help='Regenerar en la misma carpeta con respaldo automático')
    p=subs.add_parser('ver',help='Gráfico 3D y planta a partir de una fila guardada')
    p.add_argument('--excel',default='resultados/estructuras.xlsx');p.add_argument('--id',type=int)
    p.add_argument('--html');p.add_argument('--abrir',action='store_true')
    p=subs.add_parser('finalizar',help='Publicar una base completa cuyo reemplazo quedó bloqueado')
    p.add_argument('--temporal',required=True);p.add_argument('--salida',required=True)
    args=parser.parse_args()
    if args.accion=='finalizar':
        temporal=Path(args.temporal)
        resumen=json.loads((temporal/'resumen_ejecucion.json').read_text(encoding='utf-8'))
        estado=json.loads((temporal/'estado.json').read_text(encoding='utf-8'))
        if resumen['exportadas']!=resumen['solicitadas'] or len(estado['filas'])!=resumen['exportadas']:
            raise ValueError('La base temporal no está completa.')
        from actualizar import publicar
        nombres=['estado.json','estructuras.xlsx','registro.jsonl','configuracion_ejecutada.json',
                 'resumen_ejecucion.json','diccionario_columnas.json','variables_ml.json']
        respaldo=publicar(temporal,args.salida,nombres)
        print(f'Base publicada en {Path(args.salida).resolve()}. Respaldo: {respaldo.name}')
        return 0
    if args.accion=='generar':
        from porticos.generador import ejecutar
        config=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
        if args.cantidad is not None: config['cantidad']=args.cantidad
        if args.semilla is not None: config['semilla']=args.semilla
        out=args.salida or config['salida']
        if args.reanudar and args.reemplazar: raise ValueError('Elija --reanudar o --reemplazar, no ambos.')
        if args.reemplazar:
            destino=Path(out).resolve(); destino.parent.mkdir(parents=True,exist_ok=True)
            temporal=Path(tempfile.mkdtemp(prefix='preparando_estructuras_',dir=destino.parent))
            summary=ejecutar_con_recuperacion(ejecutar,config,temporal,False)
            if summary['exportadas']!=summary['solicitadas']:
                raise ValueError(f'No se completó la cantidad. La base anterior se conserva. Revise {temporal}')
            actualizar_entradas_vanos(temporal)
            summary['archivo']=str(destino/'estructuras.xlsx')
            (temporal/'resumen_ejecucion.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
            from actualizar import publicar
            nombres=['estado.json','estructuras.xlsx','registro.jsonl','configuracion_ejecutada.json',
                     'resumen_ejecucion.json','diccionario_columnas.json','variables_ml.json']
            respaldo=publicar(temporal,destino,nombres)
            print(f'Base reemplazada. Respaldo: {respaldo}')
            print('Los gráficos HTML anteriores no se actualizan: vuelva a generarlos con ver.')
        else:
            summary=ejecutar_con_recuperacion(ejecutar,config,out,args.reanudar)
            actualizar_entradas_vanos(out)
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        return 0 if summary['exportadas']==summary['solicitadas'] else 2
    from porticos.visualizacion import dibujar
    ident=args.id if args.id is not None else int(input('Número de estructura: '))
    print(dibujar(args.excel,ident,args.html,args.abrir))
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,FileNotFoundError,PermissionError) as exc:
        raise SystemExit(f'ERROR: {exc}')
