# Monitor Nacional SEN + SEIA

Versión FastAPI del monitor original en Streamlit. Incluye API JSON, dashboard HTML con Plotly y Leaflet, y diseño adaptable a móviles para acceso mediante QR.

## Cambios para los datos y las coordenadas

- La integración del Coordinador reconoce tanto las filas del archivo (`id_central`, `central`, `gen_real_mw`, `fecha_hora`) como el esquema documentado (`idCentral`, `nombreCentralUnidad`, `valor`, `fecha`, `hora`).
- Las respuestas paginadas se leen página por página, incluyendo respuestas con filas dentro de `content`.
- Si una central tiene más de una unidad generadora en la misma hora, sus valores se suman para representar la generación conjunta.
- Los resultados parecidos del SEIA se ofrecen como candidatos. El mapa no usa el primero automáticamente; debes confirmar el proyecto correcto o ingresar latitud/longitud.
- La ubicación elegida queda guardada en el navegador para esa central. Sin ubicación, los datos oficiales del SEN se pueden cargar igual y el mapa queda sin una chincheta inventada.
- Los errores de autenticación y de conexión del Coordinador se muestran en la interfaz en vez de ocultarse como una estimación.
- El período inicial es 01-01-2021 a 31-03-2025 (verano austral hasta fines de marzo); las fechas se pueden cambiar en el panel.
- Para rangos extensos, SEN y Open-Meteo se consultan en bloques de hasta 90 días para evitar respuestas demasiado grandes y respetar la paginación.
- El gráfico histórico resume la generación por día para que el período completo se pueda explorar en móvil; los registros horarios se conservan en la tabla.
- Las respuestas SEN quedan en caché por 24 horas para evitar repetir decenas de consultas cuando varias personas abren el mismo tablero.

## Requisitos

Python 3.10 o superior.

## Ejecutar localmente

```bash
cd sen_seia_dashboard
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://127.0.0.1:8000`. La documentación de la API está en `http://127.0.0.1:8000/docs`.

La plataforma toma la API key desde el backend; las personas que la visitan no tienen que ingresarla. Para pegarla en el código, abre `main.py` y reemplaza `PEGA_AQUI_TU_API_KEY` en esta línea:

```python
SEN_API_KEY = os.getenv("SEN_API_KEY", "PEGA_AQUI_TU_API_KEY").strip()
```

La alternativa recomendada para Render es definir `SEN_API_KEY` en **Environment Variables**. La clave nunca se envía al HTML ni al navegador. Si el repositorio es público, usa la variable de entorno en lugar de escribir la clave en el código.

Las llamadas al Coordinador siguen el conector probado de Streamlit: `user_key`, `pageSize=10000`, encabezado `accept: application/json` y sin enviar `page` en la primera solicitud. El catálogo consulta la fecha de 15 días atrás; los datos operativos consultan el período elegido en bloques de hasta 90 días. Para compatibilidad con esa conexión, la verificación TLS está desactivada únicamente para el endpoint SEN.

## Render

Crea un servicio **Web Service** conectado al repositorio:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment:** `SEN_API_KEY` (valor secreto; preferido)

Render asigna una URL pública HTTPS. Esa URL se puede usar para generar el QR. Al abrirla desde el celular, la interfaz adapta controles, gráficos, mapa y tabla al ancho disponible.

## Endpoints

- `GET /api/health`: estado del servicio.
- `POST /api/catalogo`: catálogo solar del Coordinador (usa la clave guardada en el servidor).
- `POST /api/dashboard`: metadatos SEIA, clima Open-Meteo, generación SEN o estimación satelital.
- `GET /docs`: documentación interactiva OpenAPI.

La app conserva el factor de emisión y otros criterios del código original. El Coordinador describe generación real como potencia en MW, aunque algunas respuestas identifican la unidad como MWh; antes de usar totales en informes o balances de emisiones, valida la unidad y granularidad de tu cuenta y endpoint.
