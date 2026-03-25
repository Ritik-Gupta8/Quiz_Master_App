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

def generate_quiz_questions(subject, chapter, num_questions=20, level="Medium", grade="10th"):
    """
    Generates quiz questions using Gemini AI.
    Returns a list of dictionaries, each containing question_statement, 
    option1, option2, option3, option4, and correct_option.
    """
    if not API_KEY:
        return {"error": "Google API Key not configured. Please set GOOGLE_API_KEY environment variable."}

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Generate exactly {num_questions} multiple-choice questions for Grade {grade} students.
    Subject: {subject}
    Topic/Chapter: {chapter}
    Difficulty level: {level}
    
    Requirements:
    1. Each question must have a clear, age-appropriate statement for Grade {grade}.
    2. Exactly 4 unique options (option1, option2, option3, option4).
    3. The correct option must be identified as 'option1', 'option2', 'option3', or 'option4'.
    
    Return ONLY a valid JSON array of objects with the following keys:
    "question_statement", "option1", "option2", "option3", "option4", "correct_option".
    
    Example format:
    [
      {{
        "question_statement": "What is the capital of France?",
        "option1": "Paris",
        "option2": "London",
        "option3": "Berlin",
        "option4": "Madrid",
        "correct_option": "option1"
      }}
    ]
    
    Do not include any text outside the JSON array.
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
