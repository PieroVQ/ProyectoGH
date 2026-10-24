# Modelo, reglas y trazabilidad

## Versiones y fuentes

- E.030: RM183-2026-VIVIENDA. [Publicación oficial](https://www.gob.pe/institucion/vivienda/normas-legales/8081915-183-2026-vivienda).
- E.060: DS010-2009-VIVIENDA. [Repositorio oficial RNE](https://www.gob.pe/institucion/vivienda/informes-publicaciones/2309793-reglamento-nacional-de-edificaciones-rne).
- E.020: DS011-2006-VIVIENDA, cargas y pesos.
- Para consulta del articulado: [E.030](https://www.construccionyvivienda.com/norma-tecnica-e-030-diseno-sismorresistente/), [E.060](https://www.construccionyvivienda.com/norma-tecnica-e-060-concreto-armado/), [E.020](https://www.construccionyvivienda.com/norma-tecnica-e-020-cargas/).
- [OpenSeesPy elasticBeamColumn](https://openseespydoc.readthedocs.io/en/latest/src/elasticBeamColumn.html), [masa y peso](https://openseesdigital.com/2020/11/20/mass-and-weight/).

Las reglas están centralizadas en `normas.py`. Se debe revisar la versión antes
de utilizar el proyecto con posteriores modificaciones normativas. La fuente
oficial tiene precedencia sobre las reproducciones web.

## Idealización explícita

Pórticos espaciales Euler–Bernoulli, secciones brutas, ejes de elementos entre
centros de nudos, sin brazos rígidos ni aporte de alas de losa. Conexiones rígidas.
Base empotrada. Ec se convierte desde la expresión de E.060 en MPa al sistema
kgf/cm²; Poisson=0.20 es una hipótesis del estudio. La torsión de rectángulos
usa una aproximación de Saint-Venant; no es una regla de la E.030.

Cada piso tiene un diafragma rígido con Ux, Uy y Rz. Se integra el peso de cada
rectángulo de losa, segmento de viga y columna, incluyendo su centroide e
inercia polar. La mitad del peso de la columna del primer piso asignada a la
base no participa en la masa libre. No hay masa vertical dinámica ni análisis
de sismo vertical. No se infiere la flexibilidad de un suelo a partir de S.

La flexibilidad de los 3n DOF se calcula con 3n cargas unitarias en OpenSees.
Invertirla produce la rigidez estáticamente condensada del pórtico 3D. Los DOF
eliminados carecen de masa en esta idealización. Se resuelve Kφ=ω²Mφ por
Cholesky y eigensolución simétrica NumPy. Se utilizan todos los 3n modos,
que recuperan la masa participante horizontal del modelo. Una prueba los
compara con `ops.eigen('-fullGenLapack',3n)`.

## Predimensionamiento

Columnas: criterio empírico Pserv/(0.35fc), redondeo a 5cm, grupos esquina,
exterior e interior. Se actualiza con axiales de gravedad y carga tributaria.
Las áreas requeridas finales se exportan por grupo. Secciones superiores no
mayores que las inferiores. Relación rectangular inicial 1 o 1.25, con eje mayor
en la dirección global más corta. Se evita que vigas excedan el ancho del núcleo.

Vigas: peralte común por dirección, gobernado por luz máxima/10, mínimo inicial
50cm como restricción del estudio compatible con base de 25cm y b/h<=0.5.
Se verifica luz libre>=4h; ancho mínimo de pórticos y límites geométricos de
E.060 21.5/21.6 se respetan en el dominio configurado. No se diseña refuerzo.

Losas: mínimo del estudio 15cm maciza y 20cm aligerada. E.060 tabla9.1 para
una dirección; 9.6.3.3 para maciza bidireccional con relación libre<=2.
Se evalúa continuidad por ubicación del paño. Para alpha de losas bidireccionales
se usa la viga rectangular sin ala, conservadora respecto de su rigidez.
Se incrementa 10% en borde en esa rama como decisión conservadora. Para
alpha<=0.2 se usa el caso exterior sin ábaco/rigidez de borde de tabla9.3 a
fy=420MPa, sólo si el fy configurado no supera ese valor. Espesor macizo
redondeado a 1cm; aligerado a catálogo 20/25/30cm. Requerimientos mayores
descartan el caso en vez de extrapolar el peso de aligerantes.

No se atribuyen los mínimos de 15/20cm ni las fórmulas empíricas de columnas
y vigas a una obligación normativa universal. No se incluye el criterio de
columna fuerte/viga débil porque exige capacidades con armaduras.

## Cargas

Catálogo: C01 vivienda homogénea q=0.020; C02 oficina homogénea q=0.025;
B01 museo/área de asamblea homogénea q=0.040; B02 comercio homogéneo
q=0.050 kgf/cm². C corresponde a U=1 y B a U=1.3. C02 no representa
corredores de oficinas con carga distinta; tales áreas deben modelarse en una
extensión del catálogo. Cubierta plana no ocupada regularmente: 0.010 kgf/cm².

Acabados 0.008/0.010/0.012 y tabiquería fija aislada 0/0.010/0.015 kgf/cm²
son hipótesis de carga equivalente del estudio, no valores normativos de
tabiquería real. No hay tabiques móviles ni peso de escaleras. Las cargas se
repiten en pisos típicos; la cubierta no recibe tabiquería. Los paños macizos
pueden representar zonas reservadas, sin introducir huecos ni equipos.

Concreto 0.0024 kgf/cm³. Aligerados del anexo E.020: nervio10cm cada40cm,
capa5cm, pesos 0.030/0.035/0.042 kgf/cm² para 20/25/30cm. No se reemplaza
ese peso por un volumen macizo. Las áreas de losa excluyen vigas y columnas;
las vigas se metran entre caras de columnas, que se metran en altura completa.

Las losas unidireccionales transfieren a dos vigas y las macizas bidireccionales
usan reparto geométrico de 45 grados. Las cargas por viga se aproximan mediante
una distribución uniforme con la misma resultante. Por ello, este proyecto no
entrega momentos gravitacionales de losa/viga como resultados de diseño.
La masa se integra por separado según su ubicación real. No se aplican
reducciones de carga viva gravitacional.

## Respuesta sísmica y comprobaciones

Tablas4/5: sin Vs30, se usan extremos prescritos de S2/S3; no se interpola al
azar. Espectro art.18 con rama ascendente corta y espectro estático diferenciado.
R=8 es hipótesis de ductilidad/regularidad. CQC al5%; combinación direccional
SRSS100/30, art.43. Excentricidades accidentales ±5% trasladan la masa, con
acoplamientos de traslación-rotación y teorema de ejes paralelos. Se mantienen
signos constantes en altura y se resuelve cada caso modalmente.

El cortante mínimo usa período empírico H/35 (H en metros convertidos desde
cm) y el límite C/R aplicable. Se ajustan fuerzas al80% del estático bajo la
hipótesis regular. Desplazamientos no reciben ese escalamiento; para la
comprobación regular se amplifican por0.75R y se comparan con0.007.

Se restan desplazamientos por modo antes de CQC. El cortante de piso suma
fuerzas modales con signo antes de combinar. Se reportan CM y esquinas.
Las envolventes independientes de signos accidentales y orientaciones son
conservadoras; no constituyen una deformada simultánea.

La rigidez de piso V/Δ se obtiene bajo una carga estática auxiliar común,
con giros y dirección transversal restringidos. Se verifican piso blando,
masa (con excepción de cubierta) y torsión condicionada a deriva. La planta
constante, retícula ortogonal sin huecos ni transferencias satisface por
construcción los criterios geométricos incluidos en este dominio.

Regularidad por resistencia, resistencia del diafragma y detallado dúctil
permanecen pendientes. No confundir los indicadores booleanos parciales con
una certificación. No se incluyen P–Delta: se informa P·Δ/(V·h) con cargas de
servicio y respuesta normativa como indicador orientativo del modelo lineal.
No se fija un umbral de ese indicador como si fuese una verificación de E.030.

## Reproducibilidad y restricciones de investigación

Semilla de familia=semilla global+104729·ID_familia. Máximo de tres variantes
iniciales: base, columnas+5cm, vigas+5cm; cuarta opcional combina incrementos.
No se fuerza el cumplimiento de deriva para conservar la variabilidad de
respuesta. Se filtran las irregularidades evaluables y se registra el descarte.
Este filtro cambia la distribución de la población: debe considerarse al
interpretar importancias de variables. Cien filas son un piloto.

El Excel contiene valores, no fórmulas que recalculen OpenSees. Modificar una
celda no actualiza sus resultados: vuelva a generar/analizar. La visualización
reconstruye la geometría almacenada, sin usar una nueva semilla.
