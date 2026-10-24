"""Pórtico espacial OpenSees y condensación estática exacta de DOF sin masa.

3 DOF por diafragma (Ux,Uy,Rz). La flexibilidad se obtiene aplicando cargas
unitarias al modelo 3D completo. La eigensolución de ese sistema reducido
conserva el modelo elástico elegido; no es una fórmula empírica de período.
"""
import numpy as np
import openseespy.opensees as ops
from .geometria import bloque,seccion_col,metrar
from .normas import G,R0,LIM_DERIVA,espectro,cortante_estatico,correlacion_cqc,cqc,combinar_direcciones

def torsion_rect(a,b):
    a,b=max(a,b),min(a,b)
    return a*b**3/3*(1-.63*b/a+.052*(b/a)**5)

def construir(b,m):
    ops.wipe(); ops.model('basic','-ndm',3,'-ndf',6)
    n=b['n']; xs=np.r_[0,np.cumsum(b['lx'])]; ys=np.r_[0,np.cumsum(b['ly'])]; zz=np.r_[0,np.cumsum(b['alturas'])]
    nodes={}; masters=[]; cols={}; beams={}; tag=0; ele=0
    for k in range(n+1):
        for i,x in enumerate(xs):
            for j,y in enumerate(ys):
                tag+=1; nodes[k,i,j]=tag; ops.node(tag,float(x),float(y),float(zz[k]))
                if k==0: ops.fix(tag,1,1,1,1,1,1)
    for k in range(n):
        tag+=1; masters.append(tag)
        ops.node(tag,float(m['cm'][k,0]),float(m['cm'][k,1]),float(zz[k+1]))
        ops.fix(tag,0,0,1,1,1,0)
        slaves=[nodes[k+1,i,j] for i in range(len(xs)) for j in range(len(ys))]
        ops.rigidDiaphragm(3,tag,*slaves)
        ops.mass(tag,m['pesos'][k]/G,m['pesos'][k]/G,0,0,0,m['inercia_peso'][k]/G)
    # E060 8.5: Ec=4700 sqrt(fc_MPa) MPa, convertido exactamente.
    E=4700*np.sqrt(b['fc']*.0980665)/.0980665; shear=E/(2*1.2)
    ops.geomTransf('Linear',1,1,0,0) # columna: xlocal=Z, zlocal=X
    ops.geomTransf('Linear',2,0,0,1) # viga: zlocal=Z
    for k in range(n):
        for i in range(len(xs)):
            for j in range(len(ys)):
                bx,by=seccion_col(b,k,i,j); ele+=1; cols[k,i,j]=ele
                ops.element('elasticBeamColumn',ele,nodes[k,i,j],nodes[k+1,i,j],bx*by,float(E),float(shear),torsion_rect(bx,by),by*bx**3/12,bx*by**3/12,1)
        for d in ('X','Y'):
            bw,h=b['vigas'][bloque(b,k)][d]
            for i in range(len(xs)-1 if d=='X' else len(xs)):
                for j in range(len(ys) if d=='X' else len(ys)-1):
                    ii,jj=(i+1,j) if d=='X' else (i,j+1)
                    ele+=1; beams[k,d,i,j]=ele
                    ops.element('elasticBeamColumn',ele,nodes[k+1,i,j],nodes[k+1,ii,jj],bw*h,float(E),float(shear),torsion_rect(bw,h),bw*h**3/12,h*bw**3/12,2)
    ops.timeSeries('Constant',1); ops.pattern('Plain',1,1)
    for (k,i,j),w in m['pointloads'].items(): ops.load(nodes[k+1,i,j],0,0,-float(w),0,0,0)
    for (k,d,i,j),w in m['beamloads'].items():
        length=b['lx'][i] if d=='X' else b['ly'][j]
        ops.eleLoad('-ele',beams[k,d,i,j],'-type','-beamUniform',0,-float(w/length))
    ops.constraints('Transformation'); ops.numberer('RCM'); ops.system('UmfPack')
    ops.test('NormDispIncr',1e-10,20); ops.algorithm('Linear')
    ops.integrator('LoadControl',1); ops.analysis('Static')
    if ops.analyze(1)!=0: raise RuntimeError('Fallo análisis gravitacional')
    ops.reactions()
    reaction=sum(ops.nodeReaction(nodes[0,i,j],3) for i in range(len(xs)) for j in range(len(ys)))
    error=abs(reaction-m['peso_total_gravitacional'])/m['peso_total_gravitacional']
    axial={key:abs(ops.eleResponse(e,'globalForce')[2]) for key,e in cols.items()}
    return masters,nodes,axial,error

def gravedad(b):
    m=metrar(b)
    _,_,ax,err=construir(b,m)
    return ax,err

def condensar(b,m):
    masters,nodes,ax,error=construir(b,m)
    if error>1e-6: raise RuntimeError(f'Desequilibrio gravitacional {error}')
    dofs=(1,2,6)
    def displacement(): return np.array([ops.nodeDisp(node,dof) for node in masters for dof in dofs])
    baseline=displacement()
    ops.loadConst('-time',0.)
    dim=3*b['n']; flex=np.zeros((dim,dim))
    ops.integrator('LoadControl',0.)
    for j in range(dim):
        tag=100+j; ops.timeSeries('Constant',tag); ops.pattern('Plain',tag,tag)
        force=1e4 if j%3<2 else 1e6
        f=[0.]*6; f[dofs[j%3]-1]=force
        ops.load(masters[j//3],*f)
        if ops.analyze(1)!=0: raise RuntimeError('Fallo condensación')
        flex[:,j]=(displacement()-baseline)/force
        ops.remove('loadPattern',tag); ops.remove('timeSeries',tag)
    asym=np.linalg.norm(flex-flex.T)/np.linalg.norm(flex)
    if asym>1e-6: raise RuntimeError(f'Flexibilidad no simétrica {asym}')
    K=np.linalg.inv((flex+flex.T)/2)
    return (K+K.T)/2,ax,error,asym

def matriz_masa(m,ex=0,ey=0):
    n=len(m['pesos']); M=np.zeros((3*n,3*n))
    for k in range(n):
        mass=m['pesos'][k]/G; J=m['inercia_peso'][k]/G
        M[3*k:3*k+3,3*k:3*k+3]=[[mass,0,-mass*ey],[0,mass,mass*ex],[-mass*ey,mass*ex,J+mass*(ex*ex+ey*ey)]]
    return M

def modos(K,M):
    chol=np.linalg.cholesky(M)
    inv=np.linalg.inv(chol)
    ev,v=np.linalg.eigh(inv@K@inv.T)
    if ev[0]<=0: raise RuntimeError('Rigidez no positiva / mecanismo')
    phi=np.linalg.solve(chol.T,v)
    w=np.sqrt(ev); periods=2*np.pi/w
    residual=np.linalg.norm(K@phi-M@phi*ev)/max(np.linalg.norm(K@phi),1)
    if residual>1e-7: raise RuntimeError('Residuo modal excesivo')
    return w,periods,phi,residual

def observadores(b,m):
    """Transforma Ux,Uy,Rz a desplazamientos y diferencias en puntos fijos."""
    n=b['n']; points=[(0.,0.),(sum(b['lx']),0.),(0.,sum(b['ly'])),(sum(b['lx']),sum(b['ly']))]
    D=np.zeros((n,2,5,3*n)); drift=np.zeros_like(D)
    for k in range(n):
        for p,(x,y) in enumerate(points+[tuple(m['cm'][k])]):
            for d in range(2):
                D[k,d,p,3*k+d]=1
                D[k,d,p,3*k+2]=-(y-m['cm'][k,1]) if d==0 else x-m['cm'][k,0]
                drift[k,d,p]=D[k,d,p]
                if k>0:
                    drift[k,d,p,3*(k-1)+d]-=1
                    drift[k,d,p,3*(k-1)+2]-=-(y-m['cm'][k-1,1]) if d==0 else x-m['cm'][k-1,0]
                drift[k,d,p]/=b['alturas'][k]
    return D,drift

def respuesta_caso(b,m,K,ex,ey):
    M=matriz_masa(m,ex,ey); w,T,phi,res=modos(K,M); rho=correlacion_cqc(w)
    D,DR=observadores(b,m); n=b['n']
    out=[]; ratios=[]
    for d in range(2):
        r=np.zeros(3*n); r[d::3]=1
        gamma=phi.T@M@r
        modal_u=phi*(gamma*espectro(T,b)/(w*w))[None,:]
        # Fuerzas modales con signo; luego sumar por encima de cada piso.
        force=K@modal_u
        story=np.array([[np.sum(force[3*k+axis::3],axis=0) for axis in range(2)] for k in range(n)])
        disp=cqc(D@modal_u,rho)
        dr=cqc(DR@modal_u,rho)
        out.append({'u':disp,'dr':dr,'v':cqc(story,rho)})
        ratios.append(gamma*gamma/(r@M@r))
    return out,T,np.array(ratios),res

def rigidez_pisos(b,m,K):
    """Ensayo estático independiente con traslación, giros restringidos.
    V/delta provienen de la misma carga. No divide envolventes espectrales.
    """
    n=b['n']; ret=[]
    h=np.cumsum(b['alturas']); force=m['pesos']*h; force/=sum(force)
    for d in range(2):
        ids=np.arange(d,3*n,3)
        disp=np.linalg.solve(K[np.ix_(ids,ids)],force)
        delta=np.diff(np.r_[0,disp]); shear=np.cumsum(force[::-1])[::-1]
        ret.append(shear/delta)
    return np.array(ret)

def analizar(b):
    m=metrar(b); K,ax,error,asym=condensar(b,m)
    nominal,T,ratios,res=respuesta_caso(b,m,K,0,0)
    tx,ty=[float(T[np.argmax(ratios[d])]) for d in range(2)]
    static,tstatic=cortante_estatico(b,sum(m['pesos']))
    cases=[]
    # Signo constante en altura. Casos desplazados solo perpendicularmente
    # al sismo correspondiente. Cada caso resuelve sus propios modos.
    for d in range(2):
        for sign in (-1,1):
            ex=sign*.05*sum(b['lx']) if d==1 else 0
            ey=sign*.05*sum(b['ly']) if d==0 else 0
            resp,_,_,_=respuesta_caso(b,m,K,ex,ey)
            cases.append((d,resp[d]))
    # Envolvente por dirección, incluyendo caso nominal.
    ux=[]; drx=[]; vx=[]; torsion=np.ones(2)
    for d in range(2):
        allc=[nominal[d]]+[v for direction,v in cases if direction==d]
        ux.append(np.maximum.reduce([v['u'] for v in allc]))
        drx.append(np.maximum.reduce([v['dr'] for v in allc]))
        vx.append(np.maximum.reduce([v['v'] for v in allc]))
        for v in allc:
            for k in range(b['n']):
                # En un diafragma rígido extremos están entre las esquinas.
                # Promedio de extremos del mismo caso y misma línea.
                pairs=[(0,2),(1,3)] if d==0 else [(0,1),(2,3)]
                for p,q in pairs:
                    a,z=v['dr'][k,d,p],v['dr'][k,d,q]
                    if max(a,z)*.75*R0>.5*LIM_DERIVA:
                        torsion[d]=max(torsion[d],2*max(a,z)/max(a+z,1e-15))
    displacement=combinar_direcciones(ux[0],ux[1])
    drift=combinar_direcciones(drx[0],drx[1])
    # 80% sólo bajo hipótesis de regularidad, que se comprueba parcialmente.
    scales=[max(1,.8*static/v[0,d]) for d,v in enumerate(vx)]
    vcombined=combinar_direcciones(vx[0]*scales[0],vx[1]*scales[1])
    story_stiff=rigidez_pisos(b,m,K)
    soft=[]
    for karr in story_stiff:
        fail=any(karr[i]<.7*karr[i+1] for i in range(len(karr)-1))
        fail=fail or any(karr[i]<.8*np.mean(karr[i+1:i+4]) for i in range(len(karr)-3))
        soft.append(bool(fail))
    mass_fail=any(max(a,z)>1.5*min(a,z) for a,z in zip(m['pesos'][:-2],m['pesos'][1:-1]))
    regular=not(any(soft) or mass_fail or max(torsion)>1.3)
    theta=[]
    for d in range(2):
        p=np.cumsum(m['peso_servicio'][::-1])[::-1]
        delta=drift[:,d,:4].max(axis=1)*np.array(b['alturas'])*.75*R0
        theta.append(float(np.max(p*delta/(np.maximum(vcombined[:,d],1)*np.array(b['alturas'])))))
    return {'metrado':m,'K':K,'axiales':ax,'error_equilibrio':error,'error_reciprocidad':asym,
            'residuo_modal':res,'periodos':T,'masa_modal':ratios,'Tx':tx,'Ty':ty,
            'T_estatico':tstatic,'V_estatico':static,'V_modal':np.array([vx[d][:,d] for d in range(2)]),
            'V_combinado':vcombined,'escala_fuerzas':scales,
            'u_elastica':displacement,'u_normativa':displacement*.75*R0,
            'deriva_elastica':drift,'deriva_normativa':drift*.75*R0,
            'torsion':torsion,'rigidez_pisos':story_stiff,'piso_blando':soft,
            'irregular_masa':mass_fail,'regularidad_evaluable':regular,'theta_indicador':theta}
