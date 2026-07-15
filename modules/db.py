"""Modul koneksi & query database SQLite untuk Peta Digital UNJ."""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "database.sqlite")


def get_connection() -> sqlite3.Connection:
    """Buat koneksi SQLite dan auto-seed database jika belum ada."""
    db_exists = os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

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
            print(f"Error auto-initializing database: {e}", file=sys.stderr)

    return conn


# ── Sesi Pengguna ─────────────────────────────────────────────────────────

def ensure_session(conn: sqlite3.Connection, sesi_id: str) -> None:
    """Pastikan baris sesi ada di pengguna_sesi (idempotent)."""
    conn.execute(
        "INSERT OR IGNORE INTO pengguna_sesi (id_sesi) VALUES (?)", (sesi_id,)
    )
    conn.commit()


# ── Query Gedung ──────────────────────────────────────────────────────────

def get_all_gedung(conn: sqlite3.Connection) -> pd.DataFrame:
    """Gedung sungguhan saja (waypoint jalur 'WP_%' disembunyikan dari UI)."""
    return pd.read_sql_query(
        "SELECT * FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\' "
        "ORDER BY kategori, nama_gedung", conn
    )


def get_all_gedung_for_routing(conn: sqlite3.Connection) -> pd.DataFrame:
    """Semua node termasuk waypoint jalur — khusus untuk membangun graf rute."""
    return pd.read_sql_query(
        "SELECT * FROM gedung ORDER BY id_gedung", conn
    )


def get_gedung_by_kategori(conn: sqlite3.Connection, kategori_list: list) -> pd.DataFrame:
    if not kategori_list:
        return get_all_gedung(conn)
    placeholders = ",".join(["?" for _ in kategori_list])
    query = f"""
        SELECT * FROM gedung
        WHERE kategori IN ({placeholders}) AND nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\'
        ORDER BY kategori, nama_gedung
    """
    return pd.read_sql_query(query, conn, params=kategori_list)


def get_semua_kategori_gedung(conn: sqlite3.Connection) -> list:
    cur = conn.cursor()
    return [r[0] for r in cur.execute(
        "SELECT DISTINCT kategori FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\' "
        "ORDER BY kategori"
    ).fetchall()]


def insert_gedung(conn: sqlite3.Connection, data: dict) -> int:
    data = dict(data)
    data.setdefault("foto_id", None)
    cur = conn.execute(
        """INSERT INTO gedung
           (nama_gedung, kategori, fakultas_unit, fungsi, deskripsi,
            latitude, longitude, jam_operasional, foto_id)
           VALUES (:nama_gedung, :kategori, :fakultas_unit, :fungsi, :deskripsi,
                   :latitude, :longitude, :jam_operasional, :foto_id)""",
        data,
    )
    conn.commit()
    return cur.lastrowid


def update_gedung(conn: sqlite3.Connection, id_gedung: int, data: dict) -> None:
    data = dict(data)
    data["id_gedung"] = id_gedung
    data.setdefault("foto_id", None)
    conn.execute(
        """UPDATE gedung SET
             nama_gedung = :nama_gedung, kategori = :kategori,
             fakultas_unit = :fakultas_unit, fungsi = :fungsi,
             deskripsi = :deskripsi, latitude = :latitude,
             longitude = :longitude, jam_operasional = :jam_operasional,
             foto_id = :foto_id
           WHERE id_gedung = :id_gedung""",
        data,
    )
    conn.commit()


def delete_gedung(conn: sqlite3.Connection, id_gedung: int) -> None:
    conn.execute("DELETE FROM rute WHERE id_asal = ? OR id_tujuan = ?", (id_gedung, id_gedung))
    conn.execute("DELETE FROM gedung WHERE id_gedung = ?", (id_gedung,))
    conn.commit()


# ── Query Fasilitas ───────────────────────────────────────────────────────

def get_all_fasilitas(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT f.*, g.nama_gedung
        FROM fasilitas f
        LEFT JOIN gedung g ON f.id_gedung = g.id_gedung
        ORDER BY f.kategori_fasilitas, f.nama_fasilitas
    """
    return pd.read_sql_query(query, conn)


def get_fasilitas_by_gedung(conn: sqlite3.Connection, id_gedung: int) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM fasilitas WHERE id_gedung = ? ORDER BY nama_fasilitas",
        conn, params=(id_gedung,),
    )


def insert_fasilitas(conn: sqlite3.Connection, data: dict) -> int:
    data = dict(data)
    data.setdefault("foto_id", None)
    cur = conn.execute(
        """INSERT INTO fasilitas
           (nama_fasilitas, kategori_fasilitas, deskripsi, unit_pengguna, foto_id, id_gedung)
           VALUES (:nama_fasilitas, :kategori_fasilitas, :deskripsi, :unit_pengguna, :foto_id, :id_gedung)""",
        data,
    )
    conn.commit()
    return cur.lastrowid


def update_fasilitas(conn: sqlite3.Connection, id_fasilitas: int, data: dict) -> None:
    data = dict(data)
    data["id_fasilitas"] = id_fasilitas
    data.setdefault("foto_id", None)
    conn.execute(
        """UPDATE fasilitas SET
             nama_fasilitas = :nama_fasilitas, kategori_fasilitas = :kategori_fasilitas,
             deskripsi = :deskripsi, unit_pengguna = :unit_pengguna, foto_id = :foto_id,
             id_gedung = :id_gedung
           WHERE id_fasilitas = :id_fasilitas""",
        data,
    )
    conn.commit()


def delete_fasilitas(conn: sqlite3.Connection, id_fasilitas: int) -> None:
    conn.execute("DELETE FROM fasilitas WHERE id_fasilitas = ?", (id_fasilitas,))
    conn.commit()


# ── Query Rute ────────────────────────────────────────────────────────────

def get_all_edges(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT
            r.id_asal, r.id_tujuan, r.jarak_meter,
            ga.nama_gedung AS nama_asal, ga.latitude AS lat_asal, ga.longitude AS lon_asal,
            gt.nama_gedung AS nama_tujuan, gt.latitude AS lat_tujuan, gt.longitude AS lon_tujuan
        FROM rute r
        JOIN gedung ga ON r.id_asal   = ga.id_gedung
        JOIN gedung gt ON r.id_tujuan = gt.id_gedung
    """
    return pd.read_sql_query(query, conn)


# ── Log Aktivitas ─────────────────────────────────────────────────────────

def insert_log(
    conn: sqlite3.Connection,
    jenis_aksi: str,
    sesi_id: str,
    id_gedung: Optional[int] = None,
    detail: Optional[dict] = None,
) -> None:
    ensure_session(conn, sesi_id)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO log_aktivitas (timestamp, jenis_aksi, id_sesi, id_gedung, detail_json)
           VALUES (?, ?, ?, ?, ?)""",
        (ts, jenis_aksi, sesi_id, id_gedung, json.dumps(detail or {}, ensure_ascii=False)),
    )
    conn.execute(
        "UPDATE pengguna_sesi SET jumlah_aktivitas = jumlah_aktivitas + 1, "
        "waktu_terakhir = ? WHERE id_sesi = ?",
        (ts, sesi_id),
    )
    conn.commit()


def get_recent_logs(conn: sqlite3.Connection, limit: int = 100) -> pd.DataFrame:
    query = f"""
        SELECT
            la.id_log, la.timestamp, la.jenis_aksi,
            COALESCE(g.nama_gedung, '-') AS nama_gedung,
            la.id_sesi, la.detail_json
        FROM log_aktivitas la
        LEFT JOIN gedung g ON la.id_gedung = g.id_gedung
        ORDER BY la.timestamp DESC
        LIMIT {limit}
    """
    return pd.read_sql_query(query, conn)


# ── Statistik Dashboard ───────────────────────────────────────────────────

def get_kategori_visit_count(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT g.kategori, COUNT(*) AS jumlah
        FROM log_aktivitas la
        JOIN gedung g ON la.id_gedung = g.id_gedung
        WHERE la.jenis_aksi = 'view_marker'
        GROUP BY g.kategori
        ORDER BY jumlah DESC
    """
    return pd.read_sql_query(query, conn)


def get_aksi_trend(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT DATE(timestamp) AS tanggal, jenis_aksi, COUNT(*) AS jumlah
        FROM log_aktivitas
        WHERE timestamp >= DATE('now', '-7 days')
        GROUP BY tanggal, jenis_aksi
        ORDER BY tanggal
    """
    return pd.read_sql_query(query, conn)


def get_aksi_distribution(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT jenis_aksi, COUNT(*) AS jumlah
        FROM log_aktivitas
        GROUP BY jenis_aksi
        ORDER BY jumlah DESC
    """
    return pd.read_sql_query(query, conn)


def get_total_stats(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    stats = {}
    stats["total_gedung"] = cur.execute(
        "SELECT COUNT(*) FROM gedung WHERE nama_gedung NOT LIKE 'WP\\_%' ESCAPE '\\'"
    ).fetchone()[0]
    stats["total_fasilitas"] = cur.execute("SELECT COUNT(*) FROM fasilitas").fetchone()[0]
    stats["total_log"] = cur.execute("SELECT COUNT(*) FROM log_aktivitas").fetchone()[0]
    stats["total_sesi"] = cur.execute("SELECT COUNT(*) FROM pengguna_sesi").fetchone()[0]
    stats["total_rute"] = cur.execute("SELECT COUNT(*) FROM rute").fetchone()[0]
    return stats
