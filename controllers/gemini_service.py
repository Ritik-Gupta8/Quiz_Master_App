import google.generativeai as genai
import os
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Free-tier model fallback chain — ordered by most likely to have remaining quota.
# Each model has its OWN per-day / per-minute quota bucket on the free tier,
# so a fresh model will succeed even if another is exhausted.
GEMINI_MODELS = [
    "gemini-1.5-flash-8b",                  # lightest, 1500 RPD free quota
    "gemini-1.5-flash-8b-001",              # pinned version, separate bucket
    "gemini-1.5-flash",                     # 1500 RPD free quota
    "gemini-1.5-flash-001",                 # pinned version, separate bucket
    "gemini-2.0-flash-lite",               # 2.0 lite, separate quota
    "gemini-2.5-flash-lite-preview-06-17", # newest lite, separate quota
    "gemini-2.5-flash",                    # 2.5 flash (may have lower free quota)
    "gemini-2.0-flash",                    # 2.0 flash (last resort)
]

# Errors that mean we should try the next model
SKIP_CODES = ["429", "404", "quota", "RESOURCE_EXHAUSTED", "not found", "503", "overloaded"]


def get_api_key():
    return os.getenv("GOOGLE_API_KEY")


def _try_generate(model_name, prompt):
    """Try generating content with a given model.
    Returns (text, None) on success or (None, error_str) on failure.
    """
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
    Falls back across multiple model IDs when quota is exceeded.
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
        f"Return ONLY a JSON array. Each element must have these exact keys: "
        f"question_statement, option1, option2, option3, option4, correct_option "
        f"(correct_option must be one of: 'option1', 'option2', 'option3', 'option4').\n"
        f"No markdown fences, no extra text — raw JSON only."
    )

    last_error = "All Gemini models failed or quota exhausted across all free-tier models."
    for model_name in GEMINI_MODELS:
        try:
            content, err = _try_generate(model_name, prompt)
            if err:
                last_error = f"{model_name}: {err}"
                continue

            # Strip markdown fences if the model added them anyway
            content = content.strip()
            if content.startswith("```json"):
                content = content[len("```json"):].strip()
            elif content.startswith("```"):
                content = content[3:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

            # Parse JSON
            try:
                questions = json.loads(content)
                if isinstance(questions, list) and len(questions) > 0:
                    return questions  # success
                last_error = f"{model_name}: Returned empty or non-list JSON."
                continue
            except json.JSONDecodeError as jde:
                last_error = f"{model_name}: JSON parse error — {jde.msg}"
                continue

        except Exception as e:
            err_str = str(e)
            last_error = f"{model_name}: {err_str[:200]}"  # truncate long API errors

            if any(code in err_str for code in SKIP_CODES):
                # Pause before trying next model to avoid burst-firing RPM limit
                if "429" in err_str and "per_day" not in err_str.lower() and "PerDay" not in err_str:
                    time.sleep(3)  # wait 3s on per-minute rate limit
                else:
                    time.sleep(0.5)  # small pause between model switches
                continue  # try next model

            # Unexpected (non-quota) error — stop immediately
            break

    return {"error": last_error}
