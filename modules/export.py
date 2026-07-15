"""Modul ekspor data — GeoJSON dan CSV untuk keperluan analitik lanjutan."""

import json
import pandas as pd


def gedung_to_geojson(gedung_df: pd.DataFrame) -> str:
    """Konversi DataFrame gedung ke format GeoJSON FeatureCollection."""
    features = []
    for _, row in gedung_df.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
            "properties": {
                "id_gedung":        int(row["id_gedung"]),
                "nama_gedung":      str(row["nama_gedung"]),
                "kategori":         str(row.get("kategori", "")),
                "fakultas_unit":    str(row.get("fakultas_unit", "")),
                "deskripsi":        str(row.get("deskripsi", "")),
                "jam_operasional":  str(row.get("jam_operasional", "")),
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "name": "Gedung Kampus UNJ",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    return json.dumps(geojson, indent=2, ensure_ascii=False)


def gedung_to_csv_bytes(gedung_df: pd.DataFrame) -> bytes:
    cols = ["id_gedung", "nama_gedung", "kategori", "fakultas_unit", "fungsi",
            "latitude", "longitude", "jam_operasional", "foto_id", "deskripsi"]
    df_export = gedung_df[[c for c in cols if c in gedung_df.columns]].copy()
    return df_export.to_csv(index=False).encode("utf-8")


def fasilitas_to_csv_bytes(fasilitas_df: pd.DataFrame) -> bytes:
    cols = ["id_fasilitas", "nama_fasilitas", "kategori_fasilitas", "unit_pengguna",
            "nama_gedung", "deskripsi"]
    df_export = fasilitas_df[[c for c in cols if c in fasilitas_df.columns]].copy()
    return df_export.to_csv(index=False).encode("utf-8")


def log_to_csv_bytes(log_df: pd.DataFrame) -> bytes:
    return log_df.to_csv(index=False).encode("utf-8")


def geojson_to_bytes(geojson_str: str) -> bytes:
    return geojson_str.encode("utf-8")
