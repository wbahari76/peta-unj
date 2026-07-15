"""Modul pembangun peta Folium untuk Peta Digital UNJ."""

from __future__ import annotations

import folium
from folium import plugins
import pandas as pd

from modules.utils import drive_thumb_url, drive_thumb_url_fallback


# ── Konfigurasi Warna & Ikon Per Kategori Gedung ─────────────────────────────

KATEGORI_CONFIG: dict[str, dict] = {
    "Akademik":               {"color": "#2F6FED", "icon": "graduation-cap", "prefix": "fa"},
    "Administrasi & Layanan": {"color": "#8B5CF6", "icon": "building",        "prefix": "fa"},
    "Fasilitas Umum":         {"color": "#12B5B0", "icon": "cutlery",         "prefix": "fa"},
    "Kesehatan & Keamanan":   {"color": "#2E9E5B", "icon": "medkit",          "prefix": "fa"},
    "Parkir":                 {"color": "#D9973B", "icon": "car",             "prefix": "fa"},
}

_FOLIUM_ICON_COLOR_MAP = {
    "#2F6FED": "blue", "#8B5CF6": "purple", "#12B5B0": "cadetblue",
    "#2E9E5B": "green", "#D9973B": "orange",
}

DEFAULT_CENTER = (-6.1948, 106.8785)
DEFAULT_ZOOM = 17


TILE_LAYERS = {
    "Standar (OpenStreetMap)": {
        "tiles": "OpenStreetMap",
        "attr": "© OpenStreetMap contributors",
    },
    "Minimalis (CartoDB)": {
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attr": "© OpenStreetMap contributors © CARTO",
        "name": "CartoDB Dark",
    },
    "Satelit (Esri)": {
        "tiles": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, …",
        "name": "Esri Satellite",
    },
}


def _build_popup(row: pd.Series, fasilitas_df: pd.DataFrame | None) -> folium.Popup:
    """Bangun popup HTML kaya untuk satu gedung, termasuk tombol rute langsung."""
    cfg = KATEGORI_CONFIG.get(row.get("kategori", ""), {"color": "#555"})
    badge_bg = cfg["color"]

    fas_html = ""
    if fasilitas_df is not None and not fasilitas_df.empty:
        chips = []
        for _, fr in fasilitas_df.head(5).iterrows():
            f_photo = drive_thumb_url(fr.get("foto_id"), size=240)
            f_fallback = drive_thumb_url_fallback(fr.get("foto_id"))
            if f_photo:
                avatar = (
                    f'<img src="{f_photo}" loading="lazy" referrerpolicy="no-referrer" '
                    'style="width:64px;height:64px;border-radius:9px;object-fit:cover;'
                    'flex-shrink:0;border:1px solid #2A4570;" '
                    f'onerror="this.onerror=null;this.src=\'{f_fallback}\';'
                    "this.onerror=function(){this.style.display='none';this.nextElementSibling.style.display='flex';};\" />"
                    '<div style="display:none;width:64px;height:64px;border-radius:9px;background:#1F3A5F;'
                    'flex-shrink:0;align-items:center;justify-content:center;font-size:24px;">🧩</div>'
                )
            else:
                avatar = (
                    '<div style="width:64px;height:64px;border-radius:9px;background:#1F3A5F;'
                    'flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:24px;">🧩</div>'
                )
            chips.append(
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                f'{avatar}<span style="font-size:13px;color:#D6E2F5;line-height:1.35;">{fr["nama_fasilitas"]}</span></div>'
            )
        more = ""
        if len(fasilitas_df) > 5:
            more = f"<div style='color:#8FA3BF;font-size:10.5px;margin-top:2px;'>+{len(fasilitas_df)-5} fasilitas lainnya</div>"
        fas_html = f"""
        <div style="border-top:1px solid #1F3A5F;margin-top:8px;padding-top:8px;">
          <div style="font-size:10.5px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
                      color:#C98A2C;margin-bottom:6px;">🏷 Fasilitas Terkait</div>
          {''.join(chips)}
          {more}
        </div>"""

    jam_html = ""
    if row.get("jam_operasional") and row["jam_operasional"] != "-":
        jam_html = f"""
        <div style="display:flex;align-items:center;gap:5px;margin-top:6px;color:#aaa;font-size:11px;">
          <span>🕐</span><span>{row['jam_operasional']}</span>
        </div>"""

    fakultas_html = ""
    if row.get("fakultas_unit") and row["fakultas_unit"] not in ("", "-"):
        fakultas_html = f"""
        <div style="display:flex;align-items:center;gap:5px;color:#aaa;font-size:11px;margin-top:2px;">
          <span>🏛</span><span>{row['fakultas_unit']}</span>
        </div>"""

    foto_url = drive_thumb_url(row.get("foto_id"), size=900)
    foto_fallback = drive_thumb_url_fallback(row.get("foto_id"))
    foto_html = ""
    if foto_url:
        onerror_js = (
            "this.onerror=null;"
            f"this.src='{foto_fallback}';"
            "this.onerror=function(){this.parentElement.style.display='none';};"
        )
        foto_html = (
            '<div style="width:100%;height:170px;overflow:hidden;background:#0A1628;">'
            f'<img src="{foto_url}" loading="lazy" referrerpolicy="no-referrer" '
            'style="width:100%;height:100%;object-fit:cover;display:block;" '
            f'onerror="{onerror_js}" /></div>'
        )

    html = f"""
    <div style="font-family:'Segoe UI',sans-serif;min-width:280px;max-width:320px;
                background:#111F3A;border-radius:10px;overflow:hidden;color:#E8F0FE;">
      {foto_html}
      <div style="padding:12px;">
        <div style="display:inline-block;padding:3px 8px;border-radius:12px;
                    background:{badge_bg};color:#fff;font-size:10px;
                    font-weight:600;letter-spacing:.5px;text-transform:uppercase;
                    margin-bottom:6px;">
          {row.get('kategori','')}
        </div>
        <h4 style="margin:0 0 6px;font-size:14.5px;font-weight:700;
                   color:#E8F0FE;line-height:1.3;">
          {row['nama_gedung']}
        </h4>
        <p style="margin:0 0 6px;font-size:12px;color:#8FA3BF;line-height:1.5;">
          {str(row.get('deskripsi',''))[:170]}{'…' if len(str(row.get('deskripsi',''))) > 170 else ''}
        </p>
        <div style="border-top:1px solid #1F3A5F;padding-top:8px;">
          {fakultas_html}
          {jam_html}
          <div style="display:flex;align-items:center;gap:5px;color:#aaa;font-size:11px;margin-top:2px;">
            <span>📍</span>
            <span>{row['latitude']:.5f}, {row['longitude']:.5f}</span>
          </div>
        </div>
        {fas_html}
      </div>
    </div>"""
    n_chips = min(len(fasilitas_df), 5) if fasilitas_df is not None else 0
    base_height = 220 + (170 if foto_url else 0) + (n_chips * 72) + (18 if fasilitas_df is not None and len(fasilitas_df) > 5 else 0)
    return folium.Popup(folium.IFrame(html, width=340, height=min(660, base_height)), max_width=350)

def build_map(
    gedung_df: pd.DataFrame,
    fasilitas_df: pd.DataFrame | None = None,
    tile_mode: str = "Standar (OpenStreetMap)",
    route_coords: list[tuple[float, float]] | None = None,
    highlight_ids: list[int] | None = None,
) -> folium.Map:
    """Bangun peta Folium lengkap dengan marker per kategori gedung dan rute."""
    tile_cfg = TILE_LAYERS.get(tile_mode, TILE_LAYERS["Standar (OpenStreetMap)"])
    m = folium.Map(
        location=DEFAULT_CENTER,
        zoom_start=DEFAULT_ZOOM,
        tiles=None,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles=tile_cfg["tiles"],
        attr=tile_cfg.get("attr", ""),
        name=tile_cfg.get("name", tile_mode),
    ).add_to(m)

    feature_groups: dict[str, folium.FeatureGroup] = {}
    for kat in gedung_df["kategori"].unique():
        fg = folium.FeatureGroup(name=f"🏷 {kat}", show=True)
        fg.add_to(m)
        feature_groups[kat] = fg

    highlight_ids = set(highlight_ids or [])
    highlight_coords = []

    for _, row in gedung_df.iterrows():
        kat = row.get("kategori", "Fasilitas Umum")
        cfg = KATEGORI_CONFIG.get(kat, {"color": "#555", "icon": "info-sign", "prefix": "glyphicon"})
        icon_color_name = _FOLIUM_ICON_COLOR_MAP.get(cfg["color"], "gray")

        fas_for_gedung = None
        if fasilitas_df is not None and "id_gedung" in fasilitas_df.columns:
            fas_for_gedung = fasilitas_df[fasilitas_df["id_gedung"] == row["id_gedung"]]

        popup = _build_popup(row, fas_for_gedung)
        tooltip = folium.Tooltip(
            f"<b style='font-family:Segoe UI'>{row['nama_gedung']}</b><br/>"
            f"<small style='color:#aaa'>{kat}</small>",
            sticky=False,
        )

        is_highlighted = row["id_gedung"] in highlight_ids
        if is_highlighted:
            highlight_coords.append((row["latitude"], row["longitude"]))

        icon = folium.Icon(
            color="red" if is_highlighted else icon_color_name,
            icon_color="#fff",
            icon=cfg["icon"],
            prefix=cfg["prefix"],
        )

        marker = folium.Marker(
            location=(row["latitude"], row["longitude"]),
            popup=popup,
            tooltip=tooltip,
            icon=icon,
            z_index_offset=1000 if is_highlighted else 0,
        )
        fg = feature_groups.get(kat)
        if fg:
            marker.add_to(fg)

    # ── Route polyline ────────────────────────────────────────────────────
    if route_coords and len(route_coords) >= 2:
        folium.PolyLine(
            locations=route_coords, color="#C98A2C", weight=5, opacity=0.95,
            tooltip="Jalur terpendek",
        ).add_to(m)
        folium.PolyLine(
            locations=route_coords, color="#E0A94E", weight=10, opacity=0.22,
        ).add_to(m)
        folium.Marker(
            location=route_coords[0],
            icon=folium.Icon(color="green", icon="play", prefix="fa"),
            tooltip="<b>Asal</b>",
        ).add_to(m)
        folium.Marker(
            location=route_coords[-1],
            icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
            tooltip="<b>Tujuan</b>",
        ).add_to(m)
        lats = [c[0] for c in route_coords]
        lons = [c[1] for c in route_coords]
        # Offset kecil ke Utara (max lat) agar rute agak ke bawah, cap di zoom 18
        m.fit_bounds(
            [[min(lats), min(lons)], [max(lats) + 0.0008, max(lons)]],
            max_zoom=18
        )
    elif highlight_coords:
        if len(highlight_coords) == 1:
            lat, lon = highlight_coords[0]
            # Box buatan ke arah Utara agar marker di-push ke bawah, max zoom 18.5
            m.fit_bounds(
                [[lat, lon - 0.0005], [lat + 0.0009, lon + 0.0005]],
                max_zoom=18
            )
        else:
            lats = [c[0] for c in highlight_coords]
            lons = [c[1] for c in highlight_coords]
            m.fit_bounds(
                [[min(lats), min(lons)], [max(lats) + 0.0008, max(lons)]],
                max_zoom=18
            )

    plugins.Fullscreen(position="topright").add_to(m)
    plugins.LocateControl(
        position="topright",
        locateOptions={"enableHighAccuracy": True, "maxZoom": 18},
    ).add_to(m)
    plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)

    return m
