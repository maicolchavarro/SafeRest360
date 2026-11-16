# SafeRest 360: Brief de negocio AI Pitch 2026 — versión corregida

**Universidad de Boyacá · Ingeniería de Sistemas · Inteligencia Artificial · Noviembre de 2026**

Esta versión responde a las 15 observaciones del jurado (ver el anexo al final). Todo lo que aparece como "medido" se ejecutó con el prototipo y sus datos están en el repositorio del proyecto; lo que es estimación o supuesto se marca como tal.

---

## A. Propuesta de valor

SafeRest 360 usa las cámaras que el restaurante ya tiene para avisarle al administrador por **Telegram o WhatsApp** cuando alguien entra a una zona prohibida o cuando un área de trabajo se queda sola, para que pueda reaccionar a tiempo sin estar mirando las cámaras todo el día. Con Telegram los avisos no tienen costo por mensaje; WhatsApp sigue disponible para quien lo prefiera.

---

## B. El problema

El administrador de un restaurante no puede estar en todas partes al mismo tiempo. Las cámaras graban, pero casi nadie las mira en el momento, así que muchos problemas (alguien en la bodega, la caja sola, un área descuidada) se descubren horas o días después. Contratar a una persona solo para vigilar las pantallas es costoso para un negocio pequeño.

**¿Qué tan grande es el sector?** En Colombia hay cerca de 132.000 restaurantes y negocios de comida, y unos 54.100 son formales [1]. Además, los gremios del sector han hablado públicamente de la inseguridad como una de sus preocupaciones [2].

---

## C. La solución: cómo funciona

El sistema funciona en cinco pasos:

1. **Conexión:** se conecta a las cámaras del restaurante por RTSP, el protocolo estándar de las cámaras IP.
2. **Detección:** un modelo de inteligencia artificial ya entrenado (YOLOv8n) revisa unas 5 imágenes por segundo de cada cámara y reconoce dónde hay personas (no quiénes son).
3. **Seguimiento:** ByteTrack mantiene la identidad de cada persona entre imágenes.
4. **Reglas:** el administrador dibuja sobre la imagen en vivo las zonas que le interesan (bodega, caja) y configura reglas sencillas, por ejemplo "persona en la bodega después de las 10 p. m.".
5. **Aviso:** se guarda el evento con una foto del momento y se envía el mensaje con la foto por el canal que el restaurante elija: **Telegram** (sin costo por mensaje) o **WhatsApp**.

Nuestro aporte no es inventar un detector nuevo, sino adaptar uno probado a la operación diaria de un restaurante: zonas, horarios, tiempos de confirmación y avisos que no saturen.

| Qué detecta | Descripción | Estado en el prototipo |
|---|---|---|
| Entrada a zona restringida | Avisa si alguien permanece dentro de un lugar marcado como prohibido (bodega, cuarto técnico). Que alguien entre no significa que no tenga permiso; el aviso es para que el administrador revise. | Funciona en vivo |
| Zona sin personal | Avisa si un área importante (caja, barra, cocina) se queda sin nadie más tiempo del definido. La pantalla muestra la cuenta regresiva antes del aviso. | Funciona en vivo |
| Aforo máximo | Avisa si hay más personas de las permitidas en una zona. | Funciona en vivo |
| Situaciones fuera de lo normal | Solo casos concretos acordados con cada restaurante y probados antes. | Más adelante, tras pruebas |

---

## D. Arquitectura del sistema

*[Observación del jurado #1: arquitectura en la nube]*

**Componentes:**

| Componente | Tecnología | Función |
|---|---|---|
| Aplicación web | Next.js, TypeScript | Panel, cámaras, editor de zonas y reglas, centro de alertas |
| API | FastAPI (Python) | Usuarios y roles, cámaras, zonas, reglas, alertas; cada restaurante solo ve sus datos |
| Lector de cámaras | OpenCV + FFmpeg | Lee el video RTSP, se reconecta solo, conserva solo la imagen más reciente |
| Motor de visión | YOLOv8n + ByteTrack + motor de reglas | Detecta personas, las sigue y evalúa las reglas de cada zona |
| Base de datos | SQLite (desarrollo) / PostgreSQL (producción) | Restaurantes, usuarios, cámaras, zonas, reglas, alertas, notificaciones |
| Avisos | Telegram Bot API (predeterminado) o WhatsApp Business Platform | Envía el aviso con la foto a los administradores |

**Flujo de datos:** cámara (RTSP) → lector de cámaras → motor de visión → evento → alerta guardada con foto → aviso por Telegram o WhatsApp → el administrador la revisa y la marca como revisada, resuelta o falsa alarma.

**¿Dónde se procesa el video?** La decisión se tomó con los costos de la sección L:

- **En el restaurante (recomendado).** Un equipo pequeño en el local lee las cámaras y ejecuta el modelo. Solo salen a internet los eventos, las fotos de las alertas y el estado de las cámaras. Así las cámaras nunca quedan expuestas a internet y el video continuo no sale del restaurante.
- **En la nube.** Técnicamente posible, pero el costo por restaurante supera el precio del plan (sección L).

La API, la base de datos y el panel sí van en la nube (contenedores Docker), compartidos por todos los restaurantes. En el prototipo actual el lector de cámaras corre dentro de la API para simplificar la demo; separarlo como servicio en el restaurante es el siguiente paso de arquitectura.

---

## E. Cámaras: ¿sirven las que ya tengo?

**Opción 1 – Usar las cámaras que ya tiene.** Antes de vender, visitamos el restaurante y probamos las cámaras durante 3 a 7 días, de día y de noche. Revisamos si se puede acceder a la imagen por RTSP, la calidad, la luz, el ángulo y si hay objetos que tapen la vista. Si las cámaras son sencillas, solo ofrecemos lo básico (entrada a zona restringida y zona sin personal), y solo si la prueba sale bien.

**Opción 2 – Cámaras recomendadas por SafeRest 360.** Para clientes que necesiten renovar, recomendamos cámaras IP de 4 megapíxeles, conectadas por cable, compatibles con ONVIF, con visión nocturna y que manejen bien la luz fuerte de puertas y ventanas. Una buena cámara mal ubicada también falla: por eso solo damos garantía después de probarla en el sitio, con la meta de detectar al menos 9 de cada 10 presencias y no más de 3 falsas alarmas por cámara al día.

**¿Cuánto cuestan?** En tiendas colombianas, una cámara de este tipo cuesta entre $450.000 y $600.000, y en Mercado Libre entre $465.000 y $740.000 (precios consultados en octubre de 2026) [3][4]. La instalación se cotiza con un técnico local.

| Característica | Mínimo | Recomendado |
|---|---|---|
| Resolución | 720p (1280×720) | 1080p o 4 MP |
| Protocolo | RTSP | RTSP + ONVIF |
| Conexión | Wi-Fi | Cable Ethernet (PoE) |
| Visión nocturna | Deseable | Sí (infrarrojo) |

**Fuentes de video probadas en el prototipo:** cámaras IP simuladas (servidor RTSP local con videos de archivo de restaurante con licencia libre) y un celular Android usado como cámara IP. La app solo acepta direcciones `rtsp://` o `rtsps://`.

---

## F. Clientes y competencia

**¿Quién pagaría?** El dueño o administrador de un restaurante pequeño o mediano que ya tiene entre 2 y 8 cámaras y no puede pagar a alguien para vigilarlas. Empezaríamos en Tunja y Boyacá, y luego en otras ciudades intermedias.

| Alternativa que existe hoy | Qué ofrece | Por qué SafeRest 360 es diferente |
|---|---|---|
| Cámaras tradicionales con su app | Grabar y ver en vivo desde el celular | Avisan por cualquier movimiento y no entienden zonas ni tiempos; alguien tiene que revisar. |
| Cámaras "inteligentes" (Hikvision, Dahua) | Detectan personas desde la misma cámara | Hay que comprar cámaras nuevas (unos $590.000 cada una) y los avisos llegan a una app propia. |
| Plataformas de seguridad con IA (Coram AI, Eagle Eye, Verkada) | Análisis avanzado de video en la nube | Pensadas para empresas grandes; precios por cotización, estimados entre US$15 y US$50 por cámara al mes [5]. |
| Un vigilante o monitorista | Criterio humano | Cuesta un salario y no puede mirar todo a la vez. |

**Nuestra diferencia:** aprovecha las cámaras existentes, los avisos se ajustan a cada restaurante (zonas, horarios, tiempos), llegan con foto por Telegram o WhatsApp (aplicaciones de mensajería comunes, no una app propia), se instala en una sola visita y cuesta menos que las plataformas similares.

---

## G. Motor de visión: modelos y licencias

*[Observación del jurado #3: selección y licenciamiento de YOLO]*

YOLO (You Only Look Once) es una familia de detectores de objetos en tiempo real que procesa la imagen completa en una sola pasada [11]. Evaluamos además RF-DETR, un detector tipo transformer con licencia permisiva [15].

| Modelo | Autor | Licencia código / pesos | Parámetros | Uso en un SaaS de código cerrado |
|---|---|---|---|---|
| YOLOv8n | Ultralytics | AGPL-3.0 / AGPL-3.0 | 3,16 M | Requiere licencia Enterprise de Ultralytics |
| YOLOv8s | Ultralytics | AGPL-3.0 / AGPL-3.0 | 11,17 M | Requiere licencia Enterprise |
| YOLOv8m | Ultralytics | AGPL-3.0 / AGPL-3.0 | 25,90 M | Requiere licencia Enterprise |
| RF-DETR Nano | Roboflow | Apache-2.0 / Apache-2.0 | 30,47 M | Permitido |
| RF-DETR Small | Roboflow | Apache-2.0 / Apache-2.0 | 32,11 M | Permitido |
| YOLO-NAS-S | Deci AI | Apache-2.0 / licencia propia | ~12 M | **Los pesos preentrenados no permiten uso comercial** |

**Licencias.** AGPL-3.0 obliga a publicar el código fuente de un servicio que use YOLOv8, o a comprar la licencia Enterprise de Ultralytics (precio por cotización). El repositorio de SafeRest 360 es público, así que el MVP académico cumple esa condición.

**Corrección respecto a la versión anterior:** se había dicho que YOLO-NAS-S era "libre para uso comercial". El código de super-gradients es Apache-2.0, pero sus pesos preentrenados tienen una licencia propia de Deci que prohíbe el uso comercial sin un acuerdo aparte [14]. YOLO-NAS queda **descartado**.

**Estrategia:** MVP con **YOLOv8n preentrenado** (código publicado). Para un producto comercial de código cerrado: **RF-DETR** (Apache-2.0) o la licencia Enterprise de Ultralytics. La elección se basa en las mediciones de la sección I.

---

## H. Datos y entrenamiento por Transfer Learning

*[Observaciones del jurado #4 y #5: Transfer Learning y datasets]*

**Dataset.** Usamos el dataset público COCO 2017 [12]. **Estos datos no fueron recopilados por el equipo**; no se grabó a personas en restaurantes.

- Fuente: **COCO val2017**. Los pesos preentrenados de los modelos se entrenaron con train2017, así que usar val2017 evita evaluar con imágenes que los modelos ya vieron.
- Solo la clase persona (`category_id = 1`), sin anotaciones de multitud (`iscrowd = 0`).
- **2.000 imágenes con 7.680 personas**, divididas por imagen (semilla 42): **1.400 entrenamiento / 400 validación / 200 prueba**. El conjunto de prueba tiene **775 personas**.

**Aumentación.** Albumentations [16]: volteo horizontal, brillo y contraste (±0,3), ruido gaussiano, desenfoque de movimiento, escala (±20 %) y desenfoque gaussiano. En el experimento final se entrenó solo con las 1.400 imágenes originales, porque Ultralytics ya aumenta los datos en cada época y las copias adicionales triplicaban el tiempo de entrenamiento en CPU.

**Protocolo de Transfer Learning.**

1. Se parte de los pesos de COCO (80 clases) y se reentrena para una sola clase, persona. En YOLOv8n se transfieren 349 de 355 tensores; la cabeza de detección se reinicia.
2. **Diseñado (GPU):** 100 épocas, 640 px, lote 16, AdamW, tasa 0,001, parada temprana a 20 épocas.
3. **Ejecutado (CPU, sin GPU):** YOLOv8n, 15 épocas, 416 px, lote 8, AdamW, tasa 0,001, parada temprana a 10, semilla 42. Duró **59,5 minutos** en un portátil con AMD Ryzen 7 5700U. El intento en Google Colab (GPU T4) no se completó por desconexiones.
4. Cada experimento queda registrado (`vision-engine/experiments/`), con la curva época por época.

---

## I. Comparación de modelos y resultados medidos

*[Observaciones del jurado #6 y #7: estado del arte y comparación]*

**Estado del arte (cifras publicadas por los autores, no medidas por el equipo).** No son comparables entre sí porque usan benchmarks distintos.

| Referencia | Modelo | Resultado publicado | Benchmark |
|---|---|---|---|
| Redmon et al. (2016) [11] | YOLOv1 | 63,4 mAP | PASCAL VOC 2007 |
| Bochkovskiy et al. (2020) [13] | YOLOv4 | 43,5 AP (65,7 AP50) | COCO test-dev |
| Jocher et al. (2023) [17] | YOLOv8x | 53,9 mAP50-95 | COCO val2017, 80 clases |
| Deci AI (2023) [14] | YOLO-NAS-L | 52,2 mAP50-95 | COCO val2017, 80 clases |

**Método de medición del equipo.** El mismo código evaluó todos los modelos sobre las 200 imágenes de prueba (775 personas):

- **mAP@50 y mAP@50-95:** evaluación oficial de COCO (`pycocotools`), solo personas.
- **Precisión, recall y F1:** al umbral de confianza 0,5 que usa la aplicación, con IoU ≥ 0,5.
- **Latencia:** promedio por imagen en un portátil con CPU AMD Ryzen 7 5700U, **sin GPU**.

| Modelo | Licencia | Entrada | mAP@50 | mAP@50-95 | Precisión | Recall | F1 | Latencia CPU | FPS CPU |
|---|---|---|---|---|---|---|---|---|---|
| YOLOv8n preentrenado | AGPL-3.0 | 640 px | 0,736 | 0,483 | 0,936 | 0,475 | 0,630 | 50 ms | 20,1 |
| YOLOv8s preentrenado | AGPL-3.0 | 640 px | 0,792 | 0,555 | 0,917 | 0,587 | 0,716 | 99 ms | 10,1 |
| YOLOv8m preentrenado | AGPL-3.0 | 640 px | 0,819 | 0,588 | 0,897 | 0,663 | 0,763 | 300 ms | 3,3 |
| RF-DETR Nano preentrenado | Apache-2.0 | 384 px | 0,782 | 0,527 | 0,904 | 0,609 | 0,728 | 208 ms | 4,8 |
| RF-DETR Small preentrenado | Apache-2.0 | 512 px | **0,832** | **0,589** | 0,903 | **0,676** | **0,773** | 390 ms | 2,6 |
| YOLOv8n preentrenado | AGPL-3.0 | 416 px | 0,655 | 0,420 | 0,956 | 0,395 | 0,559 | 37 ms | 27,2 |
| YOLOv8n con Transfer Learning (15 épocas) | AGPL-3.0 | 416 px | 0,578 | 0,339 | 0,916 | 0,339 | 0,495 | 38 ms | 26,5 |

**Lectura de los resultados.**

1. **Pocas falsas alarmas, muchas personas no detectadas por imagen.** La precisión está entre 0,90 y 0,96, pero el recall entre 0,34 y 0,68. La causa principal son las personas pequeñas o lejanas, frecuentes en COCO: en YOLOv8n a 640 px la precisión media fue 0,19 en personas pequeñas frente a 0,76 en grandes (RF-DETR Small: 0,27 frente a 0,86).
2. **El Transfer Learning corto empeoró el modelo** (mAP@50 de 0,578 frente a 0,655 sin ajustar, a 416 px). Las causas: la cabeza de detección se reinicia; solo hubo 1.400 imágenes y 15 épocas en CPU, frente a las 118.000 imágenes del modelo original; y la validación seguía mejorando al terminar (0,438 en la época 1 y 0,602 en la 15). **Conclusión:** con este presupuesto, el ajuste no supera al modelo preentrenado. Vale la pena repetirlo con imágenes de restaurantes reales, con consentimiento, y con GPU.
3. **Frente a las metas de la sección J:** mAP@50 ≥ 0,80 lo cumplen YOLOv8m y RF-DETR Small; ≥ 15 FPS en CPU solo YOLOv8n; **ningún modelo llega a recall ≥ 0,85 por imagen**.

**Modelo elegido.**

- **MVP: YOLOv8n preentrenado, 640 px.** Es el único que funciona en tiempo real en CPU y tiene la mayor precisión a 640 px.
- **Producto comercial: RF-DETR Small** (Apache-2.0), el más preciso. Necesita GPU o analizar menos imágenes por segundo.
- **Riesgo abierto:** el recall se midió por imagen. La meta comercial (9 de cada 10 presencias) se mide por evento: una persona que permanece varios segundos en una zona aparece en muchas imágenes seguidas. Que esto eleve la detección por evento es una hipótesis que **debe verificarse en el piloto**.

---

## J. Protocolo de evaluación

*[Observación del jurado #8: protocolo de evaluación]*

**Métricas del modelo:** mAP@50 (principal), mAP@50-95, precisión, recall y F1.

**Metas:**

- Laboratorio, por imagen: mAP@50 ≥ 0,80 y procesamiento ≥ 15 imágenes por segundo.
- Piloto, por evento (la garantía comercial): detectar al menos 9 de cada 10 presencias y no más de 3 falsas alarmas por cámara al día.

**Piloto en un restaurante real:**

1. 1 restaurante, 2 a 4 cámaras, de 3 a 7 días, con aviso visible de videovigilancia y autorización del dueño.
2. Mínimo 168 horas de video procesadas (una semana completa).
3. Revisión manual de una muestra de eventos y de 200 imágenes al azar para calcular precisión y recall reales.
4. Condiciones variadas: día, noche, hora pico, hora valle y luz artificial.
5. Métricas de negocio: avisos útiles frente a falsas alarmas (marcadas por el operador en la app) y tiempo de respuesta del administrador.

**Rendimiento:** latencia medida en CPU (sección I). La medición en GPU queda pendiente.

---

## K. Reglas, avisos y falsos positivos

*[Observaciones del jurado #9 y #10: coherencia de los avisos y falsos positivos]*

**Cómo decide el sistema** (implementado y con pruebas automatizadas):

- Cada zona es un polígono dibujado sobre la imagen. Una persona cuenta como "dentro" si **sus pies** (el punto inferior central de su recuadro) caen dentro del polígono; así no se activa por alguien que solo pasa por delante.
- Cada zona nueva trae una regla por defecto que el administrador puede cambiar en el **editor de reglas**:

| Regla | Cuándo avisa | Por defecto | Ajustable |
|---|---|---|---|
| Entrada prohibida | Alguien permanece dentro durante el **tiempo de confirmación** | Confirmar 2 s · gravedad alta · repetir cada 2 min | Confirmación 0–600 s |
| Zona sin personal | La zona sigue vacía más del tiempo máximo | 2 min · gravedad media · repetir cada 5 min | 10 s a 24 h |
| Aforo máximo | Hay más personas que el máximo durante la confirmación | 5 personas · confirmar 2 s | 1–100 personas |

- **Horarios:** cada regla puede aplicar solo ciertos días y horas, en la zona horaria del restaurante, incluidos turnos que cruzan la medianoche (por ejemplo, bodega restringida de 22:00 a 06:00).
- **Estado en vivo:** la pantalla de cada cámara colorea las zonas: atendida (verde), abandonada con la cuenta regresiva hasta el aviso (ámbar), y sin atender o intrusión con el aviso ya enviado (rojo).

**Cómo se evitan las falsas alarmas:**

1. **Tiempo de confirmación:** una detección de un solo instante no genera aviso.
2. **Espera entre avisos:** mientras la situación continúe, la misma regla no repite el aviso antes del tiempo configurado.
3. **Horarios:** la regla no aplica cuando no tiene sentido (por ejemplo, la bodega durante el turno).
4. **Umbral de confianza** de 0,5, con precisión medida de 0,936 en YOLOv8n (sección I).
5. **Revisión humana:** el operador marca cada aviso como revisado, resuelto o falsa alarma; esos datos sirven para ajustar zonas y reglas en el piloto.

**Coherencia de los avisos.** Con 4 cámaras, 3 o 4 zonas, confirmación de 2 s y espera de 2 a 5 minutos, unos 10 avisos al día es un volumen alcanzable para eventos reales; si llegan muchos más, normalmente las reglas están mal ajustadas y el administrador termina ignorándolos. Por eso el cupo de **300 avisos al mes** se mantiene en el canal WhatsApp, donde cada mensaje cuesta. En Telegram no hay cupo de cobro porque los mensajes no cuestan, pero la recomendación de ajustar las reglas para no saturar al administrador es la misma. Las políticas comerciales del cupo de WhatsApp (avisar al cliente al llegar al 80 % y 100 %, resumen diario de los avisos no críticos, y que los avisos de zona restringida nunca se detengan) **aún no están implementadas** en el prototipo.

**Canales de aviso y sus requisitos** *[Observación #14]*. El administrador elige el canal; el mensaje es el mismo en ambos: la foto de la alerta con qué pasó, en qué zona y cámara, la gravedad y la frase "Aviso para revisión. La decisión final la toma una persona".

| | Telegram (predeterminado) | WhatsApp |
|---|---|---|
| Costo por mensaje | **Sin costo**: la API de bots de Telegram no cobra por mensaje [21] | ≈ US$0,0009 por mensaje de utilidad en Colombia [6][7] |
| Requisitos | Crear un bot con BotFather; cada administrador abre el bot y pulsa Iniciar (/start), porque un bot no puede escribirle a quien no lo ha iniciado; se registra su identificador de chat | Cuenta de WhatsApp Business Platform verificada por Meta, plantilla de mensaje de "utilidad" aprobada por Meta y autorización (opt-in) de cada número |
| Límites | Límites de frecuencia de Telegram (del orden de un mensaje por segundo por chat) [21]; la espera entre avisos de cada regla queda muy por debajo | Cupo del plan: 300 avisos al mes |
| Estado en el prototipo | **Funciona con un bot real**: se envió y entregó un mensaje de prueba; cada alerta nueva sale con su foto y el resultado queda registrado (enviado, fallido o desconocido) | Implementado en **modo prueba** (se registra sin enviarse); el envío real con credenciales de Meta no se ha probado |
| Ventaja para el cliente | Avisos sin costo ni cupo; requiere tener Telegram | No requiere instalar otra aplicación si el administrador ya usa WhatsApp |

---

## L. Modelo de negocio y viabilidad económica

*[Observación del jurado #15: viabilidad económica]*

**Precios tentativos.** El precio mensual es el mismo en los dos canales; lo que cambia es el cupo de avisos, porque solo WhatsApp tiene costo por mensaje.

| Concepto | Precio (COP) | Qué incluye |
|---|---|---|
| Visita de evaluación | $80.000 | Prueba de las cámaras; se descuenta de la instalación si el cliente contrata. |
| Instalación y configuración (una sola vez) | $400.000 | Conectar hasta 4 cámaras, marcar zonas y horarios, configurar el canal de avisos y enseñar a usar el sistema. |
| **Plan Base con Telegram** (recomendado) | $149.000 / mes | Hasta 4 cámaras, **avisos con foto por Telegram sin cupo ni costo adicional**, 2 administradores que reciben avisos, historial de 30 días y soporte. |
| **Plan Base con WhatsApp** | $149.000 / mes | Hasta 4 cámaras, **300 avisos al mes por WhatsApp**, 2 celulares que reciben avisos, historial de 30 días y soporte. |
| Cámara adicional | $30.000 / mes | Hasta 8 cámaras por local (ambos planes). |
| Más avisos por WhatsApp | $15.000 por 300 más | Solo plan WhatsApp. Antes de cobrar, revisamos gratis si las reglas están bien ajustadas. |
| Cámara nueva (si la necesita) | $450.000 – $600.000 | Precio de referencia en tiendas; la instalación se cotiza aparte. |

El Plan Base equivale a unos US$9 por cámara al mes, menos que las plataformas con IA (US$15–50) y mucho menos que un vigilante. El cliente puede cambiar de canal en cualquier momento.

**Costo de los avisos.**

- **Telegram: $0.** La API de bots de Telegram no cobra por mensaje [21]; solo impone límites de frecuencia, que la espera entre avisos de cada regla respeta.
- **WhatsApp:** los avisos son "mensajes de utilidad", que en Colombia cuestan alrededor de US$0,0009 cada uno [6][7]. Suponiendo que ningún mensaje es gratis: 300 avisos × 2 celulares + 10 % ≈ 660 mensajes ≈ **US$0,60 al mes por restaurante (unos $2.500)**. Un proveedor intermediario cobraría una tarifa adicional.

**Costo de procesar el video.** Es el costo dominante y se calculó con lo medido:

- YOLOv8n procesa unas 20 imágenes por segundo en un procesador de portátil (sección I). A 5 imágenes por segundo por cámara, eso alcanza para unas **4 cámaras**, que es justo el Plan Base.
- **Opción nube:** una máquina virtual comparable (Google Cloud e2-standard-8) cuesta unos US$0,268 la hora, ≈ **US$196 al mes** [18], es decir ≈ **$813.000 por restaurante**, más de 5 veces el precio del plan. **No es viable.**
- **Opción en el restaurante (elegida):** un equipo con el mismo procesador medido. Referencia: un portátil con Ryzen 7 5700U cuesta unos $2.130.000 en una tienda colombiana [19]; un mini PC equivalente debería costar menos (por confirmar). Amortizado en 24 meses: ≈ **$88.750 al mes**.

**Escenarios mensuales (Plan Base, 4 cámaras).** Supuestos: tasa de 4.150 COP/USD (la implícita en el Brief original); el equipo del restaurante lo pone SafeRest 360 en comodato y se amortiza en 24 meses; la plataforma compartida (API, base de datos y almacenamiento en la nube) cuesta US$50 al mes hasta 10 restaurantes y US$150 al mes con 50. **Este último es un supuesto del equipo que falta cotizar.** No incluye salarios ni la instalación (que se cobra aparte).

| Restaurantes | Ingreso | Equipos en restaurantes | Plataforma | Resultado con Telegram (avisos $0) | Resultado con WhatsApp (avisos $2.500 por restaurante) |
|---|---|---|---|---|---|
| 1 | $149.000 | $88.750 | $207.500 | −$147.250 | −$149.750 |
| 10 | $1.490.000 | $887.500 | $207.500 | $395.000 (27 %) | $370.000 (25 %) |
| 50 | $7.450.000 | $4.437.500 | $622.500 | $2.390.000 (32 %) | $2.265.000 (30 %) |

**Lectura:** el costo de los avisos es pequeño frente al del equipo que procesa el video; el beneficio de Telegram no es tanto el ahorro (unos $2.500 por restaurante al mes) como poder ofrecer **avisos sin cupo** sin que el costo crezca con el uso. Si el cliente compra el equipo junto con la instalación, como ya se hace con las cámaras nuevas, el costo mensual se reduce a avisos y plataforma, y el margen supera el 80 % desde 10 restaurantes en ambos canales. La decisión entre comodato y venta del equipo se validará en el piloto, junto con el precio.

---

## M. Reconocimiento facial: solo empleados y en una fase futura

*[Observación del jurado #12: reconocimiento facial]*

El reconocimiento facial **no está en el MVP**; el sistema detecta "persona", no identidades. Para saber si quien entró a la bodega es personal autorizado habría que validar técnica y legalmente su identidad, porque en Colombia la cara es un **dato sensible**: la Ley 1581 de 2012 exige autorización previa, expresa e informada [8], y la Superintendencia de Industria y Comercio (SIC) ha dicho que no se puede obligar a nadie a usar reconocimiento facial sin ofrecer otra opción [9]. Como un empleado puede sentirse presionado por su jefe, no basta con una cláusula en el contrato de trabajo. Por eso, si se implementa:

- **Nunca clientes ni visitantes:** sus rostros no se guardan ni se comparan.
- **Datos protegidos:** se guarda una huella digital del rostro cifrada (no fotos), con acceso restringido, y se borra al terminar el contrato o cuando el empleado lo pida.
- **Siempre revisa una persona:** la IA puede equivocarse; nadie puede ser sancionado solo por lo que diga el sistema.
- **Antes de construirlo:** validación con un abogado especialista en protección de datos.

---

## N. Privacidad y protección de datos

*[Observación del jurado #13: protección de datos]*

**Un aviso es una alerta para revisar, nunca una acusación; la decisión final siempre la toma una persona.**

| Medida | Estado en el prototipo |
|---|---|
| Las imágenes en vivo solo existen en memoria; se guarda una foto únicamente cuando hay una alerta | Implementado |
| Cada restaurante solo ve sus cámaras, zonas, reglas, alertas y fotos (con pruebas automatizadas de aislamiento) | Implementado |
| Inicio de sesión con contraseña cifrada (bcrypt) y tokens JWT; roles de administrador y operador | Implementado |
| Las cámaras no se exponen a internet: el video se lee dentro de la red local; el servidor RTSP de pruebas solo escucha en el propio equipo | Implementado en desarrollo; en producción, con el equipo en el restaurante (sección D) |
| La app solo acepta direcciones de cámara RTSP, para que no se pueda usar para abrir otros archivos o servicios | Implementado |
| Los avisos con foto solo llegan a los chats de Telegram o números registrados por el administrador del restaurante; las credenciales del bot y de WhatsApp viven solo en el servidor, nunca en la app web | Implementado |
| Depuración de alertas y fotos por el administrador (una por una, o las anteriores a N días; 30 por defecto) | Implementado |
| Borrado automático programado de las fotos a los 30 días | Pendiente |
| Cifrado de las fotos guardadas y HTTPS en producción | Pendiente |
| Registro de auditoría de quién ve o cambia qué | Pendiente |

**Cumplimiento [8][10]:** aviso visible de videovigilancia en el local, política de tratamiento de datos publicada, registro de la base de datos ante la SIC cuando aplique, y un procedimiento para consultar, corregir o eliminar datos.

**Datos usados por el equipo:** solo datos públicos (COCO, videos de archivo con licencia libre) y grabaciones propias del equipo con su consentimiento. No se recopilaron imágenes de personas de forma indiscriminada.

---

## O. Robustez y casos límite

*[Observación del jurado #11: robustez]*

| Escenario | Riesgo | Mitigación | Estado |
|---|---|---|---|
| Personas lejanas o pequeñas | No se detectan (recall de 0,19 en personas pequeñas) | Ubicar cámaras más cerca de las zonas clave; prueba en sitio antes de vender | Medido en laboratorio; validar en piloto |
| Detección errónea de un instante | Falso aviso | Tiempo de confirmación (2 s por defecto) | Implementado |
| Persona que se queda en la zona | Avisos repetidos | Espera entre avisos por regla | Implementado |
| Cámara desconectada | Zona sin vigilancia | Reconexión automática; la cámara aparece "fuera de línea" | Implementado |
| Baja luz o noche | Menos detecciones | Cámaras con infrarrojo; prueba nocturna en la visita | Validar en piloto |
| Reflejos, pósters, maniquíes | Falsos positivos | Ajustar zonas; el operador marca falsas alarmas | Validar en piloto |
| Varias personas juntas | Conteo de aforo incorrecto | ByteTrack; confirmación en aforo | Validar en piloto |
| Cámara movida | Las zonas dejan de coincidir | Editar las zonas sobre la imagen en vivo (mover el recuadro y ajustar sus esquinas); revisión mensual | Implementado |

**En el piloto se medirá:** falsas alarmas por hora en condiciones normales y adversas, tiempo de recuperación tras una desconexión y estabilidad del seguimiento.

---

## P. Estado del prototipo (noviembre de 2026)

Lo que se puede demostrar hoy:

- Inicio de sesión con roles; cada restaurante ve solo sus datos.
- Registro de cámaras RTSP y **vista en vivo** con las detecciones dibujadas, a unas 5 imágenes analizadas por segundo por cámara. Probado con cámaras simuladas, un celular Android como cámara IP y un iPhone cuya dirección de video se obtuvo por ONVIF con usuario y contraseña.
- Zonas dibujadas sobre la imagen en vivo, que se pueden **editar** (mover, ajustar esquinas, renombrar) y **eliminar** con confirmación.
- **Editor de reglas** por zona: tipo, tiempos, gravedad, espera entre avisos, horario, pausar y reanudar.
- Estado de cada zona en vivo con **cuenta regresiva**.
- Centro de alertas con la **foto del momento**, flujo de revisión (revisada, resuelta, falsa alarma) y depuración del historial.
- **Avisos reales por Telegram** con la foto de la alerta (verificado con un bot real); WhatsApp en modo prueba.
- Pruebas automatizadas: **133** (47 del motor de visión y 86 de la API), incluido un entrenamiento real de una época en CPU, la lectura de un video con detección y alerta, y el envío simulado por Telegram.

**Pendiente:** piloto en un restaurante real, envío real por WhatsApp, separar el lector de cámaras como equipo en el restaurante, borrado automático programado de fotos, cifrado, auditoría y el cupo de avisos de WhatsApp.

---

## Q. Equipo

| Integrante | Rol | Responsabilidad |
|---|---|---|
| Wilson Sebastián Moreno Sánchez | Técnico | Inteligencia artificial, reglas de avisos y conexión con Telegram y WhatsApp |
| Michael Stevent Chavarro Nope | Producto y mercado | Pruebas piloto y validación del precio |
| Paula Selene Becerra Morales | Diseño, demo y pitch | Prototipo, demo en vivo y video de respaldo |

---

## Referencias

1. Valora Analitik, "Ventas de restaurantes mejoraron, pero aún hay retos" (cifras de Acoga, 2025). valoraanalitik.com
2. Cambio, entrevista al presidente de Acodres sobre inseguridad en restaurantes (2024). cambiocolombia.com
3. JFM Technology (Colombia), fichas de producto Hikvision. jfmtechnology.com
4. Mercado Libre Colombia, listado "cámara IP Hikvision PoE". electronica.mercadolibre.com.co
5. RFP.wiki (Coram AI vs. Eagle Eye) y FitGap (Coram AI): estimaciones de terceros, no listas oficiales. rfp.wiki
6. Meta, Pricing on the WhatsApp Business Platform. developers.facebook.com
7. Gallabox, WhatsApp Rate Card (Colombia, utilidad US$0,0009). docs.gallabox.com
8. Ley Estatutaria 1581 de 2012 (Función Pública). funcionpublica.gov.co
9. Asuntos Legales, caso SIC sobre recolección forzada de biometría. asuntoslegales.com.co
10. Asuntos Legales, guía SIC de datos personales en videovigilancia. asuntoslegales.com.co
11. Redmon, J., Divvala, S., Girshick, R. y Farhadi, A. (2016). "You Only Look Once: Unified, Real-Time Object Detection". CVPR 2016.
12. Lin, T.-Y. et al. (2014). "Microsoft COCO: Common Objects in Context". ECCV 2014.
13. Bochkovskiy, A., Wang, C.-Y. y Liao, H.-Y. M. (2020). "YOLOv4: Optimal Speed and Accuracy of Object Detection". arXiv:2004.10934.
14. Deci AI (2023). YOLO-NAS, repositorio Deci-AI/super-gradients; licencia de los pesos en `LICENSE.YOLONAS.md`. github.com
15. Roboflow (2025). RF-DETR, repositorio roboflow/rf-detr (Apache-2.0 para Nano, Small y Medium). github.com
16. Buslaev, A. et al. (2020). "Albumentations: Fast and Flexible Image Augmentations". Information, 11(2), 125.
17. Jocher, G., Chaurasia, A. y Qiu, J. (2023). Ultralytics YOLOv8. github.com/ultralytics
18. Holori, precio de Google Cloud e2-standard-8 en us-central1 (US$0,268 por hora bajo demanda; agregador de precios, consultado en noviembre de 2026). calculator.holori.com
19. Computell Technology (Colombia), portátil Onix con Ryzen 7 5700U a $2.130.000 (consultado en noviembre de 2026). computelltechnology.tiendana.com
20. Zhang, Y. et al. (2022). "ByteTrack: Multi-Object Tracking by Associating Every Detection Box". ECCV 2022.
21. Telegram, Bot API y preguntas frecuentes para desarrolladores de bots (uso de la API sin costo por mensaje; límites de frecuencia). core.telegram.org/bots

---

## Anexo: correspondencia con las observaciones del jurado

| # | Observación | Sección | Cómo se respondió |
|---|---|---|---|
| 1 | Arquitectura en la nube | D | Componentes y flujo; procesamiento en el restaurante y plataforma en la nube, justificado con costos |
| 2 | Costos detallados | L | Costos por restaurante con fuentes y supuestos explícitos |
| 3 | Selección de YOLO y licencias | G | 6 modelos con licencia de código y de pesos; corrección sobre YOLO-NAS |
| 4 | Transfer Learning | H, I | Protocolo diseñado y ejecutado, con resultado medido |
| 5 | Datasets | H | COCO val2017, 2.000 imágenes; datos públicos, no recopilados por el equipo |
| 6 | Estado del arte | I | Cifras publicadas con su benchmark |
| 7 | Comparación de modelos | I | 7 configuraciones medidas con el mismo método |
| 8 | Protocolo de evaluación | J | Metas de laboratorio y de piloto, y procedimiento del piloto |
| 9 | Coherencia de los avisos | K | Reglas, tiempos, espera entre avisos y justificación de 300 avisos al mes |
| 10 | Falsos positivos | K, O | Confirmación, horarios, espera entre avisos y revisión humana |
| 11 | Robustez | O | Escenarios, mitigación y estado |
| 12 | Reconocimiento facial | M | Fase futura, solo empleados, con análisis de la Ley 1581 |
| 13 | Protección de datos | N | Medidas implementadas y pendientes |
| 14 | Requisitos de WhatsApp | K, L | Requisitos de Meta para WhatsApp; Telegram agregado como canal sin costo por mensaje, ya funcionando |
| 15 | Viabilidad económica | L | Escenarios con 1, 10 y 50 restaurantes para cada canal de aviso |
