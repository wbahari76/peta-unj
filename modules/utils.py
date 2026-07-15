"""Utilitas kecil bersama antar-modul."""


def drive_thumb_url(foto_id: str | None, size: int = 800) -> str | None:
    """
    Bangun URL thumbnail langsung dari ID file Google Drive (foto gedung/
    fasilitas yang dibagikan lewat Google Drive dengan akses "siapa saja
    yang memiliki tautan"). Mengembalikan None jika foto_id kosong.

    CATATAN: foto hanya akan tampil jika file di Google Drive sudah
    di-share dengan akses "Anyone with the link — Viewer". Jika file
    masih private/restricted, gambar tidak akan pernah bisa dimuat oleh
    browser siapa pun (termasuk pengguna aplikasi ini).
    """
    if not foto_id or str(foto_id).strip() in ("", "-", "None", "nan"):
        return None
    return f"https://drive.google.com/thumbnail?id={foto_id}&sz=w{size}"


def drive_thumb_url_fallback(foto_id: str | None) -> str | None:
    """URL alternatif (format googleusercontent) untuk fallback bila format
    utama gagal dimuat — beberapa file merespons lebih baik ke format ini."""
    if not foto_id or str(foto_id).strip() in ("", "-", "None", "nan"):
        return None
    return f"https://lh3.googleusercontent.com/d/{foto_id}=w800"
