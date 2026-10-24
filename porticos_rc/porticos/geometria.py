"""Muestreo reproducible, secciones agrupadas y metrado disjunto."""
import copy
import math
import numpy as np
from .normas import GAMMA_RC, G, redondear, sitio, losa_unidir, losa_bidir

GRUPOS=('esquina','exterior','interior')

def grupo(i,j,nx,ny):
    bordes=int(i in (0,nx))+int(j in (0,ny))
    return GRUPOS[2-bordes]

def bloque(b,k):
    return int(bool(b['transicion']) and k>=b['transicion'])

def seccion_col(b,k,i,j):
    g=grupo(i,j,len(b['lx']),len(b['ly']))
    return b['columnas'][bloque(b,k)][g]

def resistencias_config(c):
    valores=c['fc_kgf_cm2']
    valores=valores if isinstance(valores,list) else [valores]
    if not valores or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in valores):
        raise ValueError('fc_kgf_cm2 debe ser un número positivo o una lista no vacía de números positivos')
    return [float(v) for v in valores]

def validar_config(c):
    if not 2<=c['pisos_min']<=c['pisos_max']<=5: raise ValueError('Pisos permitidos: 2 a 5')
    if not 2<=c['vanos_min']<=c['vanos_max']<=5: raise ValueError('Vanos permitidos: 2 a 5')
    if not 300<=c['luz_min_cm']<=c['luz_max_cm']<=600: raise ValueError('Luces: 300 a 600 cm')
    if not 270<=c['altura_min_cm']<=c['altura_max_cm']<=330: raise ValueError('Alturas: 270 a 330 cm')
    if c['cantidad']<1 or c['variantes_por_familia'] not in (1,2,3,4): raise ValueError('Cantidad/variantes inválidas')
    if not 0<=c['fraccion_maciza_max']<=0.5: raise ValueError('Fracción maciza inválida')
    resistencias=resistencias_config(c)
    if c['fy_kgf_cm2']<=0: raise ValueError('fy debe ser positivo')
    if any(fc*.0980665<21 for fc in resistencias) and not c.get('permitir_fc_inferior_21MPa_estudio',False):
        raise ValueError('fc inferior a 21 MPa: habilite explícitamente permitir_fc_inferior_21MPa_estudio para investigación')
    if any(u not in (1,1.3) for u in c['U']): raise ValueError('U implementado: 1 o 1.3')
    for z in c['Z']:
        for s in c['suelos']: sitio(z,s)
    for key in ('acabados_kgf_cm2','tabiqueria_fija_kgf_cm2'):
        if not c[key] or min(c[key])<0: raise ValueError('Cargas negativas/vacías')

def generar_familia(c, familia):
    seed=c['semilla']+familia*104729
    r=np.random.default_rng(seed)
    n=c['pisos_min']+(familia-1)%(c['pisos_max']-c['pisos_min']+1)
    def luces():
        count=int(r.integers(c['vanos_min'],c['vanos_max']+1))
        ref=float(r.integers(c['luz_min_cm']//10,c['luz_max_cm']//10+1)*10)
        if r.random()<0.5: return [ref]*count
        return np.clip(np.round(ref*r.uniform(.8,1.2,count)/10)*10,c['luz_min_cm'],c['luz_max_cm']).tolist()
    for _ in range(100):
        lx,ly=luces(),luces()
        if max(sum(lx),sum(ly))/min(sum(lx),sum(ly))<=2.5: break
    else: raise ValueError('No se obtuvo proporción de planta admisible')
    ht=int(r.integers(c['altura_min_cm']//10,c['altura_max_cm']//10+1)*10)
    h1=int(r.integers(ht//10,int(min(1.2*ht,360))//10+1)*10)
    u=float(r.choice(c['U'])); z=float(r.choice(c['Z'])); soil=str(r.choice(c['suelos']))
    s,tp,tl=sitio(z,soil)
    # C01: vivienda uniforme; C02: oficina uniforme sin corredores especiales.
    # B01: museo / área homogénea de asamblea; B02: comercio homogéneo.
    code=str(r.choice(['C01','C02'] if u==1 else ['B01','B02']))
    q={'C01':.020,'C02':.025,'B01':.040,'B02':.050}[code]
    trans=int(math.ceil(n/2)) if n>=4 and r.random()<.5 else 0
    nblocks=2 if trans else 1
    b={'familia':familia,'semilla':seed,'variante':0,'n':n,'lx':lx,'ly':ly,
       'alturas':[h1]+[ht]*(n-1),'fc':float(np.random.default_rng(np.random.SeedSequence([c['semilla'],familia,210280])).choice(resistencias_config(c))),'fy':c['fy_kgf_cm2'],
       'u':u,'z':z,'suelo':soil,'s':s,'tp':tp,'tl':tl,'codigo_cargas':code,
       'qv':q,'qv_techo':.010,'acabados':float(r.choice(c['acabados_kgf_cm2'])),
       'tabiques':float(r.choice(c['tabiqueria_fija_kgf_cm2'])),
       'transicion':trans,'columnas':[],'vigas':[], 'ratio_col':float(r.choice([1,1.25]))}
    for block in range(nblocks):
        b['columnas'].append({g:[30.,30.] for g in GRUPOS})
        b['vigas'].append({d:[max(25.,redondear(.4*max(50,max(l)/10))),max(50.,redondear(max(l)/10))]
                           for d,l in [('X',lx),('Y',ly)]})
    solid=bool(r.random()<.35)
    types=np.full((len(lx),len(ly)),1 if solid else 0,dtype=int)
    if not solid:
        target=r.uniform(0,c['fraccion_maciza_max'])*sum(lx)*sum(ly)
        used=0
        for idx in r.permutation(types.size):
            i,j=np.unravel_index(idx,types.shape)
            a=lx[i]*ly[j]
            if used+a<=target: types[i,j]=1; used+=a
    b['paños']=types.tolist()  # patrón repetido en altura, sin huecos
    b['t_maciza']=15.; b['t_aligerada']=20.
    return b

def alternativa(base,v):
    b=copy.deepcopy(base); b['variante']=v
    if v in (1,3):
        for dic in b['columnas']:
            for g in GRUPOS: dic[g]=[x+5 for x in dic[g]]
    if v in (2,3):
        for dic in b['vigas']:
            for d in ('X','Y'):
                dic[d][1]+=5
                dic[d][0]=max(dic[d][0],redondear(.4*dic[d][1]))
    return b

def ajustar_losas(b):
    nx,ny=len(b['lx']),len(b['ly'])
    tm,ta=15.,20.
    for _ in range(40):
        required_m=15.; required_a=20.
        for v in b['vigas']:
            for i,lx in enumerate(b['lx']):
                for j,ly in enumerate(b['ly']):
                    # luz libre de losa: entre caras de las vigas paralelas al borde
                    ax=lx-v['Y'][0]; ay=ly-v['X'][0]
                    spanx=ax<=ay
                    cont=int(i>0)+int(i<nx-1) if spanx else int(j>0)+int(j<ny-1)
                    if b['paños'][i][j]==0:
                        required_a=max(required_a,losa_unidir(min(ax,ay),cont,b['fy'],True))
                    elif max(ax,ay)/min(ax,ay)>2:
                        required_m=max(required_m,losa_unidir(min(ax,ay),cont,b['fy'],False))
                    else:
                        req,_=losa_bidir(ax,ay,tm,v['X'],v['Y'],i in (0,nx-1) or j in (0,ny-1),b['fy'])
                        required_m=max(required_m,req)
        newm=redondear(required_m,1)
        newa=next((t for t in (20.,25.,30.) if t+1e-8>=required_a),None)
        if newa is None: raise ValueError('Aligerado requiere >30cm: fuera del catálogo de peso E.020')
        if newm<=tm and newa<=ta: break
        tm=max(tm,newm); ta=max(ta,newa)
    else: raise ValueError('Espesor de losa no convergente')
    b['t_maciza']=tm; b['t_aligerada']=ta

def rectangulos_losa(b,k,i,j):
    """Área neta: excluye vigas y porciones de columnas que invaden el paño."""
    xs=np.r_[0,np.cumsum(b['lx'])]; ys=np.r_[0,np.cumsum(b['ly'])]
    v=b['vigas'][bloque(b,k)]
    a,c=xs[i]+v['Y'][0]/2,xs[i+1]-v['Y'][0]/2
    d,f=ys[j]+v['X'][0]/2,ys[j+1]-v['X'][0]/2
    cutters=[]
    for ii,jj in [(i,j),(i+1,j),(i,j+1),(i+1,j+1)]:
        bx,by=seccion_col(b,k,ii,jj)
        cutters.append((xs[ii]-bx/2,xs[ii]+bx/2,ys[jj]-by/2,ys[jj]+by/2))
    xx=sorted(set([a,c]+[q for r in cutters for q in r[:2] if a<q<c]))
    yy=sorted(set([d,f]+[q for r in cutters for q in r[2:] if d<q<f]))
    for x0,x1 in zip(xx[:-1],xx[1:]):
        for y0,y1 in zip(yy[:-1],yy[1:]):
            x,y=(x0+x1)/2,(y0+y1)/2
            if not any(r[0]<x<r[1] and r[2]<y<r[3] for r in cutters): yield (x0,x1,y0,y1)

def metrar(b):
    """Fuerzas gravitacionales + momentos de masa por nivel, sin duplicación.
    Las cargas superficiales se transfieren a las vigas. La forma distribuida
    se aproxima como uniforme equivalente en cada viga (resultante exacta).
    La masa superficial se integra geométricamente, independientemente de
    esa simplificación gravitacional.
    """
    nx,ny=len(b['lx']),len(b['ly']); n=b['n']
    xs=np.r_[0,np.cumsum(b['lx'])]; ys=np.r_[0,np.cumsum(b['ly'])]
    beamloads={}; pointloads={}; moments=np.zeros((n,4)); dead=np.zeros(n); live=np.zeros(n)
    service=np.zeros(n); solid_area=0.; total_area=0.
    def mass(k,w,x,y,jgeom=0):
        if k<0: return
        moments[k]+=[w,w*x,w*y,w*(x*x+y*y+jgeom)]
    for k in range(n):
        v=b['vigas'][bloque(b,k)]
        # Columnas de entrepiso: peso dividido en extremos, mitad inferior
        # del primer piso gravita sobre base y no participa como masa libre.
        for i,x in enumerate(xs):
            for j,y in enumerate(ys):
                bx,by=seccion_col(b,k,i,j)
                w=bx*by*b['alturas'][k]*GAMMA_RC
                for lev in (k-1,k):
                    pointloads[(lev,i,j)]=pointloads.get((lev,i,j),0)+w/2
                    mass(lev,w/2,x,y,(bx*bx+by*by)/12)
                    if lev>=0: dead[lev]+=w/2; service[lev]+=w/2
        for d in ('X','Y'):
            bx,h=v[d]
            for i in range(nx if d=='X' else nx+1):
                for j in range(ny+1 if d=='X' else ny):
                    ii,jj=(i+1,j) if d=='X' else (i,j+1)
                    dim=0 if d=='X' else 1
                    le=(b['lx'][i] if d=='X' else b['ly'][j])
                    clear=le-(seccion_col(b,k,i,j)[dim]+seccion_col(b,k,ii,jj)[dim])/2
                    if clear<=0 or clear<4*h: raise ValueError('Luz libre de viga <4h (E060 21.5.1.2)')
                    w=bx*h*clear*GAMMA_RC
                    beamloads[(k,d,i,j)]=w
                    x=(xs[i]+xs[ii])/2; y=(ys[j]+ys[jj])/2
                    shift=(seccion_col(b,k,i,j)[dim]-seccion_col(b,k,ii,jj)[dim])/4
                    if d=='X': x+=shift
                    else: y+=shift
                    mass(k,w,x,y,(clear*clear+bx*bx)/12)
                    dead[k]+=w; service[k]+=w
        alpha=.25 if k==n-1 or b['u']==1 else .50
        qv=b['qv_techo'] if k==n-1 else b['qv']
        for i in range(nx):
            for j in range(ny):
                mac=b['paños'][i][j]==1
                pp=GAMMA_RC*b['t_maciza'] if mac else {20.:.030,25.:.035,30.:.042}[b['t_aligerada']]
                qd=pp+b['acabados']+(0 if k==n-1 else b['tabiques'])
                area=0
                for x0,x1,y0,y1 in rectangulos_losa(b,k,i,j):
                    a=(x1-x0)*(y1-y0); area+=a
                    mass(k,a*(qd+alpha*qv),(x0+x1)/2,(y0+y1)/2,((x1-x0)**2+(y1-y0)**2)/12)
                total_area+=area
                if mac: solid_area+=area
                dead[k]+=area*qd; live[k]+=area*qv; service[k]+=area*(qd+qv)
                ax=b['lx'][i]-v['Y'][0]; ay=b['ly'][j]-v['X'][0]
                # Fracción hacia vigas paralelas a Y (luz resistente X).
                if mac and max(ax,ay)/min(ax,ay)<=2:
                    fraction_y=1-.5*ax/ay if ax<=ay else .5*ay/ax
                else: fraction_y=float(ax<=ay)
                total=area*(qd+qv)
                for key,frac in [((k,'Y',i,j),fraction_y/2),((k,'Y',i+1,j),fraction_y/2),
                                 ((k,'X',i,j),(1-fraction_y)/2),((k,'X',i,j+1),(1-fraction_y)/2)]:
                    beamloads[key]+=total*frac
    weights=moments[:,0]
    cm=moments[:,1:3]/weights[:,None]
    inertia=moments[:,3]-weights*np.sum(cm*cm,axis=1)
    if np.any(inertia<=0): raise ValueError('Inercia de masa no positiva')
    applied=sum(beamloads.values())+sum(pointloads.values())
    return {'beamloads':beamloads,'pointloads':pointloads,'peso_muerto':dead,'peso_vivo':live,
            'peso_servicio':service,'pesos':weights,'cm':cm,'inercia_peso':inertia,
            'peso_total_gravitacional':applied,'fraccion_maciza':solid_area/total_area}

def dimensionar(b,c,axiales=None):
    """Crece hasta cubrir carga tributaria o axiales del modelo gravitacional."""
    before=copy.deepcopy(b['columnas'])
    nx,ny=len(b['lx']),len(b['ly']); m=metrar(b)
    ax=[b['lx'][0]/2]+[(b['lx'][i-1]+b['lx'][i])/2 for i in range(1,nx)]+[b['lx'][-1]/2]
    ay=[b['ly'][0]/2]+[(b['ly'][j-1]+b['ly'][j])/2 for j in range(1,ny)]+[b['ly'][-1]/2]
    maxreq=[{g:0 for g in GRUPOS} for _ in b['columnas']]
    for k in range(b['n']):
        for i in range(nx+1):
            for j in range(ny+1):
                p=(sum(m['peso_servicio'][k:])*ax[i]*ay[j]/(sum(b['lx'])*sum(b['ly'])))
                if axiales is not None: p=max(p,axiales[(k,i,j)])
                g=grupo(i,j,nx,ny); bl=bloque(b,k)
                maxreq[bl][g]=max(maxreq[bl][g],p/(.35*b['fc']))
    for bl,groups in enumerate(b['columnas']):
        for g in GRUPOS:
            ratio=b['ratio_col'] if sum(b['lx'])!=sum(b['ly']) else 1.
            # Restricción del estudio: ancho de viga dentro del núcleo de
            # columna; también evita solape del metrado en los nudos.
            short=max(25.,max(sec[0] for sec in b['vigas'][bl].values()),redondear(math.sqrt(maxreq[bl][g]/ratio)))
            long=max(short,redondear(short*ratio))
            target=[long,short] if sum(b['lx'])<sum(b['ly']) else [short,long]
            groups[g]=[max(x,y) for x,y in zip(groups[g],target)]
            if max(groups[g])>c['dimension_columna_max_cm']: raise ValueError('Columna excede límite del estudio')
    if len(b['columnas'])==2:
        for g in GRUPOS: b['columnas'][0][g]=[max(a,z) for a,z in zip(b['columnas'][0][g],b['columnas'][1][g])]
    b['area_requerida']=maxreq
    return before!=b['columnas']
