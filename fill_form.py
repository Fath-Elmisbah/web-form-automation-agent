# fill_form.py (updated and hardened)

import os, json, time, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from prompts import LLM_PROMPT_TEMPLATE
from mock_data import mock_data

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
ALLOW_SUBMIT = os.getenv("ALLOW_SUBMIT", "false").lower() in ("1","true","yes")

genai.configure(api_key=API_KEY)

TEST_URL = "https://mendrika-alma.github.io/form-submission/"


def safe_json_extract(text):
    """Extracts first JSON array found in text."""
    json_match = re.search(r"\[[\s\S]*\]", text)
    if not json_match:
        raise ValueError(f"LLM returned no JSON array\n{text[:200]}")
    return json.loads(json_match.group(0))


def call_llm(form_html, data):
    prompt = LLM_PROMPT_TEMPLATE.format(form_html=form_html, data_json=json.dumps(data))

    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(prompt)

    # robust extraction
    raw = ""
    try:
        if resp and hasattr(resp, "text"):
            raw = resp.text
        else:
            raw = str(resp)
    except:
        raw = str(resp)

    # keep the JSON only
    return safe_json_extract(raw)


def find_by_label(page, label_text):
    if not label_text:
        return None
    try:
        label = page.query_selector(f"label:text('{label_text}')")
        if label:
            for_attr = label.get_attribute("for")
            if for_attr:
                el = page.query_selector(f"#{for_attr}")
                if el:
                    return el
        return None
    except:
        return None


def resolve_element(page, key, selector, label_hint):
    if not key:
        return None

    selector = (selector or "").strip()

    # 1️⃣ Direct selector
    if selector:
        el = page.query_selector(selector)
        if el:
            return el

    # 2️⃣ Label hint
    el = find_by_label(page, label_hint)
    if el:
        return el

    # 3️⃣ Best-effort heuristic (split nested key)
    frags = key.split('.') if isinstance(key, str) else []
    for frag in reversed(frags):
        if len(frag) < 2:
            continue  # too short
        guess = page.query_selector(
            f"input[name*='{frag}'], input[id*='{frag}'], textarea[name*='{frag}'], select[name*='{frag}']"
        )
        if guess:
            return guess

    return None


def apply_mapping(page, mapping):
    for entry in mapping:

        if not isinstance(entry, dict):
            print(f"[WARN] Invalid mapping element skipped: {entry}")
            continue

        key = entry.get("key")
        if not key:
            print(f"[WARN] Missing key in entry, skipping: {entry}")
            continue

        action = entry.get("action", "fill").lower()
        value = entry.get("value", "")
        selector = entry.get("selector", "")
        label_hint = entry.get("label_hint", "")

        el = resolve_element(page, key, selector, label_hint)

        if not el:
            print(f"[WARN] Element not found for: {key} (label={label_hint}, selector={selector})")
            continue

        tag = el.evaluate("e => e.tagName.toLowerCase()")

        try:
            if action == "fill":
                if tag in ("input", "textarea", "select"):
                    el.fill(str(value))
                else:
                    el.click()

            elif action == "select":
                try:
                    el.select_option(str(value))
                except:
                    el.fill(str(value))

            elif action == "check":
                if str(value).lower() in ("true", "yes", "y", "1"):
                    el.check()
                else:
                    el.uncheck()

            elif action == "click":
                el.click()

            print(f"[OK] {action.upper()} -> {key} = {value}")
            time.sleep(0.05)

        except Exception as e:
            print(f"[ERROR] while applying {key}: {e}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(TEST_URL)

        page.wait_for_selector("form, input")
        form_el = page.query_selector("form") or page.query_selector("input")
        form_html = form_el.inner_html()

        mapping = call_llm(form_html, mock_data)
        print("=== LLM Mapping Loaded ===")
        print(json.dumps(mapping, indent=2)[:1000])  # shorten output if huge

        apply_mapping(page, mapping)
        print("Done. Browser will remain open. Press 1 to submit, Enter to exit...")
        x = input()
        if ALLOW_SUBMIT and x == "1":
            submit = page.query_selector("button[type='submit'], input[type='submit']")
            if submit:
                submit.click()
                print("[SUBMIT] Form submitted.")

        print("Thank you")


if __name__ == "__main__":
    main()

