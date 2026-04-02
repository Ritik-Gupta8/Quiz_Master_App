import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Free-tier model fallback chain — tries each in order until one works
GEMINI_MODELS = [
    "gemini-2.5-flash-lite-preview-06-17",  # newest lite, separate quota
    "gemini-2.0-flash-lite",                # 2.0 lite, separate quota
    "gemini-2.5-flash",                     # 2.5 flash
    "gemini-2.0-flash",                     # 2.0 flash (last resort)
]

def get_api_key():
    return os.getenv("GOOGLE_API_KEY")


def _try_generate(model_name, prompt):
    """Try generating content with a given model. Returns (text, None) on success or (None, error_str) on failure."""
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    # Extract text robustly
    if hasattr(response, "text") and response.text:
        return response.text.strip(), None
    if hasattr(response, "candidates") and response.candidates:
        try:
            return response.candidates[0].content.parts[0].text.strip(), None
        except Exception:
            pass
    return None, "Empty response from model."


def generate_quiz_questions(subject, chapter, num_questions=10, level="Medium", grade="10th"):
    """Generate quiz questions using Gemini AI.
    Returns a list of dicts with keys:
    question_statement, option1, option2, option3, option4, correct_option.
    """
    api_key = get_api_key()
    if not api_key:
        return {"error": "Google API Key (GOOGLE_API_KEY) not found. Ensure your .env file is set up correctly."}

    genai.configure(api_key=api_key)

    # Keep prompt concise to minimise token usage on the free tier
    prompt = (
        f"Generate exactly {num_questions} multiple-choice quiz questions "
        f"for Grade {grade} students on Subject: {subject}, Topic: {chapter}, "
        f"Difficulty: {level}.\n"
        f"Return ONLY a JSON array. Each element must have these keys: "
        f"question_statement, option1, option2, option3, option4, correct_option "
        f"(correct_option is 'option1', 'option2', 'option3', or 'option4').\n"
        f"No extra text, no markdown fences."
    )

    last_error = "All Gemini models failed."
    for model_name in GEMINI_MODELS:
        try:
            content, err = _try_generate(model_name, prompt)
            if err:
                last_error = f"{model_name}: {err}"
                continue

            # Strip markdown fences if present
            if content.startswith("```json"):
                content = content[len("```json"):].strip()
            elif content.startswith("```"):
                content = content[3:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

            # Parse JSON
            try:
                questions = json.loads(content)
                return questions  # success — return immediately
            except json.JSONDecodeError as jde:
                last_error = f"{model_name}: JSON parse error — {jde.msg}"
                continue  # try next model

        except Exception as e:
            err_str = str(e)
            last_error = f"{model_name}: {err_str}"
            # Only skip to next model on quota/rate/not-found errors
            if any(code in err_str for code in ["429", "404", "quota", "RESOURCE_EXHAUSTED", "not found"]):
                continue
            # For other unexpected errors break immediately
            break

    return {"error": last_error}
