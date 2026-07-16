def drive_thumb_url(foto_id: str | None, size: int=800) -> str | None:
    if not foto_id or str(foto_id).strip() in ('', '-', 'None', 'nan'):
        return None
    return f'https://drive.google.com/thumbnail?id={foto_id}&sz=w{size}'

def drive_thumb_url_fallback(foto_id: str | None) -> str | None:
    if not foto_id or str(foto_id).strip() in ('', '-', 'None', 'nan'):
        return None
    return f'https://lh3.googleusercontent.com/d/{foto_id}=w800'