from helper import validate_image, encode_image_to_base64,process_structural_signatures
import openai
import os
import json
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
        You are an accurate assistant analyzing an engineering/building plan PDF page.  
        Your job is to extract specific structured fields.  

        ### Extraction Fields:
        - PROJECT TITLE  
        - SEALS (list of seal contents, each broken into Name, Address, Phone Number)

        ### Rules:
        1. PROJECT TITLE:
           - If label 'PROJECT TITLE' or 'TITLE' is present, return its value.  
           - If missing, find the full text line that starts with 'PLAN SHOWING'.  
           - If nothing is found, return "".

        2. OWNER SIGNATURE → Search for labels such as:
            - OWNER SIGNATURE
            - SIGNATURE OF OWNER
            - OWNER'S SIGNATURE
            - APPLICANT  

        3. STRUCTURAL ENGINEER → Search for labels such as:
            - STRUCTURAL ENGINEER
            - SIGNATURE OF STRUCTURAL ENGINEER
            - STRUCTURAL ENGINEER'S SIGNATURE
            - REGISTERED STRUCTURAL ENGINEER  

        4. REGISTERED ENGINEER → Search for labels such as:
            - REGISTERED ENGINEER
            - ARCHITECT SIGNATURE
            - SIGNATURE OF ARCHITECT
            - LICENSED SURVEYOR
            - ARCHITECT/LICENSED SURVEYOR SIGNATURE  

            ### Output Formatting Rules:
            1. Return only the exact matched text as it appears in the document (do not rephrase, translate, or modify).  
            2. If a field cannot be found, return an empty string "" for that field.  
            3. The response must be strictly valid JSON only (no extra text, no markdown, no explanations).  
            4. Ensure that all field names in the JSON exactly match the extraction fields defined above.  

            ### Example Output:
            {
                "PROJECT TITLE": "PLAN SHOWING THE PROPOSED CONSTRUCTION OF STILT + 5 FLOORS WITH 93 D.UNITS AFFORDABLE HOUSING RESIDENTIAL BUILDING AT S.NOS: 69/9D1A1 & 70/2A1, EAST COAST ROAD, KANATHUR REDDIKUPPAM VILLAGE, THIRUPORUR TALUK, CHENGALPET DISTRICT.",
                "OWNER SIGNATURE": "For SIDHARTH FOUNDATIONS AND HOUSING LIMITED",
                "STRUCTURAL ENGINEER": "AMARNATH. R. BORAIAH, M.Tech Structural Engineering Grade-1 (RSE) Reg: No. TVLR/RSE/G-1/2023/02/004 #17, C-Block, R.V. Nagar, Ashoknagar, Chennai-83. Ph: 9731303187",
                "REGISTERED ENGINEER": "G.A VAMSI VARMA K, B.Arch Regd.No.CA/2012/55059 4th Floor, Bootstart Co-working Rishab Arcade, Sanjay Nagar Main Road, Raj Mahal Villas 2nd Stage, Bengaluru, Karnataka-560001, Mobile:9538974027"
            }

            Now extract and return the results in the same JSON format.
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
                {"role": "system", "content": "You are a helpful assistant that outputs strict JSON only."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                },
            ],
            max_tokens=800,
        )
        raw_result = response.choices[0].message.content.strip()
        try:
            cleaned = raw_result.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
        except Exception:
            return {
                "status": False,
                "statusCode": 500,
                "message": f"Failed to parse JSON: {raw_result}",
                "data": {}
            }        
        data = {
           "PROJECT TITLE": parsed.get("PROJECT TITLE", ""),
            "OWNER SIGNATURE": parsed.get("OWNER SIGNATURE", ""),
            "STRUCTURAL ENGINEER": parsed.get("STRUCTURAL ENGINEER", ""),
            "REGISTERED ENGINEER": parsed.get("REGISTERED ENGINEER", "")
        }
        extract_detail = process_structural_signatures(data)
        return {
            "status": True,
            "statusCode": 200,
            "message": "Success",
            "PROJECT TITLE": extract_detail.get("PROJECT TITLE", ""),
            "OWNER SIGNATURE": extract_detail.get("OWNER SIGNATURE", ""),            
            "REGISTERED ENGINEER": extract_detail.get("REGISTERED ENGINEER", "")
        }
    except Exception as e:
        print("Error in extract_pdf_details_from_image:", str(e))
        return {
            "status": False,
            "statusCode": 500,
            "message": str(e),
            "data": {}
        }
