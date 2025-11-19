import os 
from PIL import Image
import io
import base64
import json

def validate_image(image_path: str):
    try :
        if not os.path.exists(image_path):
            return False
        try:
            Image.open(image_path)
            return True
        except Exception:
            return False
    except Exception as e :
        print("Error in the validate_image Functions :",str(e))
        return False

def encode_image_to_base64(image_path: str):
    try:
        SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"]
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in SUPPORTED_IMAGE_FORMATS:
            img = Image.open(image_path)
            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="JPEG")
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode("utf-8")
        else:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error in the encode_image_to_base64 Function: {str(e)}")
        return False

def clean_json_output(raw_result: str) -> dict:
    try:
        cleaned = raw_result.strip()
        cleaned = cleaned.replace("```json", "")
        cleaned = cleaned.replace("```", "")
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)        
        return {
            "PROJECT TITLE": parsed.get("PROJECT TITLE", ""),
            "OWNER SIGNATURE": parsed.get("OWNER SIGNATURE", ""),
            "STRUCTURAL ENGINEER": parsed.get("STRUCTURAL ENGINEER", ""),
            "REGISTERED ENGINEER": parsed.get("REGISTERED ENGINEER", "")
        }
    except Exception as e:
        return {
            "PROJECT TITLE": "",
            "OWNER SIGNATURE": "",
            "STRUCTURAL ENGINEER": "",
            "REGISTERED ENGINEER": ""
        }