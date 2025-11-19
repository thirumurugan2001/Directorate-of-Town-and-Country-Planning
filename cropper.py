import io
import requests
import fitz
from PIL import Image
import numpy as np
import cv2

def rotate_image(pil_img, angle):
    (h, w) = pil_img.size[::-1]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        np.array(pil_img),
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return Image.fromarray(rotated)

def align_text_blocks(pdf_bytes, dpi=200):
    doc = fitz.open("pdf", pdf_bytes)
    if doc.page_count == 0:
        return None, "PDF has no pages"
    page = doc[0]
    text_blocks = page.get_text("blocks")
    angles = []

    for block in text_blocks:
        x0, y0, x1, y1, text, *_ = block
        if not text.strip():
            continue
        dx = x1 - x0
        dy = y1 - y0
        if dx == 0:
            continue
        angle = np.degrees(np.arctan2(dy, dx))
        if dx > (y1 - y0) * 3:
            angles.append(angle)
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
    if not angles:
        return pil_img, "No valid text lines found; no rotation applied"
    median_angle = np.median(angles)
    if median_angle < -45:
        median_angle += 90
    elif median_angle > 45:
        median_angle -= 90
    if abs(median_angle) < 1.0:
        return pil_img, "Already horizontal"
    rotated = rotate_image(pil_img, -median_angle)
    return rotated, f"Rotated {median_angle:.2f}° to align text"

def crop_right_side(pil_img, crop_ratio=0.3):
    w, h = pil_img.size
    left = int(w * (1 - crop_ratio))
    return pil_img.crop((left, 0, w, h))

def process_pdf_from_url(pdf_url):
    try:
        response = requests.get(pdf_url, timeout=20)
        if response.status_code != 200:
            return None, f"Failed to fetch PDF: {pdf_url}"
        pdf_bytes = io.BytesIO(response.content)
        deskewed_img, msg = align_text_blocks(pdf_bytes)
        cropped = crop_right_side(deskewed_img, crop_ratio=0.3)
        return cropped, f"Success ({msg} + cropped)"
    except Exception as e:
        return None, f"Error processing PDF: {e}"