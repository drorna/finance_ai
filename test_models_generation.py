import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API Key found.")
    exit()

genai.configure(api_key=api_key)

print("Testing generation with available models...")
working_models = []

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Testing {m.name}...", end=" ")
            try:
                model = genai.GenerativeModel(m.name)
                response = model.generate_content("Hello")
                print("SUCCESS")
                working_models.append(m.name)
            except Exception as e:
                print(f"FAILED: {e}")
except Exception as e:
    print(f"Listing failed: {e}")

print("\n--- RESULTS ---")
if working_models:
    print(f"Working models: {working_models}")
else:
    print("No models worked.")
