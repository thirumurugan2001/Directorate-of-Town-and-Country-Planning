from helper import validate_image, encode_image_to_base64, process_structural_signatures
import openai
import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

def extract_pdf_details_from_image(image_path: str):
    try:
        if not validate_image(image_path):
            print("[DEBUG] Image validation failed.")
            return {    
                "status": False,
                "statusCode": 400,
                "message": "Invalid image file",
                "data": {}
            }
        client = openai.OpenAI(
            base_url=os.getenv("GPT_URL"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
        )

        prompt = """
        CRITICAL: You are a highly accurate document analysis AI specialized in engineering and building plans. Extract EXACT text as it appears in the document without any modification, translation, or rephrasing.

        # MANDATORY EXTRACTION FIELDS:

        1. PROJECT TITLE:
           - Primary: Look for "PROJECT TITLE", "TITLE OF PROJECT", "TITLE:", "PROJECT:" labels
           - Secondary: Find any line starting with "PLAN SHOWING", "PROPOSED", "CONSTRUCTION OF"
           - Tertiary: Look for the largest font text that describes the project scope
           - If nothing found: return empty string ""

        2. OWNER SIGNATURE:
           - Labels: "OWNER SIGNATURE", "SIGNATURE OF OWNER", "OWNER'S SIGNATURE", "APPLICANT", "PROPRIETOR"
           - Also check: "FOR [Company Name]", "SIGNATURE OF APPLICANT"
           - Extract the complete text block after these labels
           - Include company names, representative names, and "For [Company]" patterns

        3. STRUCTURAL ENGINEER:
           - Labels: "STRUCTURAL ENGINEER", "SIGNATURE OF STRUCTURAL ENGINEER", "STRUCTURAL ENGINEER'S SIGNATURE"
           - Also: "REGISTERED STRUCTURAL ENGINEER", "R.S.E", "STRUCTURAL CONSULTANT"
           - Look for registration numbers, qualifications, addresses, phone numbers
           - Extract the entire signature block including name, registration, address, contact

        4. REGISTERED ENGINEER/ARCHITECT:
           - Labels: "REGISTERED ENGINEER", "ARCHITECT", "SIGNATURE OF ARCHITECT", "LICENSED SURVEYOR"
           - Also: "ARCHITECT/LICENSED SURVEYOR", "REGISTERED ARCHITECT", "CONSULTING ENGINEER"
           - Extract complete details: name, registration number, address, phone, email
           - Include all qualification details like B.Arch, M.Tech, etc.

        # EXTRACTION RULES:
        - PRESERVE EXACT TEXT: Do not modify, correct, translate, or rephrase any text
        - COMPLETE BLOCKS: Extract entire signature blocks with all details
        - MULTIPLE OCCURRENCES: If multiple instances exist, choose the most complete/legible one
        - CONTEXT AWARE: Look near seals, stamps, signature lines, and labeled sections
        - FORMAT PRESERVATION: Keep original line breaks, spacing, and punctuation
        - CASE SENSITIVE: Maintain original capitalization

        # SEARCH STRATEGY:
        1. Scan for explicit labels in bold, underlined, or prominent text
        2. Look near the bottom of documents for signature sections
        3. Check around official seals and registration stamps
        4. Examine corners and margins for architect/engineer details
        5. Verify text near "APPROVED BY", "CERTIFIED BY", "CHECKED BY"

        # QUALITY CONTROL:
        - Reject incomplete extractions (single words without context)
        - Prefer longer, more complete text blocks
        - Include registration numbers when present
        - Capture full addresses and contact information
        - Verify the text belongs to the correct category

        # OUTPUT FORMAT:
        Return STRICT JSON only with these exact field names:
        {
            "PROJECT TITLE": "exact text as found or empty string",
            "OWNER SIGNATURE": "exact text as found or empty string", 
            "STRUCTURAL ENGINEER": "exact text as found or empty string",
            "REGISTERED ENGINEER": "exact text as found or empty string"
        }

        # EXAMPLES OF GOOD EXTRACTION:
        {
            "PROJECT TITLE": "PLAN SHOWING THE PROPOSED CONSTRUCTION OF STILT + 5 FLOORS WITH 93 D.UNITS AFFORDABLE HOUSING RESIDENTIAL BUILDING AT S.NOS: 69/9D1A1 & 70/2A1, EAST COAST ROAD, KANATHUR REDDIKUPPAM VILLAGE, THIRUPORUR TALUK, CHENGALPET DISTRICT.",
            "OWNER SIGNATURE": "For SIDHARTH FOUNDATIONS AND HOUSING LIMITED",
            "STRUCTURAL ENGINEER": "AMARNATH. R. BORAIAH, M.Tech Structural Engineering Grade-1 (RSE) Reg: No. TVLR/RSE/G-1/2023/02/004 #17, C-Block, R.V. Nagar, Ashoknagar, Chennai-83. Ph: 9731303187",
            "REGISTERED ENGINEER": "G.A VAMSI VARMA K, B.Arch Regd.No.CA/2012/55059 4th Floor, Bootstart Co-working Rishab Arcade, Sanjay Nagar Main Road, Raj Mahal Villas 2nd Stage, Bengaluru, Karnataka-560001, Mobile:9538974027"
        }

        Now analyze the image and extract with maximum accuracy. Return ONLY the JSON object.
        """

        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            return {
                "status": False,
                "statusCode": 400,
                "message": "Failed to encode image",
                "data": {}
            }
        response = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise document analysis AI that extracts exact text from engineering documents. You always output valid JSON without any additional text, explanations, or markdown formatting."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                },
            ],
            max_tokens=1500,  
            temperature=0.1,  
            top_p=0.1,     )

        raw_result = response.choices[0].message.content.strip()
        print(f"[DEBUG] Raw API response: {raw_result}")
        try:
            cleaned = re.sub(r'```json\s*|\s*```', '', raw_result).strip()            
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)            
            parsed = json.loads(cleaned)            
            required_fields = ["PROJECT TITLE", "OWNER SIGNATURE", "STRUCTURAL ENGINEER", "REGISTERED ENGINEER"]
            for field in required_fields:
                if field not in parsed:
                    parsed[field] = ""
                else:
                    if isinstance(parsed[field], str):
                        parsed[field] = re.sub(r'\s+', ' ', parsed[field]).strip()                    
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parsing failed. Raw: {raw_result}")
            return {
                "status": False,
                "statusCode": 500,
                "message": f"Failed to parse JSON: {str(e)}",
                "data": {}
            }
        except Exception as e:
            print(f"[DEBUG] Processing error: {str(e)}")
            return {
                "status": False,
                "statusCode": 500,
                "message": f"Processing error: {str(e)}",
                "data": {}
            }
        extracted_data = {
            "PROJECT TITLE": parsed.get("PROJECT TITLE", ""),
            "OWNER SIGNATURE": parsed.get("OWNER SIGNATURE", ""),
            "STRUCTURAL ENGINEER": parsed.get("STRUCTURAL ENGINEER", ""),
            "REGISTERED ENGINEER": parsed.get("REGISTERED ENGINEER", "")
        }
        meaningful_data = False
        for key, value in extracted_data.items():
            if value and len(value.strip()) > 5:
                meaningful_data = True
                break

        if not meaningful_data:
            print("[DEBUG] No meaningful data extracted from image")
            return {
                "status": False,
                "statusCode": 404,
                "message": "No extractable data found in the image",
                "data": {}
            }
        extract_detail = process_structural_signatures(extracted_data)        
        final_data = {
            "PROJECT TITLE": extract_detail.get("PROJECT TITLE", ""),
            "OWNER SIGNATURE": extract_detail.get("OWNER SIGNATURE", ""),            
            "REGISTERED ENGINEER": extract_detail.get("REGISTERED ENGINEER", ""),
            "STRUCTURAL ENGINEER": extract_detail.get("STRUCTURAL ENGINEER", "") 
        }
        return {
            "status": True,
            "statusCode": 200,
            "message": "Successfully extracted document details",
            "PROJECT TITLE": final_data["PROJECT TITLE"],
            "OWNER SIGNATURE": final_data["OWNER SIGNATURE"],            
            "REGISTERED ENGINEER": final_data["REGISTERED ENGINEER"],
            "STRUCTURAL ENGINEER": final_data["STRUCTURAL ENGINEER"] 
        }
    except Exception as e:
        print(f"[ERROR] extract_pdf_details_from_image: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")        
        return {
            "status": False,
            "statusCode": 500,
            "message": f"Extraction failed: {str(e)}",
            "data": {}
        }


def extract_pdf_details_with_retry(image_path: str, max_retries: int = 2):
    for attempt in range(max_retries + 1):
        try:
            result = extract_pdf_details_from_image(image_path)            
            if result["status"] or result["statusCode"] in [400, 404]:
                return result                
            if attempt < max_retries:
                print(f"[DEBUG] Retry attempt {attempt + 1}/{max_retries}")
                import time
                time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries:
                return {
                    "status": False,
                    "statusCode": 500,
                    "message": f"All extraction attempts failed: {str(e)}",
                    "data": {}
                }    
    return {
        "status": False,
        "statusCode": 500,
        "message": "Extraction failed after all retries",
        "data": {}
    }