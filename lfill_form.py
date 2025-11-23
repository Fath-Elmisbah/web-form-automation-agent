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
    model = genai.GenerativeModel("gemini-2.5-flash")
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
    """Get all input/textarea/select elements"""
    elements = page.query_selector_all("input, textarea, select")
    editable = []
    for el in elements:
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        disabled = el.evaluate("e => e.disabled")
        readonly = el.evaluate("e => e.readOnly")
        if not disabled and not readonly:
            selector = el.evaluate("e => e.outerHTML")
            editable.append({"selector": selector, "handle": el})
    return editable

def get_best_guesses(page, editable_elements, data):
    """Ask LLM for best guess + second guess for each element"""
    all_assignments = []
    for el in editable_elements:
        element_html = el['selector']
        prompt = LLM_PROMPT_BEST_GUESS.format(
            element_html=element_html,
            element_selector=element_html[:50],
            data_json=json.dumps(data)
        )
        text = call_llm(prompt)
        try:
            assignments = safe_json_extract(text)
            all_assignments.extend(assignments)
        except Exception as e:
            print(f"[ERROR] LLM failed for element: {element_html[:50]}... {e}")
    return all_assignments

def resolve_conflicts(assignments):
    prompt = LLM_PROMPT_RESOLVE_CONFLICTS.format(assignments_json=json.dumps(assignments))
    text = call_llm(prompt)
    return safe_json_extract(text)

def evaluate_final(assignments):
    prompt = LLM_PROMPT_EVALUATE_FINAL.format(assignments_json=json.dumps(assignments))
    text = call_llm(prompt)
    return safe_json_extract(text)

def apply_mapping(page, mapping):
    for entry in mapping:
        el_handle = None
        try:
            el_handle = page.query_selector(f"{entry['element_selector']}")
        except:
            continue
        if not el_handle:
            continue
        best = entry.get("best_guess", {})
        value = best.get("value")
        if value is not None:
            tag = el_handle.evaluate("e => e.tagName.toLowerCase()")
            try:
                if tag in ("input", "textarea", "select"):
                    el_handle.fill(str(value))
                else:
                    el_handle.click()
                print(f"[OK] Filled {best.get('key')} = {value}")
                time.sleep(0.05)
            except Exception as e:
                print(f"[ERROR] Filling {best.get('key')}: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(record_video_dir=VIDEO_DIR)
        page = context.new_page()
        page.goto(TEST_URL)
        page.wait_for_selector("form, input, textarea, select")

        # Step 1: Extract editable elements
        editable_elements = extract_editable_elements(page)
        print(f"Found {len(editable_elements)} editable elements.")

        # Step 2: Best guesses from LLM
        assignments = get_best_guesses(page, editable_elements, mock_data)
        print(f"Initial assignments from LLM: {len(assignments)}")

        # Step 3: Resolve conflicts
        assignments = resolve_conflicts(assignments)
        print(f"After conflict resolution: {len(assignments)}")

        # Step 4: Evaluate final assignments
        final_assignments = evaluate_final(assignments)
        print(f"Final assignments to fill: {len(final_assignments)}")

        # Step 5: Fill form
        apply_mapping(page, final_assignments)

        print("Form filled. Press Enter to exit, 1 to submit...")
        x = input()
        if ALLOW_SUBMIT and x == "1":
            submit = page.query_selector("button[type='submit'], input[type='submit']")
            if submit:
                submit.click()
                print("[SUBMIT] Form submitted.")

        context.close()
        video_files = os.listdir(VIDEO_DIR)
        if video_files:
            print("Video saved at:", os.path.join(VIDEO_DIR, video_files[-1]))
        browser.close()

if __name__ == "__main__":
    main()

