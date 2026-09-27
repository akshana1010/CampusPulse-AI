"""
CampusPulse AI – File Upload Service
Validates, resizes, and saves user-uploaded images securely.
"""

import os
import uuid
import logging
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_DIMENSION = 1920   # pixels
THUMBNAIL_SIZE = (400, 400)  # for thumbnail generation (future use)


def save_uploaded_image(file_obj, app_config: dict) -> tuple[str | None, str | None]:
    """
    Validate and save an uploaded image file.

    Args:
        file_obj:   Werkzeug FileStorage object from request.files.
        app_config: Flask app.config dict (needs UPLOAD_FOLDER, ALLOWED_EXTENSIONS).

    Returns:
        (relative_path, None)  on success
        (None, error_message)  on failure
    """
    upload_folder = app_config.get("UPLOAD_FOLDER", "uploads")
    allowed = app_config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "gif", "webp"})

    # ── Validate file extension ────────────────────────────────────────────────
    filename = file_obj.filename or ""
    ext = _get_extension(filename)
    if ext not in allowed:
        return None, f"File type '.{ext}' is not allowed. Allowed: {', '.join(allowed)}"

    # ── Generate a safe, unique filename ──────────────────────────────────────
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_folder, safe_name)

    try:
        # ── Open with Pillow to validate it's a real image ────────────────────
        img = Image.open(file_obj.stream)
        img.verify()  # Raises if not a valid image

        # Re-open after verify (stream is consumed)
        file_obj.stream.seek(0)
        img = Image.open(file_obj.stream)

        # ── Strip EXIF metadata (privacy) ─────────────────────────────────────
        img_data = img.getdata()
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(img_data)

        # ── Resize if oversized ───────────────────────────────────────────────
        if max(clean_img.size) > MAX_IMAGE_DIMENSION:
            clean_img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

        # ── Save to disk ──────────────────────────────────────────────────────
        os.makedirs(upload_folder, exist_ok=True)
        clean_img.save(save_path, optimize=True, quality=85)

        # Return a web-accessible relative path
        relative_path = f"uploads/{safe_name}"
        logger.info(f"Image saved: {relative_path}")
        return relative_path, None

    except Exception as exc:
        logger.error(f"Image save failed: {exc}")
        return None, "Image could not be processed. Please try a different file."


def _get_extension(filename: str) -> str:
    """Extract and lowercase the file extension (without dot)."""
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


def delete_uploaded_image(relative_path: str, upload_folder: str) -> bool:
    """
    Delete an uploaded image from disk.

    Args:
        relative_path: e.g. 'uploads/abc123.jpg'
        upload_folder: absolute path to the uploads directory.

    Returns:
        True if deleted, False if file not found or error.
    """
    filename = os.path.basename(relative_path)
    full_path = os.path.join(upload_folder, filename)

    try:
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"Deleted image: {full_path}")
            return True
    except Exception as exc:
        logger.error(f"Could not delete image {full_path}: {exc}")

    return False
