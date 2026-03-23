import google.generativeai as genai
import os
import json
import re

# Configure Gemini API
# In a real production app, this should be fetched from environment variables
# For now, we'll anticipate GOOGLE_API_KEY being set in the environment
API_KEY = os.environ.get("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_quiz_questions(subject, chapter, num_questions, level="Medium"):
    """
    Generates quiz questions using Gemini AI.
    Returns a list of dictionaries, each containing question_statement, 
    option1, option2, option3, option4, and correct_option.
    """
    if not API_KEY:
        return {"error": "Google API Key not configured. Please set GOOGLE_API_KEY environment variable."}

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Generate {num_questions} multiple-choice questions for the subject '{subject}' and chapter '{chapter}'.
    Difficulty level: {level}.
    
    Each question must have:
    1. A clear question statement.
    2. Exactly 4 options (option1, option2, option3, option4).
    3. The correct option identified as 'option1', 'option2', 'option3', or 'option4'.
    
    Format the output as a valid JSON list of objects like this:
    [
      {{
        "question_statement": "...",
        "option1": "...",
        "option2": "...",
        "option3": "...",
        "option4": "...",
        "correct_option": "option1"
      }}
    ]
    
    Provide ONLY the JSON array. No markdown code blocks, no preamble.
    """

    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Clean up potential markdown code blocks if the AI ignored the "ONLY JSON" instruction
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        questions = json.loads(content)
        return questions
    except Exception as e:
        return {"error": str(e)}
