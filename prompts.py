LLM_PROMPT_TEMPLATE = """
You are an expert in DOM understanding and web form automation.

Goal:
Return a JSON array describing how to fill the given form using the provided mock data.

Strict rules:
- ONLY include fields that exist in the given form HTML.
- NEVER invent or hallucinate fields.
- If a field is in data_json but NOT in the form → ignore it, but be reasonable.
- If the form has fields not in data_json → ignore them., but be reasonable.
- We want to fill all what we can, but clearly unrelated fields should be skipped.
- Always first attempt selecting by a unique ID selector (#elementID).
- If no ID exists, then use the best available CSS selector based on:
  * name attribute
  * label text binding
  * input[type]
- Detect correct action automatically:
  * text, email, number, date, textarea → "fill"
  * select dropdown → "select"
  * checkbox or radio → "check"
  * button type="submit" → "click"
- Include `label_hint` ONLY if useful for fallback matching.
- NEVER use complex nth-child selectors unless unavoidable.
- MUST always return well-formed JSON ONLY.
- NO explanations, no markdown.

JSON Schema:
[
  {{
    "key": "<data key>",
    "selector": "<CSS selector>",
    "action": "fill | select | check | click",
    "value": <insert correct data value>,
    "label_hint": "<visible label text or ''>"
  }}
]

Input:
FORM_HTML:
{{form_html}}

DATA_JSON:
{{data_json}}

Output:
Strict valid JSON array only, nothing else.
"""

