import json, os, re
import pandas as pd

dfs = []
if os.path.exists("Proyectos.xlsx"):
    dfs.append(pd.read_excel("Proyectos.xlsx"))
if os.path.exists("Proyectos_pmgd.xlsx"):
    dfs.append(pd.read_excel("Proyectos_pmgd.xlsx"))

if not dfs:
    raise FileNotFoundError("No se encontraron Proyectos.xlsx ni Proyectos_pmgd.xlsx")

df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["Nombre del Proyecto"])

def limpiar_coord(val, es_lat=True):
    if pd.isna(val):
        return None
    s = str(val).strip().replace(",", ".")
    try:
        num = float(s)
        if es_lat and -56.0 <= num <= -17.0:
            return round(num, 5)
        if not es_lat and -76.0 <= num <= -66.0:
            return round(num, 5)
    except Exception:
        pass
    return None

catalogo = []
for idx, (_, row) in enumerate(df.iterrows(), start=1):
    nom = str(row["Nombre del Proyecto"]).strip()
    lat = limpiar_coord(row.get("Latitud Punto Representativo"), es_lat=True)
    lon = limpiar_coord(row.get("Longitud Punto Representativo"), es_lat=False)
    if lat is None or lon is None:
        continue

    pot = None
    for col in df.columns:
        if "potencia" in col.lower() or "mw" in col.lower():
            try:
                val_p = float(str(row[col]).replace(",", "."))
                if 0.1 < val_p <= 500:
                    pot = round(val_p, 2)
                    break
            except Exception:
                pass

    if pot is None:
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*MW", nom.upper())
        if m:
            pot = float(m.group(1).replace(",", "."))
        else:
            pot = 9.0 if ("SOLAR" in nom.upper() or "FOTOVOLTAICO" in nom.upper() or "PFV" in nom.upper()) else 3.0

    # Extraer nuevos campos solicitados del Excel
    tipo_presentacion = str(row.get("Tipo de Presentación", row.get("Tipo Presentacion", "DIA")))
    tipo_proyecto = str(row.get("Tipo de Proyecto", row.get("Tipologia", "Parque Fotovoltaico")))
    titular = str(row.get("Titular", "Titular SEA"))
    region = str(row.get("Región", row.get("Region", "Chile")))
    comuna = str(row.get("Comuna", "Chile"))

    catalogo.append({
        "id": idx,
        "nombre": nom,
        "label": f"🟢 {nom} ({pot:.1f} MW)",
        "potencia_mw": pot,
        "disponible": True,
        "lat": lat,
        "lon": lon,
        "tipo_presentacion": tipo_presentacion if tipo_presentacion != "nan" else "DIA",
        "tipo_proyecto": tipo_proyecto if tipo_proyecto != "nan" else "Parque Fotovoltaico",
        "titular": titular if titular != "nan" else "Titular SEA",
        "region": region if region != "nan" else "Chile",
        "comuna": comuna if comuna != "nan" else "Chile"
    })

with open("catalogo_completo.json", "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, indent=2)

print(f"¡Listo! Se guardaron {len(catalogo)} centrales con todos sus metadatos ambientales en catalogo_completo.json")