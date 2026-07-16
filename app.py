import os
import uuid
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
try:
    from streamlit_js_eval import get_geolocation
    _GPS_AVAILABLE = True
except ImportError:
    _GPS_AVAILABLE = False
from modules import db, map_builder, routing, analytics, export
from modules.utils import drive_thumb_url
APP_TITLE = 'Peta Digital UNJ'
APP_ICON = '🗺'
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout='wide', initial_sidebar_state='auto')
CSS_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'style.css')
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
if 'sesi_id' not in st.session_state:
    st.session_state.sesi_id = str(uuid.uuid4())[:8]
if 'route_result' not in st.session_state:
    st.session_state.route_result = None
if 'last_map_click' not in st.session_state:
    st.session_state.last_map_click = None
if 'gps_coords' not in st.session_state:
    st.session_state.gps_coords = None
if 'popup_action' not in st.session_state:
    st.session_state.popup_action = None
if 'selected_building' not in st.session_state:
    st.session_state.selected_building = None
if 'do_scroll' not in st.session_state:
    st.session_state.do_scroll = 0
_CAMPUS_LAT = (-6.1985, -6.191)
_CAMPUS_LON = (106.8745, -6.883)

def _is_near_campus(lat: float, lon: float, radius_m: float=800) -> bool:
    import math
    clat = (-6.1972 + -6.1923) / 2
    clon = (106.8762 + 106.8815) / 2
    dlat = math.radians(lat - clat)
    dlon = math.radians(lon - clon)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(clat)) * math.cos(math.radians(lat)) * math.sin(dlon / 2) ** 2
    dist = 2 * 6371000 * math.asin(math.sqrt(a))
    return dist <= radius_m
GPS_OPTION_LABEL = '📍 Lokasi Saya (GPS)'

@st.cache_resource
def get_conn():
    return db.get_connection()

@st.cache_resource
def get_osm_network():
    return routing.load_osm_network()

@st.cache_data(ttl=15)
def load_gedung(_conn):
    return db.get_all_gedung(_conn)

@st.cache_data(ttl=15)
def load_routing_gedung(_conn):
    return db.get_all_gedung_for_routing(_conn)

@st.cache_data(ttl=15)
def load_fasilitas(_conn):
    return db.get_all_fasilitas(_conn)

@st.cache_data(ttl=15)
def load_edges(_conn):
    return db.get_all_edges(_conn)

def clear_data_cache():
    load_gedung.clear()
    load_routing_gedung.clear()
    load_fasilitas.clear()
    load_edges.clear()
conn = get_conn()
db.ensure_session(conn, st.session_state.sesi_id)
_header_stats = db.get_total_stats(conn)
st.markdown(f"""\n    <div class="app-header">\n      <div class="app-header-bg"></div>\n      <div class="app-header-left">\n        <div class="app-header-icon">🗺</div>\n        <div>\n          <div class="app-title">{APP_TITLE}</div>\n          <div class="app-subtitle">\n            Sistem Informasi Geografis Kampus Universitas Negeri Jakarta\n          </div>\n        </div>\n      </div>\n      <div class="app-header-right">\n        <div class="stat-chip">\n          <div class="stat-chip-num">{_header_stats['total_gedung']}</div>\n          <div class="stat-chip-label">📍 Gedung</div>\n        </div>\n        <div class="stat-chip">\n          <div class="stat-chip-num">{_header_stats['total_fasilitas']}</div>\n          <div class="stat-chip-label">🧩 Fasilitas</div>\n        </div>\n        <div class="stat-chip">\n          <div class="stat-chip-num">{_header_stats['total_rute']}</div>\n          <div class="stat-chip-label">🧭 Jalur Rute</div>\n        </div>\n      </div>\n    </div>\n    """, unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div style="text-align:center;padding-bottom:0.75rem;"><div style="font-size:2rem;">🏛</div><div style="font-size:1rem;font-weight:700;color:#E8F0FE;">Peta Digital UNJ</div><div style="font-size:0.7rem;color:#6A82A8;">Navigasi Kampus Interaktif</div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="sidebar-section">🏷 Filter Kategori</div>', unsafe_allow_html=True)
    all_kat = db.get_semua_kategori_gedung(conn)
    selected_kat = st.multiselect('Tampilkan kategori:', options=all_kat, default=[], label_visibility='collapsed')
    st.markdown('<div class="sidebar-section">🔍 Pencarian Lokasi</div>', unsafe_allow_html=True)
    search_query = st.text_input('Cari nama gedung, fasilitas, atau deskripsi:', placeholder='Contoh: rektorat, kantin, parkir...', label_visibility='collapsed')
    if search_query != st.session_state.get('last_search_query', ''):
        st.session_state.last_search_query = search_query
        import time
        st.session_state.do_scroll = time.time()
    st.markdown('<div class="sidebar-section">🗾 Tampilan Peta</div>', unsafe_allow_html=True)
    tile_mode = st.selectbox('Tile layer:', options=list(map_builder.TILE_LAYERS.keys()), index=0, label_visibility='collapsed')
    st.markdown('<div class="sidebar-section">🧭 Pencarian Rute</div>', unsafe_allow_html=True)
    _osm_active = get_osm_network() is not None
    if _osm_active:
        st.markdown('<div style="font-size:0.72rem;color:#4CD9C0;margin-bottom:6px;">🛰️ Mode OSM aktif — rute mengikuti jalan/trotoar asli</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:0.72rem;color:#8FA3BF;margin-bottom:6px;">🧩 Mode waypoint offline (jalankan <code>database/build_network.py</code> untuk rute presisi jalan asli)</div>', unsafe_allow_html=True)
    gedung_all = load_gedung(conn)
    fasilitas_all = load_fasilitas(conn)
    edges_all = load_edges(conn)
    nama_gedung = gedung_all['nama_gedung'].tolist()

    def nama_to_id(nama: str):
        row = gedung_all[gedung_all['nama_gedung'] == nama]
        return int(row.iloc[0]['id_gedung']) if not row.empty else -1
    if _GPS_AVAILABLE:
        col_gps1, col_gps2 = st.columns([3, 2])
        with col_gps1:
            gps_clicked = st.button('📍 Pakai Lokasi Saya (GPS)', width='stretch')
        with col_gps2:
            if st.session_state.gps_coords:
                st.caption('🟢 GPS aktif')
        if gps_clicked:
            st.session_state.gps_fetch_attempt = st.session_state.get('gps_fetch_attempt', 0) + 1
        if st.session_state.get('gps_fetch_attempt', 0) > 0:
            loc = get_geolocation(component_key=f'geoloc_{st.session_state.gps_fetch_attempt}')
            if loc and loc.get('coords'):
                new_coords = (loc['coords']['latitude'], loc['coords']['longitude'])
                if new_coords != st.session_state.gps_coords:
                    st.session_state.gps_coords = new_coords
                    st.session_state.route_asal = GPS_OPTION_LABEL
                    st.rerun()
            elif gps_clicked:
                st.caption('⏳ Meminta izin lokasi di browser... klik lagi jika belum muncul.')
    else:
        st.caption('Install `streamlit-js-eval` untuk pakai lokasi GPS langsung.')
    asal_options = ['— pilih —']
    if st.session_state.gps_coords:
        asal_options.append(GPS_OPTION_LABEL)
    asal_options += nama_gedung
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        asal_nama = st.selectbox('Asal:', options=asal_options, key='route_asal')
    with col_r2:
        tujuan_nama = st.selectbox('Tujuan:', options=['— pilih —'] + nama_gedung, key='route_tujuan')
    btn_rute = st.button('🔀 Cari Rute', width='stretch')
    if btn_rute:
        if asal_nama == '— pilih —' or tujuan_nama == '— pilih —':
            st.warning('Pilih lokasi asal dan tujuan terlebih dahulu.')
        elif asal_nama == tujuan_nama:
            st.warning('Asal dan tujuan tidak boleh sama.')
        else:
            asal_is_gps = asal_nama == GPS_OPTION_LABEL
            tujuan_id = nama_to_id(tujuan_nama)
            tujuan_row = gedung_all[gedung_all['id_gedung'] == tujuan_id].iloc[0]
            if asal_is_gps:
                asal_lat, asal_lon = st.session_state.gps_coords
                if not _is_near_campus(asal_lat, asal_lon, radius_m=3000):
                    st.warning(f'⚠️ GPS kamu terdeteksi jauh dari kampus UNJ ({asal_lat:.4f}, {asal_lon:.4f} — sekitar {routing._haversine(asal_lat, asal_lon, -6.1948, 106.8785) / 1000:.1f} km). Rute ditampilkan dari pintu masuk kampus.')
                    asal_lat, asal_lon = (-6.1948, 106.8785)
            else:
                asal_id = nama_to_id(asal_nama)
                asal_row = gedung_all[gedung_all['id_gedung'] == asal_id].iloc[0]
                asal_lat, asal_lon = (asal_row['latitude'], asal_row['longitude'])
            osm_graph = get_osm_network()
            if osm_graph is not None:
                path_coords, jarak = routing.find_shortest_path_osm(osm_graph, asal_lat, asal_lon, tujuan_row['latitude'], tujuan_row['longitude'])
                path_names = [asal_nama, tujuan_nama]
            elif asal_is_gps:
                routing_gedung_all = load_routing_gedung(conn)
                G = routing.build_graph(edges_all, routing_gedung_all)
                nearest_node = routing.nearest_graph_node(G, asal_lat, asal_lon)
                path_coords, path_nodes, jarak = routing.find_shortest_path(G, nearest_node, tujuan_id)
                if path_coords:
                    path_coords = [(asal_lat, asal_lon)] + path_coords
                path_names = [G.nodes[n]['nama'] for n in path_nodes if not str(G.nodes[n]['nama']).startswith('WP_')] if path_coords else []
                if path_names:
                    path_names = [asal_nama] + path_names
            else:
                asal_id = nama_to_id(asal_nama)
                routing_gedung_all = load_routing_gedung(conn)
                G = routing.build_graph(edges_all, routing_gedung_all)
                path_coords, path_nodes, jarak = routing.find_shortest_path(G, asal_id, tujuan_id)
                path_names = [G.nodes[n]['nama'] for n in path_nodes if not str(G.nodes[n]['nama']).startswith('WP_')] if path_coords else []
            if path_coords:
                waktu = routing.calculate_walking_time(jarak)
                result = {'path_coords': path_coords, 'path_names': path_names, 'jarak_meter': jarak, 'waktu_menit': waktu}
                st.session_state.route_result = result
                import time
                st.session_state.do_scroll = time.time()
                db.insert_log(conn, 'route', st.session_state.sesi_id, detail={'asal': asal_nama, 'tujuan': tujuan_nama, 'jarak': jarak})
            else:
                st.error('Rute tidak ditemukan antara kedua lokasi tersebut.')
                st.session_state.route_result = None
    if st.button('✖ Reset Rute', width='stretch'):
        st.session_state.route_result = None
    if st.session_state.route_result:
        r = st.session_state.route_result
        st.markdown(f"""\n            <div class="route-card">\n              <div class="route-title">📍 Jalur Terpendek</div>\n              <div class="route-stat">🛣 {r['jarak_meter']:,.0f} meter</div>\n              <div class="route-stat">🚶 ~{r['waktu_menit']} menit berjalan kaki</div>\n              <div style="margin-top:8px;font-size:0.72rem;color:#8FA3BF;font-weight:600;\n                          letter-spacing:.5px;text-transform:uppercase;margin-bottom:4px;">\n                Jalur:\n              </div>\n              {''.join((f'<div class="route-path-item">{n}</div>' for n in r['path_names']))}\n            </div>\n            """, unsafe_allow_html=True)
    st.divider()
    st.markdown('<div style="font-size:0.68rem;color:#3A5278;text-align:center;line-height:1.6;">Data koordinat berdasarkan pemetaan kampus UNJ Rawamangun.<br/>', unsafe_allow_html=True)
tab_peta, tab_dashboard, tab_data = st.tabs(['🗺  Peta Interaktif', '📊  Dashboard Analitik', '📋  Data & Ekspor'])
with tab_peta:
    if selected_kat:
        display_df = gedung_all[gedung_all['kategori'].isin(selected_kat)]
    else:
        display_df = gedung_all.iloc[0:0]
        st.info('🏷 Pilih kategori di sidebar untuk menampilkan gedung di peta.')
    highlight_ids = []
    if search_query.strip():
        sq = search_query.strip().lower()
        mask_gedung = gedung_all['nama_gedung'].str.lower().str.contains(sq, na=False) | gedung_all['deskripsi'].str.lower().str.contains(sq, na=False) | gedung_all['kategori'].str.lower().str.contains(sq, na=False) | gedung_all['fakultas_unit'].str.lower().str.contains(sq, na=False)
        matched = gedung_all[mask_gedung]
        fas_mask = fasilitas_all['nama_fasilitas'].str.lower().str.contains(sq, na=False)
        fas_matched_gedung_ids = fasilitas_all.loc[fas_mask, 'id_gedung'].dropna().unique().tolist()
        extra_matched = gedung_all[gedung_all['id_gedung'].isin(fas_matched_gedung_ids)]
        matched = pd.concat([matched, extra_matched]).drop_duplicates(subset='id_gedung')
        highlight_ids = matched['id_gedung'].tolist()
        if not matched.empty:
            display_df = pd.concat([display_df, matched]).drop_duplicates(subset='id_gedung')
            db.insert_log(conn, 'search', st.session_state.sesi_id, detail={'query': search_query, 'results': len(matched)})
        if highlight_ids:
            badges = ' '.join((f'<span class="search-badge">📍 {n}</span>' for n in matched['nama_gedung'].head(6)))
            extra = f'<span class="search-badge">+{len(highlight_ids) - 6} lainnya</span>' if len(highlight_ids) > 6 else ''
            st.markdown(f'<div style="padding:0.4rem 0;margin-bottom:0.5rem;">🔍 Ditemukan <b style="color:#3FE0D8">{len(highlight_ids)}</b> lokasi: {badges}{extra}</div>', unsafe_allow_html=True)
        else:
            st.info(f'Tidak ada lokasi yang cocok dengan "{search_query}".')
    if selected_kat and len(selected_kat) < len(all_kat):
        db.insert_log(conn, 'filter', st.session_state.sesi_id, detail={'kategori': selected_kat})
    route_coords = None
    if st.session_state.route_result:
        route_coords = st.session_state.route_result['path_coords']
    st.markdown('<div id="map-target" style="position:relative; top:-60px;"></div>', unsafe_allow_html=True)
    if st.session_state.get('do_scroll', 0) > 0:
        import streamlit.components.v1 as components
        components.html(f"\n            <script>\n                // Render ID: {st.session_state.do_scroll}\n                // Tunggu sebentar sampai peta dirender, lalu scroll parent window ke peta\n                setTimeout(function() {{\n                    const target = window.parent.document.getElementById('map-target');\n                    if(target) {{\n                        target.scrollIntoView({{behavior: 'smooth', block: 'start'}});\n                    }}\n                }}, 300);\n            </script>\n            ", height=0, width=0)
    folium_map = map_builder.build_map(gedung_df=display_df, fasilitas_df=fasilitas_all, tile_mode=tile_mode, route_coords=route_coords, highlight_ids=highlight_ids)
    map_data = st_folium(folium_map, width='stretch', height=600, returned_objects=['last_object_clicked_tooltip', 'last_clicked'], key='main_map')
    if map_data and map_data.get('last_object_clicked_tooltip'):
        tooltip_text = map_data['last_object_clicked_tooltip']
        if tooltip_text != st.session_state.last_map_click:
            st.session_state.last_map_click = tooltip_text
            nama_klik = tooltip_text.split('<br')[0].replace("<b style='font-family:Segoe UI'>", '').replace('</b>', '').strip()
            row = gedung_all[gedung_all['nama_gedung'].str.startswith(nama_klik)]
            gid = int(row.iloc[0]['id_gedung']) if not row.empty else None
            db.insert_log(conn, 'view_marker', st.session_state.sesi_id, id_gedung=gid, detail={'tooltip': tooltip_text[:80]})
            if not row.empty:
                nama_lengkap = row.iloc[0]['nama_gedung']
                st.session_state.selected_building = nama_lengkap
                st.session_state.route_tujuan = nama_lengkap
                st.rerun()
    if st.session_state.selected_building:
        bname = st.session_state.selected_building
        st.markdown(f'<div style="background:linear-gradient(135deg,#111F3A,#1A2F50);border:1px solid #2A4570;border-radius:12px;padding:12px 16px;margin-top:8px;display:flex;align-items:center;justify-content:space-between;"><span style="color:#E8F0FE;font-weight:700;font-size:14px;">🏛 {bname}</span><span style="color:#8FA3BF;font-size:12px;">Klik tombol di bawah untuk navigasi</span></div>', unsafe_allow_html=True)
        col_nav_a, col_nav_b = st.columns([4, 1])
        with col_nav_a:
            if st.button(f'🧭 Navigasi ke {bname} dari GPS saya', key='btn_nav_popup', type='primary', width='stretch'):
                if not st.session_state.gps_coords:
                    st.warning("📍 Aktifkan GPS dulu: klik '📍 Pakai Lokasi Saya (GPS)' di sidebar kiri.")
                else:
                    asal_lat, asal_lon = st.session_state.gps_coords
                    if not _is_near_campus(asal_lat, asal_lon, radius_m=3000):
                        st.warning(f'⚠️ GPS kamu terdeteksi jauh dari kampus UNJ ({asal_lat:.4f}, {asal_lon:.4f}). Rute akan dihitung dari pintu masuk kampus terdekat.')
                        asal_lat, asal_lon = (-6.1948, 106.8785)
                    tujuan_id = nama_to_id(bname)
                    tujuan_row = gedung_all[gedung_all['id_gedung'] == tujuan_id].iloc[0]
                    osm_graph = get_osm_network()
                    if osm_graph is not None:
                        path_coords, jarak = routing.find_shortest_path_osm(osm_graph, asal_lat, asal_lon, tujuan_row['latitude'], tujuan_row['longitude'])
                        path_names = ['📍 Lokasi Saya', bname]
                    else:
                        routing_gedung_all = load_routing_gedung(conn)
                        G = routing.build_graph(edges_all, routing_gedung_all)
                        nearest_node = routing.nearest_graph_node(G, asal_lat, asal_lon)
                        path_coords, path_nodes, jarak = routing.find_shortest_path(G, nearest_node, tujuan_id)
                        if path_coords:
                            path_coords = [(asal_lat, asal_lon)] + path_coords
                        path_names = [G.nodes[n]['nama'] for n in path_nodes or [] if not str(G.nodes[n]['nama']).startswith('WP_')]
                        if path_names:
                            path_names = ['📍 Lokasi Saya'] + path_names
                    if path_coords:
                        waktu = routing.calculate_walking_time(jarak)
                        st.session_state.route_result = {'path_coords': path_coords, 'path_names': path_names, 'jarak_meter': jarak, 'waktu_menit': waktu}
                        st.session_state.route_asal = GPS_OPTION_LABEL
                        db.insert_log(conn, 'route', st.session_state.sesi_id, detail={'asal': 'GPS', 'tujuan': bname, 'jarak': jarak})
                        st.toast(f'🧭 Rute ditemukan! {jarak:.0f}m, ~{routing.calculate_walking_time(jarak):.0f} menit', icon='🧭')
                    else:
                        st.error('Rute tidak ditemukan. Coba pilih lokasi asal manual di sidebar.')
                    st.rerun()
        with col_nav_b:
            if st.button('✖ Tutup', key='btn_clear_sel', width='stretch'):
                st.session_state.selected_building = None
                st.rerun()
    total_shown = len(display_df)
    st.markdown(f"""<div class="map-stats-bar"><span>📍 <b style="color:#E8F0FE">{total_shown}</b> gedung ditampilkan</span><span>🏷 <b style="color:#E8F0FE">{len(selected_kat)}</b> kategori aktif</span><span>🧭 Rute: <b style="color:#E8F0FE">{('Aktif' if route_coords else 'Tidak aktif')}</b></span></div>""", unsafe_allow_html=True)
with tab_dashboard:
    @st.fragment(run_every=10)
    def _dashboard_realtime():
        _conn = get_conn()
        stats = db.get_total_stats(_conn)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="metric-card teal"><span class="metric-icon">📍</span><div class="metric-value">{stats['total_gedung']}</div><div class="metric-label">Total Gedung</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-card gold"><span class="metric-icon">🧩</span><div class="metric-value">{stats['total_fasilitas']}</div><div class="metric-label">Fasilitas</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card purple"><span class="metric-icon">🧭</span><div class="metric-value">{stats['total_rute']}</div><div class="metric-label">Jalur Rute</div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="metric-card green"><span class="metric-icon">📊</span><div class="metric-value">{stats['total_log']}</div><div class="metric-label">Total Aktivitas</div></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            kat_visit = db.get_kategori_visit_count(_conn)
            st.plotly_chart(analytics.chart_kategori_terpopuler(kat_visit), width='stretch', config={'displayModeBar': False})
        with col_b:
            dist_df = db.get_aksi_distribution(_conn)
            st.plotly_chart(analytics.chart_distribusi_aksi(dist_df), width='stretch', config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        tren_df = db.get_aksi_trend(_conn)
        st.plotly_chart(analytics.chart_tren_pencarian(tren_df), width='stretch', config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        _gedung_all = load_gedung(_conn)
        _fasilitas_all = load_fasilitas(_conn)
        col_c, col_d = st.columns([3, 2])
        with col_c:
            fig_scatter = analytics.chart_heatmap_lokasi(_gedung_all)
            st.plotly_chart(fig_scatter, width='stretch', config={'displayModeBar': False})
        with col_d:
            fas_kat_df = _fasilitas_all.groupby('kategori_fasilitas').size().reset_index(name='jumlah') if not _fasilitas_all.empty else pd.DataFrame()
            st.plotly_chart(analytics.chart_fasilitas_per_kategori(fas_kat_df), width='stretch', config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header"><div class="bar"></div><h3>📋 Log Aktivitas Terbaru</h3></div>', unsafe_allow_html=True)
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        log_limit = st.slider('Tampilkan', 10, 200, 50, 10, key='log_limit')
        log_df = db.get_recent_logs(_conn, limit=log_limit)
        if not log_df.empty:
            col_rename = {'id_log': 'ID', 'timestamp': 'Waktu', 'jenis_aksi': 'Jenis Aksi', 'nama_gedung': 'Gedung', 'id_sesi': 'Sesi', 'detail_json': 'Detail'}
            log_display = log_df.rename(columns=col_rename)
            st.dataframe(log_display, width='stretch', hide_index=True, column_config={'Waktu': st.column_config.TextColumn(width='medium'), 'Jenis Aksi': st.column_config.TextColumn(width='small'), 'Gedung': st.column_config.TextColumn(width='large'), 'Detail': st.column_config.TextColumn(width='large')})
        else:
            st.info('Belum ada log aktivitas. Mulai gunakan peta untuk mengisi data.')
        st.markdown('</div>', unsafe_allow_html=True)
    _dashboard_realtime()
with tab_data:
    st.markdown('<div class="section-header"><div class="bar"></div><h3>🗄 Database Gedung Kampus UNJ</h3></div>', unsafe_allow_html=True)
    kat_filter = st.multiselect('Filter kategori:', options=all_kat, default=all_kat, key='data_kat_filter')
    data_df = db.get_gedung_by_kategori(conn, kat_filter) if kat_filter else gedung_all
    data_df = data_df.copy()
    data_df['foto'] = data_df['foto_id'].apply(drive_thumb_url)
    display_cols = ['foto', 'id_gedung', 'nama_gedung', 'kategori', 'fakultas_unit', 'latitude', 'longitude', 'jam_operasional', 'deskripsi']
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.dataframe(data_df[[c for c in display_cols if c in data_df.columns]], width='stretch', hide_index=True, column_config={'foto': st.column_config.ImageColumn('Foto', width='small'), 'id_gedung': st.column_config.NumberColumn('ID', width='small'), 'nama_gedung': st.column_config.TextColumn('Nama Gedung', width='large'), 'kategori': st.column_config.TextColumn('Kategori', width='medium'), 'fakultas_unit': st.column_config.TextColumn('Fakultas/Unit', width='medium'), 'latitude': st.column_config.NumberColumn('Lat', format='%.6f', width='small'), 'longitude': st.column_config.NumberColumn('Lon', format='%.6f', width='small'), 'jam_operasional': st.column_config.TextColumn('Jam Operasional', width='medium'), 'deskripsi': st.column_config.TextColumn('Deskripsi', width='large')})
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><div class="bar"></div><h3>🧩 Database Fasilitas</h3></div>', unsafe_allow_html=True)
    fasilitas_display = fasilitas_all.copy()
    fasilitas_display['foto'] = fasilitas_display['foto_id'].apply(drive_thumb_url)
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.dataframe(fasilitas_display[['foto', 'id_fasilitas', 'nama_fasilitas', 'kategori_fasilitas', 'unit_pengguna', 'nama_gedung', 'deskripsi']], width='stretch', hide_index=True, column_config={'foto': st.column_config.ImageColumn('Foto', width='small'), 'id_fasilitas': st.column_config.NumberColumn('ID', width='small'), 'nama_fasilitas': st.column_config.TextColumn('Nama Fasilitas', width='medium'), 'kategori_fasilitas': st.column_config.TextColumn('Kategori', width='small'), 'unit_pengguna': st.column_config.TextColumn('Unit/Fakultas', width='medium'), 'nama_gedung': st.column_config.TextColumn('Gedung Terkait', width='medium'), 'deskripsi': st.column_config.TextColumn('Deskripsi', width='large')})
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><div class="bar"></div><h3>💾 Ekspor Data</h3></div>', unsafe_allow_html=True)
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.download_button('⬇ gedung.csv', data=export.gedung_to_csv_bytes(gedung_all), file_name='gedung.csv', mime='text/csv', width='stretch')
    with col_e2:
        geojson_str = export.gedung_to_geojson(gedung_all)
        st.download_button('⬇ gedung.geojson', data=export.geojson_to_bytes(geojson_str), file_name='gedung.geojson', mime='application/geo+json', width='stretch')
    with col_e3:
        st.download_button('⬇ fasilitas.csv', data=export.fasilitas_to_csv_bytes(fasilitas_all), file_name='fasilitas.csv', mime='text/csv', width='stretch')
    with col_e4:
        log_df_exp = db.get_recent_logs(conn, limit=1000)
        if st.download_button('⬇ log_aktivitas.csv', data=export.log_to_csv_bytes(log_df_exp), file_name='log_aktivitas.csv', mime='text/csv', width='stretch'):
            db.insert_log(conn, 'export', st.session_state.sesi_id, detail={'file': 'log_aktivitas.csv'})
    with st.expander('👁 Preview GeoJSON (5 fitur pertama)'):
        import json
        gj = json.loads(geojson_str)
        st.json({'type': 'FeatureCollection', 'features': gj['features'][:5]})
st.markdown('<div class="app-footer">Peta Digital UNJ &nbsp;|&nbsp; Sistem Informasi Geografis Kampus &nbsp;|&nbsp; Data koordinat: Pemetaan Manual Kampus UNJ Rawamangun, Jakarta Timur</div>', unsafe_allow_html=True)