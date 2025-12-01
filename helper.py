import re
import os 
import io
import json
import base64
from PIL import Image 

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
        print(f"[DEBUG] Failed to parse JSON: {e}")
        print(f"[DEBUG] Raw result: {raw_result}")
        return {
            "PROJECT TITLE": "",
            "OWNER SIGNATURE": "",
            "STRUCTURAL ENGINEER": "",
            "REGISTERED ENGINEER": ""
        }
    
def extract_engineer_blocks(text):
    blocks = re.split(r'\n\s*\n', text.strip())
    merged = []
    for block in blocks:
        parts = re.split(r'(?=(?:Dr\.|Er\.|Mr\.|Ms\.|[A-Z][a-z]+\s+[A-Z]\.))', block.strip())
        merged.extend([p.strip() for p in parts if p.strip()])
    return merged

def extract_details(block):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', block, flags=re.IGNORECASE)
    email = " | ".join(emails) if emails else ""
    phones = re.findall(r'(\+?\d[\d\s-]{7,}\d)', block)
    phone = " | ".join([p.strip() for p in phones]) if phones else ""
    cleaned = block
    for e in emails:
        cleaned = cleaned.replace(e, "")
    for p in phones:
        cleaned = cleaned.replace(p, "")
    cleaned = re.sub(r'\b(Mob|Mobile|Cell|Ph|No|Phone|Tel|E[- ]?Mail|Email Id?)\b[: ]?', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("|", " ")
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(" ,.;:-")
    return {
        "name_Address": cleaned,
        "mail": email,
        "phone": phone,
    }

def process_structural_signatures(input_data):
    result = {}
    for key, value in input_data.items():
        if key in ["STRUCTURAL ENGINEER", "REGISTERED ENGINEER"]:
            if isinstance(value, str):
                details = extract_details(value)
                result[key] = {
                    "name_Address": details["name_Address"],
                    "mail": details["mail"],
                    "phone": details["phone"]
                }
            else:
                result[key] = value
        else:
            result[key] = value
    return result

def normalize_signature(sig):
    if isinstance(sig, dict):
        return {
            "name_Address": sig.get("name_Address", "") if sig.get("name_Address", "") is not None else "",
            "mail": sig.get("mail", "") if sig.get("mail", "") is not None else "",
            "phone": sig.get("phone", "") if sig.get("phone", "") is not None else ""
        }
    if isinstance(sig, str) and sig.strip():
        return {"name_Address": sig.strip(), "mail": "", "phone": ""}
    return {"name_Address": "", "mail": "", "phone": ""}

def extract_contact_from_text(text):
    email = ""
    phone = ""    
    if text:
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, text)
        if email_matches:
            email = email_matches[0]        
        phone_pattern = r'(\+91[-\s]?)?[6-9]\d{9}'
        phone_matches = re.findall(phone_pattern, text)
        if phone_matches:
            for match in phone_matches:
                if isinstance(match, tuple):
                    phone = match[0] if match[0] else match[1]
                else:
                    phone = match
                if phone:
                    break    
    return email, phone