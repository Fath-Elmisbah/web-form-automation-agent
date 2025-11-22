import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# Initialize the model
model = genai.GenerativeModel('gemini-2.5-flash')

def analyze_form_with_gemini(form_html, form_data):
    prompt = f"""
    Analyze this web form and map the provided data to the appropriate fields.
    
    FORM HTML:
    {form_html}
    
    DATA TO FILL:
    {form_data}
    
    Instructions:
    1. Identify each form field and its purpose
    2. Map data fields to appropriate form inputs
    3. Return CSS selectors and values in JSON format
    4. Skip signature fields
    5. Handle empty values appropriately
    
    Return JSON format:
    {{"actions": [{{"selector": "css_selector", "value": "field_value", "action": "fill/select/click"}}]}}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None

# Test the connection
try:
    test_response = model.generate_content("Say 'Connected successfully' in one word.")
    print(f"Gemini API connected: {test_response.text}")
except Exception as e:
    print(f"Gemini API error: {e}")
