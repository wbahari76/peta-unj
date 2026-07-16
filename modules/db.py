import sqlite3
import os
import json
from datetime import datetime
from typing import Optional
import pandas as pd
import tempfile
import shutil
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'database.sqlite')

def get_connection() -> sqlite3.Connection:
    global DB_PATH
    db_dir = os.path.dirname(DB_PATH)
    
    # Cek permission: Streamlit Cloud kadang read-only di folder mount
    if os.path.exists(DB_PATH):
        if not os.access(DB_PATH, os.W_OK) or not os.access(db_dir, os.W_OK):
            tmp_db = os.path.join(tempfile.gettempdir(), 'peta_unj_tmp.sqlite')
            if not os.path.exists(tmp_db):
                shutil.copy2(DB_PATH, tmp_db)
            DB_PATH = tmp_db
    else:
        # Jika belum ada dan direktori tidak bisa ditulis
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                pass
        if not os.access(db_dir, os.W_OK):
            DB_PATH = os.path.join(tempfile.gettempdir(), 'peta_unj_tmp.sqlite')

    db_exists = os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    # Gunakan memory journal agar SQLite tidak mencoba membuat file -journal di direktori jika dibatasi
    conn.execute('PRAGMA journal_mode = MEMORY')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gedung'")
    table_exists = cursor.fetchone()
    if not db_exists or not table_exists:
        try:
            from database.seed_data import seed_all
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            seed_all(conn)
        except Exception as e:
            import sys
            print(f'Error auto-initializing database: {e}', file=sys.stderr)
    return conn

def ensure_session(conn: sqlite3.Connection, sesi_id: str) -> None:
    conn.execute('INSERT OR IGNORE INTO pengguna_sesi (id_sesi) VALUES (?)', (sesi_id,))
    conn.commit()

def get_all_gedung(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\' ORDER BY kategori, nama_gedung", conn)

def get_all_gedung_for_routing(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query('SELECT * FROM gedung ORDER BY id_gedung', conn)

def get_gedung_by_kategori(conn: sqlite3.Connection, kategori_list: list) -> pd.DataFrame:
    if not kategori_list:
        return get_all_gedung(conn)
    placeholders = ','.join(['?' for _ in kategori_list])
    query = f"\n        SELECT * FROM gedung\n        WHERE kategori IN ({placeholders}) AND nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\'\n        ORDER BY kategori, nama_gedung\n    "
    return pd.read_sql_query(query, conn, params=kategori_list)

def get_semua_kategori_gedung(conn: sqlite3.Connection) -> list:
    cur = conn.cursor()
    return [r[0] for r in cur.execute("SELECT DISTINCT kategori FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\' ORDER BY kategori").fetchall()]

def insert_gedung(conn: sqlite3.Connection, data: dict) -> int:
    data = dict(data)
    data.setdefault('foto_id', None)
    cur = conn.execute('INSERT INTO gedung\n           (nama_gedung, kategori, fakultas_unit, fungsi, deskripsi,\n            latitude, longitude, jam_operasional, foto_id)\n           VALUES (:nama_gedung, :kategori, :fakultas_unit, :fungsi, :deskripsi,\n                   :latitude, :longitude, :jam_operasional, :foto_id)', data)
    conn.commit()
    return cur.lastrowid

def update_gedung(conn: sqlite3.Connection, id_gedung: int, data: dict) -> None:
    data = dict(data)
    data['id_gedung'] = id_gedung
    data.setdefault('foto_id', None)
    conn.execute('UPDATE gedung SET\n             nama_gedung = :nama_gedung, kategori = :kategori,\n             fakultas_unit = :fakultas_unit, fungsi = :fungsi,\n             deskripsi = :deskripsi, latitude = :latitude,\n             longitude = :longitude, jam_operasional = :jam_operasional,\n             foto_id = :foto_id\n           WHERE id_gedung = :id_gedung', data)
    conn.commit()

def delete_gedung(conn: sqlite3.Connection, id_gedung: int) -> None:
    conn.execute('DELETE FROM rute WHERE id_asal = ? OR id_tujuan = ?', (id_gedung, id_gedung))
    conn.execute('DELETE FROM gedung WHERE id_gedung = ?', (id_gedung,))
    conn.commit()

def get_all_fasilitas(conn: sqlite3.Connection) -> pd.DataFrame:
    query = '\n        SELECT f.*, g.nama_gedung\n        FROM fasilitas f\n        LEFT JOIN gedung g ON f.id_gedung = g.id_gedung\n        ORDER BY f.kategori_fasilitas, f.nama_fasilitas\n    '
    return pd.read_sql_query(query, conn)

def get_fasilitas_by_gedung(conn: sqlite3.Connection, id_gedung: int) -> pd.DataFrame:
    return pd.read_sql_query('SELECT * FROM fasilitas WHERE id_gedung = ? ORDER BY nama_fasilitas', conn, params=(id_gedung,))

def insert_fasilitas(conn: sqlite3.Connection, data: dict) -> int:
    data = dict(data)
    data.setdefault('foto_id', None)
    cur = conn.execute('INSERT INTO fasilitas\n           (nama_fasilitas, kategori_fasilitas, deskripsi, unit_pengguna, foto_id, id_gedung)\n           VALUES (:nama_fasilitas, :kategori_fasilitas, :deskripsi, :unit_pengguna, :foto_id, :id_gedung)', data)
    conn.commit()
    return cur.lastrowid

def update_fasilitas(conn: sqlite3.Connection, id_fasilitas: int, data: dict) -> None:
    data = dict(data)
    data['id_fasilitas'] = id_fasilitas
    data.setdefault('foto_id', None)
    conn.execute('UPDATE fasilitas SET\n             nama_fasilitas = :nama_fasilitas, kategori_fasilitas = :kategori_fasilitas,\n             deskripsi = :deskripsi, unit_pengguna = :unit_pengguna, foto_id = :foto_id,\n             id_gedung = :id_gedung\n           WHERE id_fasilitas = :id_fasilitas', data)
    conn.commit()

def delete_fasilitas(conn: sqlite3.Connection, id_fasilitas: int) -> None:
    conn.execute('DELETE FROM fasilitas WHERE id_fasilitas = ?', (id_fasilitas,))
    conn.commit()

def get_all_edges(conn: sqlite3.Connection) -> pd.DataFrame:
    query = '\n        SELECT\n            r.id_asal, r.id_tujuan, r.jarak_meter,\n            ga.nama_gedung AS nama_asal, ga.latitude AS lat_asal, ga.longitude AS lon_asal,\n            gt.nama_gedung AS nama_tujuan, gt.latitude AS lat_tujuan, gt.longitude AS lon_tujuan\n        FROM rute r\n        JOIN gedung ga ON r.id_asal   = ga.id_gedung\n        JOIN gedung gt ON r.id_tujuan = gt.id_gedung\n    '
    return pd.read_sql_query(query, conn)

def insert_log(conn: sqlite3.Connection, jenis_aksi: str, sesi_id: str, id_gedung: Optional[int]=None, detail: Optional[dict]=None) -> None:
    ensure_session(conn, sesi_id)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('INSERT INTO log_aktivitas (timestamp, jenis_aksi, id_sesi, id_gedung, detail_json)\n           VALUES (?, ?, ?, ?, ?)', (ts, jenis_aksi, sesi_id, id_gedung, json.dumps(detail or {}, ensure_ascii=False)))
    conn.execute('UPDATE pengguna_sesi SET jumlah_aktivitas = jumlah_aktivitas + 1, waktu_terakhir = ? WHERE id_sesi = ?', (ts, sesi_id))
    conn.commit()

def get_recent_logs(conn: sqlite3.Connection, limit: int=100) -> pd.DataFrame:
    query = f"\n        SELECT\n            la.id_log, la.timestamp, la.jenis_aksi,\n            COALESCE(g.nama_gedung, '-') AS nama_gedung,\n            la.id_sesi, la.detail_json\n        FROM log_aktivitas la\n        LEFT JOIN gedung g ON la.id_gedung = g.id_gedung\n        ORDER BY la.timestamp DESC\n        LIMIT {limit}\n    "
    return pd.read_sql_query(query, conn)

def get_kategori_visit_count(conn: sqlite3.Connection) -> pd.DataFrame:
    query = "\n        SELECT g.kategori, COUNT(*) AS jumlah\n        FROM log_aktivitas la\n        JOIN gedung g ON la.id_gedung = g.id_gedung\n        WHERE la.jenis_aksi = 'view_marker'\n        GROUP BY g.kategori\n        ORDER BY jumlah DESC\n    "
    return pd.read_sql_query(query, conn)

def get_aksi_trend(conn: sqlite3.Connection) -> pd.DataFrame:
    query = "\n        SELECT DATE(timestamp) AS tanggal, jenis_aksi, COUNT(*) AS jumlah\n        FROM log_aktivitas\n        WHERE timestamp >= DATE('now', '-7 days')\n        GROUP BY tanggal, jenis_aksi\n        ORDER BY tanggal\n    "
    return pd.read_sql_query(query, conn)

def get_aksi_distribution(conn: sqlite3.Connection) -> pd.DataFrame:
    query = '\n        SELECT jenis_aksi, COUNT(*) AS jumlah\n        FROM log_aktivitas\n        GROUP BY jenis_aksi\n        ORDER BY jumlah DESC\n    '
    return pd.read_sql_query(query, conn)

def get_total_stats(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    stats = {}
    stats['total_gedung'] = cur.execute("SELECT COUNT(*) FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\'").fetchone()[0]
    stats['total_fasilitas'] = cur.execute('SELECT COUNT(*) FROM fasilitas').fetchone()[0]
    stats['total_log'] = cur.execute('SELECT COUNT(*) FROM log_aktivitas').fetchone()[0]
    stats['total_sesi'] = cur.execute('SELECT COUNT(*) FROM pengguna_sesi').fetchone()[0]
    stats['total_rute'] = cur.execute('SELECT COUNT(*) FROM rute').fetchone()[0]
    return stats