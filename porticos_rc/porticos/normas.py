"""Reglas versionadas. Fuentes y alcance en METODOLOGIA.md.

E.030: RM 183-2026, arts. 17,18,22,31,34,36,40-45,50-51.
E.060: DS010-2009, 9.6, 21.5.1,21.6.1. Solo predimensionamiento.
No constituye una certificación integral de regularidad/resistencia.
"""
import math
import numpy as np

G = 980.665
GAMMA_RC = 0.0024
R0 = 8.0
LIM_DERIVA = 0.007
VERSION = "E030_RM183_2026_E060_DS010_2009_E020_2006"
SOURCES = {
    "E030": "https://www.gob.pe/institucion/vivienda/normas-legales/8081915-183-2026-vivienda",
    "E060": "https://www.construccionyvivienda.com/norma-tecnica-e-060-concreto-armado/",
    "E020": "https://www.construccionyvivienda.com/norma-tecnica-e-020-cargas/",
}

def redondear(x, paso=5):
    return float(math.ceil((float(x)-1e-10)/paso)*paso)

def sitio(z, suelo):
    """Sin Vs30: extremos conservadores indicados en nota de tablas 4 y 5."""
    if z not in [0.10, 0.25, 0.35, 0.45]:
        raise ValueError("Z fuera de tabla E.030")
    if suelo == "S0": return 0.8, 0.3, 3.0
    if suelo == "S1": return 1.0, 0.4, 2.5
    if suelo == "S2": return {0.10:1.30,0.25:1.30,0.35:1.15,0.45:1.10}[z],0.6,2.0
    if suelo == "S3": return {0.10:1.60,0.25:1.40,0.35:1.20,0.45:1.20}[z],0.9,1.6
    raise ValueError("Suelo no implementado; no se extrapolan perfiles especiales")

def factor_c(t, tp, tl, estatico=False):
    t = np.asarray(t, dtype=float)
    if np.any(t < 0): raise ValueError("Período negativo")
    safe = np.maximum(t, 1e-12)
    c = np.where(t<=tp, 2.5, np.where(t<=tl, 2.5*tp/safe, 2.5*tp*tl/safe**2))
    if not estatico: c = np.where(t<0.2*tp, 1+7.5*t/tp, c)
    return c

def espectro(t, b):
    return b['z']*b['u']*b['s']*G/R0*factor_c(t,b['tp'],b['tl'])

def cortante_estatico(b, peso):
    # Art.36.1: altura en m y CT=35; conversion interna explícita desde cm.
    t = sum(b['alturas'])/100/35
    c = float(factor_c(t,b['tp'],b['tl'],True))
    return b['z']*b['u']*b['s']*max(c/R0,0.11)*peso,t

def correlacion_cqc(w, amort=0.05):
    r = np.asarray(w)[None,:]/np.asarray(w)[:,None]
    return 8*amort**2*(1+r)*r**1.5/((1-r*r)**2+4*amort**2*r*(1+r)**2)

def cqc(valores, rho):
    v=np.asarray(valores)
    return np.sqrt(np.maximum(np.einsum('...i,ij,...j->...',v,rho,v),0))

def combinar_direcciones(rx, ry):
    """Art.43: SRSS de 100% y 30%; envolvente de ambas orientaciones."""
    return np.maximum(np.hypot(rx,0.3*ry),np.hypot(0.3*rx,ry))

def losa_unidir(libre, continuos, fy, nervada):
    # E.060 tabla9.1, concreto normal. Hipótesis: divisiones desacopladas
    # frente a flecha; no verifica resistencia ni flecha de larga duración.
    divisor = ([16,18.5,21] if nervada else [20,24,28])[continuos]
    factor = 0.4 + (fy*0.0980665)/700
    return libre/divisor*factor

def losa_bidir(lx, ly, h, vigax, vigay, borde, fy):
    """E.060 9.6.3.3; alpha conservador con viga rectangular sin ala.
    Para alpha<=0.2: tabla9.3 panel exterior sin ábaco ni viga de borde,
    fila fy=420 MPa (conservadora para fy<=420MPa). No extrapola fy mayor.
    """
    fmpa=fy*0.0980665
    if fmpa>420: raise ValueError("Tabla9.3: fy>420MPa requiere ampliar tabla")
    bx,hx=vigax; by,hy=vigay
    alpha=0.5*(bx*hx**3/(ly*h**3)+by*hy**3/(lx*h**3))
    beta=max(lx,ly)/min(lx,ly)
    ln=max(lx,ly)
    if alpha<=0.2: req=ln/30
    else:
        den=36+5*beta*(min(alpha,2)-0.2) if alpha<=2 else 36+9*beta
        req=max(12.5 if alpha<=2 else 9,ln*(0.8+fmpa/1400)/den)
        # Aplicación conservadora del incremento de borde 9.6.3.3(d).
        if borde: req*=1.1
    return max(15,req),alpha
