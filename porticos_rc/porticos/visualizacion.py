"""Geometría guardada: 3D sólido y planta. HTML interactivo sin conexión."""
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .datos import leer_filas,desde_fila
from .geometria import GRUPOS,grupo,bloque,seccion_col,rectangulos_losa

def dibujar(excel,ident,destino=None,abrir=False):
    rows=leer_filas(excel)
    row=next((r for r in rows if r['ID_estructura']==ident),None)
    if row is None: raise ValueError(f'ID {ident} inexistente. Disponibles: '+', '.join(str(r['ID_estructura']) for r in rows[:100]))
    b=desde_fila(row); xs=np.r_[0,np.cumsum(b['lx'])]; ys=np.r_[0,np.cumsum(b['ly'])]; zs=np.r_[0,np.cumsum(b['alturas'])]
    fig=make_subplots(rows=1,cols=2,specs=[[{'type':'scene'},{'type':'xy'}]],column_widths=[.7,.3],horizontal_spacing=.05,subplot_titles=['Modelo 3D · cm','Planta del primer piso · cm'])
    palette={'esquina':'#19486A','exterior':'#307EA5','interior':'#64AFC8','vigaX':'#C97835','vigaY':'#E2AB64','maciza':'#8E96A8','aligerada':'#B8D7BE'}
    meshes={name:dict(x=[],y=[],z=[],i=[],j=[],k=[],text=[]) for name in palette}
    def caja(name,x0,x1,y0,y1,z0,z1,text):
        d=meshes[name]; off=len(d['x'])
        for x,y,z in [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]:
            d['x'].append(x);d['y'].append(y);d['z'].append(z);d['text'].append(text)
        for i,j,k in [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]:
            d['i'].append(off+i);d['j'].append(off+j);d['k'].append(off+k)
    for k in range(b['n']):
        for i,x in enumerate(xs):
            for j,y in enumerate(ys):
                bx,by=seccion_col(b,k,i,j);g=grupo(i,j,len(b['lx']),len(b['ly']))
                caja(g,x-bx/2,x+bx/2,y-by/2,y+by/2,zs[k],zs[k+1],f'Columna {g} · piso {k+1}<br>{bx:g} × {by:g} cm')
        for d in ('X','Y'):
            bw,h=b['vigas'][bloque(b,k)][d]
            for i in range(len(b['lx']) if d=='X' else len(xs)):
                for j in range(len(ys) if d=='X' else len(b['ly'])):
                    if d=='X': x0,x1,y0,y1=xs[i],xs[i+1],ys[j]-bw/2,ys[j]+bw/2
                    else: x0,x1,y0,y1=xs[i]-bw/2,xs[i]+bw/2,ys[j],ys[j+1]
                    caja('viga'+d,x0,x1,y0,y1,zs[k+1]-h,zs[k+1],f'Viga {d} piso {k+1}<br>{bw:g} × {h:g} cm')
        for i in range(len(b['lx'])):
            for j in range(len(b['ly'])):
                solid=b['paños'][i][j]; name='maciza' if solid else 'aligerada';t=b['t_maciza'] if solid else b['t_aligerada']
                for x0,x1,y0,y1 in rectangulos_losa(b,k,i,j):
                    caja(name,x0,x1,y0,y1,zs[k+1]-t,zs[k+1],f'Losa {name} · paño {i+1},{j+1}<br>h={t:g} cm')
    for name,d in meshes.items():
        if d['x']: fig.add_trace(go.Mesh3d(**d,name=name,color=palette[name],opacity=.4 if name in ('maciza','aligerada') else 1,hovertemplate='%{text}<extra></extra>',flatshading=True,showlegend=True),row=1,col=1)
    for i in range(len(b['lx'])):
        for j in range(len(b['ly'])):
            solid=b['paños'][i][j]; x0,x1=xs[i],xs[i+1];y0,y1=ys[j],ys[j+1]
            fig.add_trace(go.Scatter(x=[x0,x1,x1,x0,x0],y=[y0,y0,y1,y1,y0],fill='toself',fillcolor=palette['maciza' if solid else 'aligerada'],line={'color':'white'},mode='lines',showlegend=False,hovertemplate=f'Paño {i+1},{j+1}<br>{b["lx"][i]:g} × {b["ly"][j]:g} cm<extra></extra>'),row=1,col=2)
            if not solid:
                ax=b['lx'][i]-b['vigas'][0]['Y'][0];ay=b['ly'][j]-b['vigas'][0]['X'][0]
                dx,dy=((x1-x0)*.3,0) if ax<=ay else (0,(y1-y0)*.3)
                fig.add_annotation(x=(x0+x1)/2+dx/2,y=(y0+y1)/2+dy/2,ax=(x0+x1)/2-dx/2,ay=(y0+y1)/2-dy/2,axref='x',ayref='y',arrowhead=3,arrowsize=1.3,text='',row=1,col=2)
    for x in xs: fig.add_trace(go.Scatter(x=[x]*len(ys),y=ys,mode='markers',marker={'size':7,'color':'#17365D'},showlegend=False,hoverinfo='skip'),row=1,col=2)
    fig.update_layout(title=f'Estructura {ident} · familia {b["familia"]} · {b["n"]} pisos<br><sup>Tx={row["Tx_s"]:.3f} s · Ty={row["Ty_s"]:.3f} s · deriva X={row["deriva_max_X"]:.4f} · Y={row["deriva_max_Y"]:.4f}</sup>',
      template='plotly_white',height=850,scene={'aspectmode':'data','xaxis_title':'X (cm)','yaxis_title':'Y (cm)','zaxis_title':'Z (cm)'},legend={'orientation':'h','y':-.1},margin={'l':30,'r':30,'t':105,'b':85})
    fig.update_yaxes(scaleanchor='x',scaleratio=1,row=1,col=2);fig.update_xaxes(title_text='X (cm)',row=1,col=2);fig.update_yaxes(title_text='Y (cm)',row=1,col=2)
    path=Path(destino) if destino else Path(excel).with_name(f'estructura_{ident:04d}.html')
    fig.write_html(path,include_plotlyjs=True,auto_open=abrir)
    return path
