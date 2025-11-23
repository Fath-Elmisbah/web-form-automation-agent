# prompts.py

# Step 1: Best guess + second best guess for each editable field
LLM_PROMPT_BEST_GUESS = """
You are an expert form-filling AI.

Given the following HTML snippet of a form element:

{element_html}

Consider the attributes:
- Text right before the element (label, placeholder, etc.)
- ID
- Class / CSS selectors
- Name

You also have access to the following JSON data for possible values:
{data_json}

Your task:
1. Identify the most likely data field from the JSON that matches this element, and give it a confidence score from 1-5.
2. Identify a second-best guess, if any, also with score 1-5.
3. Give reasoning for both guesses.

Return JSON with the following format:
[
  {{
    "element_selector": "{element_selector}",
    "best_guess": {{"key": "attorney.first_name", "value": "John", "score": 5, "reasoning": "..."}},
    "second_guess": {{"key": "attorney.middle_name", "value": "Michael", "score": 3, "reasoning": "..."}}
  }}
]
"""

# Step 2: Resolve conflicts (same JSON field mapped to multiple elements)
LLM_PROMPT_RESOLVE_CONFLICTS = """
You are an expert form-filling AI.

Given the following list of element-to-data-field assignments:

{assignments_json}

Some JSON fields may have been assigned to multiple elements. Resolve conflicts using:
- Choose the element with the highest confidence score.
- If tied, prefer shorter distance between label and value in text/HTML.
- Remove low-confidence matches (score <= 2) if necessary.

Return a cleaned JSON list with the same format.
"""

# Step 3: Evaluate final assignments
LLM_PROMPT_EVALUATE_FINAL = """
You are an expert form-filling AI.

Given the following final element-to-data-field assignments:

{assignments_json}

Evaluate each assignment:
- If confidence seems too low (<= 2) or mismatched, remove it.
- Do not hallucinate values.
- Keep only likely correct mappings.

Return the cleaned JSON list ready for filling.
"""

