# fill_form.py

import os, json, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from prompts import LLM_PROMPT_BEST_GUESS, LLM_PROMPT_RESOLVE_CONFLICTS, LLM_PROMPT_EVALUATE_FINAL
from mock_data import mock_data

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
ALLOW_SUBMIT = os.getenv("ALLOW_SUBMIT", "false").lower() in ("1","true","yes")
genai.configure(api_key=API_KEY)

TEST_URL = "https://mendrika-alma.github.io/form-submission/"
VIDEO_DIR = "videos"

def call_llm(prompt):
    """Call the Gemini LLM and return text"""
    model = genai.GenerativeModel("gemini-2.5-flash")  # Fixed model name
    resp = model.generate_content(prompt)
    return getattr(resp, "text", str(resp))

def safe_json_extract(text):
    """
    Extracts the first valid JSON array from LLM output.
    Handles extra text before/after JSON.
    """
    import re, json

    matches = re.findall(r"\[\s*[\s\S]*?\s*\]", text)
    if not matches:
        raise ValueError(f"Failed to find JSON array in LLM output:\n{text[:300]}")

    # Use first match
    json_text = matches[0].strip()

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        # Try cleaning common issues (trailing commas)
        cleaned = re.sub(r",\s*]", "]", json_text)
        cleaned = re.sub(r",\s*}", "}", cleaned)
        return json.loads(cleaned)

def extract_editable_elements(page):
    """Get all input/textarea/select elements with better context"""
    elements = page.query_selector_all("input, textarea, select")
    editable = []
    
    for el in elements:
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        disabled = el.evaluate("e => e.disabled")
        readonly = el.evaluate("e => e.readOnly")
        
        if not disabled and not readonly:
            # Get better context including labels and surrounding text
            context = el.evaluate("""
                e => {
                    const label = e.labels?.[0]?.textContent || '';
                    const placeholder = e.placeholder || '';
                    const name = e.name || '';
                    const id = e.id || '';
                    const type = e.type || '';
                    const ariaLabel = e.getAttribute('aria-label') || '';
                    
                    // Get previous sibling text for context
                    let prevText = '';
                    let prev = e.previousElementSibling;
                    if (prev && prev.textContent) {
                        prevText = prev.textContent.trim();
                    }
                    
                    return {
                        html: e.outerHTML,
                        label: label,
                        placeholder: placeholder,
                        name: name,
                        id: id,
                        type: type,
                        ariaLabel: ariaLabel,
                        prevText: prevText
                    };
                }
            """)
            
            editable.append({
                "selector": el,  # Keep element handle for later use
                "context": context
            })
    
    return editable

def get_all_best_guesses(editable_elements, data):
    """Single LLM call to get best guesses for ALL elements"""
    print("🔍 Getting best guesses for all elements...")
    
    # Prepare elements context for LLM
    elements_context = []
    for i, el in enumerate(editable_elements):
        context = el["context"]
        elements_context.append({
            "element_id": i,
            "html": context["html"][:200],  # Limit HTML length
            "label": context["label"],
            "placeholder": context["placeholder"], 
            "name": context["name"],
            "id": context["id"],
            "type": context["type"],
            "ariaLabel": context["ariaLabel"],
            "prevText": context["prevText"]
        })
    
    prompt = LLM_PROMPT_BEST_GUESS.format(
        elements_json=json.dumps(elements_context, indent=2),
        data_json=json.dumps(data, indent=2)
    )
    
    text = call_llm(prompt)
    return safe_json_extract(text)

def resolve_all_conflicts(assignments):
    """Single LLM call to resolve all conflicts"""
    print("🔄 Resolving conflicts...")
    prompt = LLM_PROMPT_RESOLVE_CONFLICTS.format(
        assignments_json=json.dumps(assignments, indent=2)
    )
    text = call_llm(prompt)
    return safe_json_extract(text)

def evaluate_all_final(assignments):
    """Single LLM call to evaluate all final assignments"""
    print("✅ Evaluating final assignments...")
    prompt = LLM_PROMPT_EVALUATE_FINAL.format(
        assignments_json=json.dumps(assignments, indent=2)
    )
    text = call_llm(prompt)
    return safe_json_extract(text)

def apply_mapping(page, assignments, editable_elements):
    """Apply the final mapping to the form"""
    print("📝 Filling form...")
    
    filled_count = 0
    for assignment in assignments:
        element_id = assignment.get("element_id")
        best_guess = assignment.get("best_guess", {})
        
        if element_id is None or not best_guess:
            continue
            
        try:
            el_handle = editable_elements[element_id]["selector"]
            value = best_guess.get("value")
            
            if value is not None and value != "":
                # Fill the field
                el_handle.fill(str(value))
                filled_count += 1
                print(f"   ✓ Filled: {best_guess.get('key')} = '{value}'")
                time.sleep(0.1)  # Small delay for visual effect
                
        except Exception as e:
            print(f"   ✗ Failed to fill {best_guess.get('key')}: {e}")
    
    print(f"🎯 Successfully filled {filled_count} fields")

def main():
    print("🚀 Starting form automation...")
    
    with sync_playwright() as p:
        # Setup browser with video recording
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            record_video_dir=VIDEO_DIR,
            viewport={"width": 1200, "height": 800}
        )
        page = context.new_page()
        
        print("🌐 Navigating to form...")
        page.goto(TEST_URL)
        page.wait_for_selector("form, input, textarea, select")
        time.sleep(2)  # Let page load completely

        # Step 1: Extract editable elements
        print("📄 Extracting form elements...")
        editable_elements = extract_editable_elements(page)
        print(f"📋 Found {len(editable_elements)} editable elements")

        # Step 2: Single LLM call for all best guesses
        assignments = get_all_best_guesses(editable_elements, mock_data)
        print(f"🤖 Generated {len(assignments)} initial assignments")

        # Step 3: Single LLM call to resolve conflicts
        assignments = resolve_all_conflicts(assignments)
        print(f"🔄 Resolved to {len(assignments)} assignments")

        # Step 4: Single LLM call for final evaluation
        final_assignments = evaluate_all_final(assignments)
        print(f"✅ Finalized {len(final_assignments)} assignments")

        # Step 5: Fill form
        apply_mapping(page, final_assignments, editable_elements)

        # Completion
        print("\n🎉 Form filling completed!")
        print("Press Enter to exit, or type '1' + Enter to submit...")
        
        user_input = input()
        if ALLOW_SUBMIT and user_input == "1":
            submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button")
            if submit_btn:
                submit_btn.click()
                print("📤 Form submitted!")
                time.sleep(2)
        
        # Close browser and show video path
        context.close()
        browser.close()
        
        # Show video file info
        if os.path.exists(VIDEO_DIR):
            video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.webm')]
            if video_files:
                latest_video = sorted(video_files)[-1]
                print(f"🎥 Recording saved: {os.path.join(VIDEO_DIR, latest_video)}")

if __name__ == "__main__":
    main()
