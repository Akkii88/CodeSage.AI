import os
import json
import re
import time
import random
import requests
from dotenv import load_dotenv
from services.file_parser import extract_ast_structure

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBlXcMzdRHgDUZgqG2dgS3D6nbnYRla3uI")

def safe_parse_llm_output(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return [{
        "file": "unknown",
        "line": 0,
        "severity": "low",
        "title": "Parsing error",
        "description": "LLM output could not be parsed as valid JSON",
        "suggestion": "Check model response format",
        "confidence": 10
    }]

def generate_review(code: str, file_path: str):
    ast_data = extract_ast_structure(code)
    if not ast_data.get("functions") and not ast_data.get("classes") and not ast_data.get("imports"):
        ast_data = {"note": "partial parse"}
    system_prompt = (
        "You are a senior Python security and code quality reviewer.\n\n"
        "Analyze the following Python file.\n\n"
        "Return ONLY valid JSON in this exact format:\n\n"
        '{\n  "issues": [\n    {\n      "severity": "high|medium|low",\n      "title": "short issue title",\n      "description": "why this is a problem",\n      "suggestion": "how to fix it"\n    }\n  ]\n}\n\n'
        "Rules:\n"
        "- Do not invent issues.\n"
        "- Return empty issues array if code is good.\n"
        "- Include confidence (0-100) in each issue.\n"
        "- Focus on: security problems, exception handling, unsafe file handling, bad practices, performance problems, missing validation, resource leaks, maintainability"
    )

    user_message = f"""FILE: {file_path}

CODE:
{code}"""

    print("FILE:", file_path)
    print("CODE LENGTH:", len(code))
    print("PROMPT SENT:", user_message[:500])

    def analyze_with_llm(prompt, retries=5):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        headers = {"Content-Type": "application/json"}

        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                elif response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    print(f"[RATE LIMITED] Waiting {wait_time:.2f}s...")
                    time.sleep(wait_time)
                else:
                    print("LLM ERROR:", response.text)
                    return '{"issues": []}'
            except Exception as e:
                print("REQUEST FAILED:", str(e))
                time.sleep(2)
        return '{"issues": []}'

    prompt = system_prompt + "\n\n" + user_message
    return analyze_with_llm(prompt)