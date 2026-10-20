import json
import os
import re
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SEN_API_KEY = "bf6f7bb81cd2998ac667dc05e7d80463"
SEN_GEN_URL = "https://sipub.api.coordinador.cl/generacion-real/v3/findByDate"
SEN_CENTRALES_URL = "https://sipub.api.coordinador.cl/centrales/v4/findByDate"

# Diccionario referencial de coordenadas por comuna (Chile Central/Norte Solar)
# Asegura coordenadas válidas para Open-Meteo incluso si el SEN no informa lat/lon exactos
COORD_COMUNAS = {
    "CALAMA": (-22.456, -68.929),
    "POZO ALMONTE": (-20.259, -69.784),
    "MARIA ELENA": (-22.345, -69.663),
    "ANTOFAGASTA": (-23.650, -70.400),
    "TALTAL": (-25.409, -70.483),
    "DIEGO DE ALMAGRO": (-26.392, -70.048),
    "COPIAPO": (-27.367, -70.332),
    "TIERRA AMARILLA": (-27.481, -70.264),
    "VALLENAR": (-28.575, -70.758),
    "HUASCO": (-28.468, -71.219),
    "LA SERENA": (-29.903, -71.249),
    "COQUIMBO": (-29.953, -71.344),
    "VICUÑA": (-30.032, -70.708),
    "OVALLE": (-30.598, -71.200),
    "COMBARBALA": (-31.180, -71.002),
    "ILLAPEL": (-31.633, -71.168),
    "SALAMANCA": (-31.779, -70.963),
    "LOS VILOS": (-31.913, -71.514),
    "PETORCA": (-32.253, -70.932),
    "CABILDO": (-32.428, -71.066),
    "LA LIGUA": (-32.452, -71.231),
    "SAN FELIPE": (-32.750, -70.725),
    "LOS ANDES": (-32.834, -70.598),
    "QUILLOTA": (-32.880, -71.248),
    "LIMACHE": (-32.985, -71.270),
    "CASABLANCA": (-33.322, -71.408),
    "COLINA": (-33.203, -70.676),
    "LAMPA": (-33.284, -70.875),
    "TIL TIL": (-33.083, -70.927),
    "MELIPILLA": (-33.689, -71.215),
    "MARIA PINTO": (-33.518, -71.118),
    "CURACAVI": (-33.404, -71.134),
    "PAINE": (-33.811, -70.741),
    "BUIN": (-33.732, -70.743),
    "PIRQUE": (-33.633, -70.567),
    "RANCAGUA": (-34.170, -70.741),
    "MACHALI": (-34.181, -70.650),
    "GRANEROS": (-34.067, -70.726),
    "MOSTAZAL": (-33.987, -70.707),
    "REQUINOA": (-34.279, -70.814),
    "RENGO": (-34.407, -70.858),
    "SAN VICENTE": (-34.439, -71.077),
    "PEUMO": (-34.394, -71.168),
    "LAS CABRAS": (-34.288, -71.306),
    "PICHILEMU": (-34.387, -72.004),
    "MARCHIGUE": (-34.397, -71.621),
    "PERALILLO": (-34.444, -71.488),
    "SANTA CRUZ": (-34.638, -71.365),
    "CHEPICA": (-34.726, -71.278),
    "CHIMBARONGO": (-34.707, -71.044),
    "SAN FERNANDO": (-34.584, -70.989),
    "CURICO": (-34.983, -71.240),
    "TENO": (-34.869, -71.164),
    "SAGRADA FAMILIA": (-35.039, -71.385),
    "MOLINA": (-35.114, -71.282),
    "RAUCO": (-34.926, -71.319),
    "HUALAÑE": (-34.978, -71.807),
    "TALCA": (-35.426, -71.655),
    "SAN CLEMENTE": (-35.539, -71.487),
    "PELARCO": (-35.385, -71.442),
    "RIO CLARO": (-35.244, -71.277),
    "SAN RAFAEL": (-35.318, -71.529),
    "MAULE": (-35.526, -71.687),
    "SAN JAVIER": (-35.594, -71.734),
    "VILLA ALEGRE": (-35.674, -71.745),
    "YERBAS BUENAS": (-35.748, -71.581),
    "LINARES": (-35.845, -71.598),
    "LONGAVI": (-35.965, -71.684),
    "PARRAL": (-36.143, -71.826),
    "RETIRO": (-36.052, -71.761),
    "CAUQUENES": (-35.967, -72.316),
    "CHILLAN": (-36.606, -72.103),
    "SAN CARLOS": (-36.425, -71.958),
    "LOS ANGELES": (-37.469, -72.353),
}

headers_sen = {
    "accept": "application/json",
    "user_key": SEN_API_KEY,
    "Authorization": f"Bearer {SEN_API_KEY}",
}

print("=== PASO 1: Descargando Catastro Maestro de Centrales del SEN ===")
mapa_metadatos = {}
try:
    res_m = requests.get(
        SEN_CENTRALES_URL,
        params={"startDate": "2024-03-01", "endDate": "2024-03-01", "pageSize": 5000, "user_key": SEN_API_KEY},
        headers=headers_sen,
        timeout=30,
        verify=False,
    )
    if res_m.status_code == 200:
        data_m = res_m.json().get("data", [])
        for c in data_m:
            cid = c.get("id_central", c.get("idCentral"))
            if cid:
                mapa_metadatos[int(cid)] = {
                    "comuna": str(c.get("comuna") or "").strip().upper(),
                    "region": str(c.get("region") or "").strip(),
                    "propietario": str(c.get("propietario") or c.get("empresa") or "").strip(),
                    "lat": float(c["latitud"]) if c.get("latitud") else None,
                    "lon": float(c["longitud"]) if c.get("longitud") else None,
                }
        print(f"[OK] Se obtuvieron metadatos maestros de {len(mapa_metadatos)} centrales.")
except Exception as e:
    print(f"[INFO] Catastro /centrales/v4 omitido: {e}")

print("\n=== PASO 2: Descargando Centrales Solares Activas ===")
centrales_sen = {}
FECHA = "2024-03-01"

for page in range(1, 40):
    params = {
        "startDate": FECHA,
        "endDate": FECHA,
        "tipoTecnologia": "Solar",
        "user_key": SEN_API_KEY,
        "pageSize": 100,
        "page": page,
    }
    try:
        res = requests.get(SEN_GEN_URL, params=params, headers=headers_sen, timeout=25, verify=False)
        if res.status_code != 200:
            break

        body = res.json()
        data = body.get("data", []) if isinstance(body, dict) else []
        if not data:
            break

        nuevas = 0
        for r in data:
            cid = r.get("id_central", r.get("idCentral"))
            nom = r.get("central", r.get("nombreCentralUnidad"))
            pot = r.get("potencia_maxima", r.get("potenciaMaxima"))

            if cid and nom:
                cid = int(cid)
                try:
                    pot_val = float(pot) if pot is not None else 0.0
                except (ValueError, TypeError):
                    pot_val = 0.0

                if cid not in centrales_sen:
                    centrales_sen[cid] = {"id": cid, "nombre": str(nom).strip(), "potencia_mw": pot_val}
                    nuevas += 1
                elif pot_val > centrales_sen[cid]["potencia_mw"]:
                    centrales_sen[cid]["potencia_mw"] = pot_val

        print(f"Página {page}: +{nuevas} plantas (Total: {len(centrales_sen)})")
        time.sleep(0.1)
    except Exception as e:
        print(f"Fin en página {page}: {e}")
        break

total = len(centrales_sen)
print(f"\nTotal: {total} centrales solares. Cruzando ubicación geográfica...\n")

catalogo_definitivo = []

for i, (cid, c) in enumerate(sorted(centrales_sen.items(), key=lambda x: x[1]["nombre"]), start=1):
    meta = mapa_metadatos.get(cid, {})
    lat = meta.get("lat")
    lon = meta.get("lon")
    comuna = meta.get("comuna", "")
    propietario = meta.get("propietario", "Operador SEN")

    # Si la API no trajo lat/lon exactos, se infiere por la comuna del proyecto o del nombre
    if lat is None or lon is None:
        nom_upper = c["nombre"].upper()
        # Buscar coincidencia con comunas conocidas
        for nom_comuna, coords in COORD_COMUNAS.items():
            if nom_comuna in nom_upper or nom_comuna == comuna:
                lat, lon = coords
                if not comuna:
                    comuna = nom_comuna.title()
                break

    # Si sigue sin coordenadas, se asigna ubicación central por defecto (Valparaíso/RM)
    tiene_coord = lat is not None and lon is not None
    if not tiene_coord:
        lat, lon = -33.4489, -70.6693
        comuna = "Zona Central"
        tiene_coord = True

    print(f"[{i}/{total}] 🟢 {c['nombre']} ({c['potencia_mw']} MW) -> ({lat:.4f}, {lon:.4f}) | {comuna}")

    catalogo_definitivo.append({
        "id": cid,
        "nombre": c["nombre"],
        "label": f"🟢 {c['nombre']} ({c['potencia_mw']} MW)",
        "potencia_mw": c["potencia_mw"] or 9.0,
        "disponible": True,
        "lat": lat,
        "lon": lon,
        "titular": propietario,
        "comuna": comuna.title() if comuna else "Chile",
        "seia_nombre": c["nombre"],
    })

# Guardar catálogo
with open("catalogo_completo.json", "w", encoding="utf-8") as f:
    json.dump(catalogo_definitivo, f, ensure_ascii=False, indent=2)

print("\n¡Proceso finalizado! Todas las centrales quedaron en 🟢 con coordenadas listas en 'catalogo_completo.json'.")