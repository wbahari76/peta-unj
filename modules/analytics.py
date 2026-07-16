import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
CARD_BG = '#111F3A'
TEXT_MAIN = '#E8F0FE'
TEXT_MUTED = '#8FA3BF'
GOLD = '#C98A2C'
TEAL = '#12B5B0'
KATEGORI_COLOR = {'Akademik': '#2F6FED', 'Administrasi & Layanan': '#8B5CF6', 'Fasilitas Umum': '#12B5B0', 'Kesehatan & Keamanan': '#2E9E5B', 'Parkir': '#D9973B'}
PLOTLY_LAYOUT = dict(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, font=dict(color=TEXT_MAIN, family='Segoe UI, Inter, sans-serif'), margin=dict(l=16, r=16, t=40, b=16), title_font=dict(size=14, color=TEXT_MAIN))

def chart_kategori_terpopuler(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure('Belum ada data kunjungan')
    colors = [KATEGORI_COLOR.get(k, TEAL) for k in df['kategori']]
    fig = go.Figure(go.Bar(x=df['jumlah'], y=df['kategori'], orientation='h', marker_color=colors, text=df['jumlah'], textposition='outside', textfont=dict(color=TEXT_MAIN, size=12)))
    fig.update_layout(**PLOTLY_LAYOUT, title='🏆 Kategori Gedung Terpopuler', xaxis=dict(showgrid=True, gridcolor='#1F3A5F', title='Jumlah Kunjungan'), yaxis=dict(showgrid=False), height=280)
    return fig

def chart_tren_pencarian(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure('Belum ada data tren')
    color_map = {'view_marker': TEAL, 'search': '#7C4DFF', 'route': GOLD, 'filter': '#2E9E5B', 'export': '#C62828'}
    fig = go.Figure()
    for aksi in df['jenis_aksi'].unique():
        sub = df[df['jenis_aksi'] == aksi].sort_values('tanggal')
        fig.add_trace(go.Scatter(x=sub['tanggal'], y=sub['jumlah'], name=aksi, mode='lines+markers', line=dict(width=2.5, color=color_map.get(aksi, TEAL)), marker=dict(size=6), fill='tozeroy', fillcolor=f'rgba{_hex_to_rgba(color_map.get(aksi, TEAL), 0.12)}'))
    fig.update_layout(**PLOTLY_LAYOUT, title='📈 Tren Aktivitas 7 Hari Terakhir', xaxis=dict(showgrid=True, gridcolor='#1F3A5F'), yaxis=dict(showgrid=True, gridcolor='#1F3A5F'), legend=dict(bgcolor=CARD_BG, bordercolor='#1F3A5F'), height=280)
    return fig

def chart_distribusi_aksi(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure('Belum ada data distribusi')
    color_seq = [TEAL, '#7C4DFF', GOLD, '#2E9E5B', '#C62828', '#F9A825']
    label_map = {'view_marker': 'Lihat Marker', 'search': 'Pencarian', 'route': 'Rute', 'filter': 'Filter', 'export': 'Ekspor', 'admin': 'Admin'}
    labels = [label_map.get(a, a) for a in df['jenis_aksi']]
    fig = go.Figure(go.Pie(labels=labels, values=df['jumlah'], hole=0.55, marker=dict(colors=color_seq[:len(df)], line=dict(color=CARD_BG, width=2)), textinfo='label+percent', textfont=dict(color=TEXT_MAIN, size=11)))
    fig.update_layout(**PLOTLY_LAYOUT, title='🎯 Distribusi Aksi Pengguna', showlegend=False, height=280)
    return fig

def chart_heatmap_lokasi(gedung_df: pd.DataFrame) -> go.Figure:
    if gedung_df.empty:
        return _empty_figure('Belum ada data gedung')
    fig = px.scatter_mapbox(gedung_df, lat='latitude', lon='longitude', color='kategori', color_discrete_map=KATEGORI_COLOR, hover_name='nama_gedung', hover_data={'kategori': True, 'latitude': False, 'longitude': False}, zoom=15.5, height=380, title='🗺 Sebaran Gedung di Peta')
    fig.update_traces(marker=dict(size=14, opacity=0.85))
    fig.update_layout(**PLOTLY_LAYOUT, mapbox_style='carto-darkmatter', legend_title_text='Kategori', legend=dict(bgcolor=CARD_BG, bordercolor='#1F3A5F'))
    return fig

def chart_fasilitas_per_kategori(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_figure('Belum ada data fasilitas')
    fig = go.Figure(go.Bar(x=df['kategori_fasilitas'], y=df['jumlah'], marker_color=[GOLD, TEAL, '#2E9E5B', '#8B5CF6', '#D9973B'][:len(df)], text=df['jumlah'], textposition='outside'))
    fig.update_layout(**PLOTLY_LAYOUT, title='🧩 Fasilitas per Kategori', xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1F3A5F'), height=280)
    return fig

def _empty_figure(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False, font=dict(color=TEXT_MUTED, size=14))
    fig.update_layout(**PLOTLY_LAYOUT, height=280)
    return fig

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    return f'({r},{g},{b},{alpha})'