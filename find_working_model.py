import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found.")
    exit()

genai.configure(api_key=api_key)

candidates = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-pro"
]

print("Scanning for working models...")
for name in candidates:
    print(f"Testing {name}...", end=" ", flush=True)
    try:
        model = genai.GenerativeModel(name)
        # Try a very simple token count or generation
        response = model.generate_content("Hi")
        print("SUCCESS! ✅")
        print(f"FOUND WORKING MODEL: {name}")
        break
    except Exception as e:
        if "404" in str(e):
            print("Not Found (404)")
        elif "429" in str(e):
             print("Rate Limited (429)")
        else:
            print(f"Error: {str(e)[:50]}...")
