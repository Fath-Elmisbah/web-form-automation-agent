# prompts.py

# Single LLM call for ALL elements
LLM_PROMPT_BEST_GUESS = """
You are an expert form-filling AI. Analyze ALL form elements at once and map them to the provided data.

FORM ELEMENTS:
{elements_json}

AVAILABLE DATA:
{data_json}

Your task:
1. For EACH element, identify the most likely data field match
2. Provide a confidence score (1-5) for each match
3. Include reasoning for your choices
4. Consider: labels, placeholders, names, IDs, surrounding text, and field types

Return JSON array with this format for ALL elements:
[
  {{
    "element_id": 0,
    "best_guess": {{
      "key": "attorney.first_name", 
      "value": "John", 
      "score": 5, 
      "reasoning": "Label matches 'First Name' and data has attorney.first_name"
    }},
    "second_guess": {{
      "key": "client.first_name", 
      "value": "Jane", 
      "score": 3, 
      "reasoning": "Alternative match but attorney context is stronger"
    }}
  }},
  ... // more elements
]

Important: Return ONLY the JSON array, no other text.
"""

# Single LLM call for ALL conflict resolution
LLM_PROMPT_RESOLVE_CONFLICTS = """
You are an expert form-filling AI. Resolve ALL field assignment conflicts at once.

CURRENT ASSIGNMENTS:
{assignments_json}

Conflict Resolution Rules:
1. If a data field is assigned to multiple elements, keep ONLY the highest confidence match
2. Remove assignments with confidence score <= 2
3. Prefer matches where field purpose clearly aligns with data semantics
4. Ensure each data field is used at most once (unless the form has duplicate fields)

Return the cleaned JSON array with the same format, containing only the best assignments.

Important: Return ONLY the JSON array, no other text.
"""

# Single LLM call for ALL final evaluation
LLM_PROMPT_EVALUATE_FINAL = """
You are an expert form-filling AI. Perform final quality check on ALL assignments.

ASSIGNMENTS:
{assignments_json}

Evaluation Criteria:
1. Remove any assignment with confidence score <= 2
2. Remove assignments where the value doesn't match the field type (e.g., email in phone field)
3. Ensure no critical data fields are missing if obvious matches exist
4. Keep only assignments that make logical sense

Return the final JSON array ready for form filling.

Important: Return ONLY the JSON array, no other text.
"""
