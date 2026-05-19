import os
import json
import requests
import sys
from dotenv import load_dotenv

# Force stdout to use UTF-8 to prevent encoding errors on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
model = "openai/gpt-oss-120b:free"
url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

print("Using API Key:", api_key[:10] + "..." if api_key else "None")

# 1. First API call with reasoning
messages = [
    {
        "role": "user",
        "content": "How many r's are in the word 'strawberry'?"
    }
]

payload = {
    "model": model,
    "messages": messages,
    "reasoning": {"enabled": True}
}

print("\n--- Sending First Request ---")
try:
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print("Status Code:", resp.status_code)
    
    if resp.status_code == 200:
        data = resp.json()
        message = data["choices"][0]["message"]
        
        print("\nAssistant Response:")
        print(message.get("content"))
        
        print("\nReasoning Summary:")
        print(message.get("reasoning"))
        
        reasoning_details = message.get("reasoning_details")
        print("\nReasoning Details Found:", "Yes" if reasoning_details else "No")
        
        # 2. Second API call - model continues reasoning from where it left off
        follow_up_messages = [
            {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
            {
                "role": "assistant",
                "content": message.get("content"),
                "reasoning_details": reasoning_details  # Pass back unmodified
            },
            {"role": "user", "content": "Are you sure? Think carefully."}
        ]
        
        payload2 = {
            "model": model,
            "messages": follow_up_messages,
            "reasoning": {"enabled": True}
        }
        
        print("\n--- Sending Second Request (with reasoning history) ---")
        resp2 = requests.post(url, headers=headers, json=payload2, timeout=30)
        print("Status Code:", resp2.status_code)
        
        if resp2.status_code == 200:
            data2 = resp2.json()
            message2 = data2["choices"][0]["message"]
            
            print("\nAssistant Final Response:")
            print(message2.get("content"))
            
            print("\nFinal Reasoning Summary:")
            print(message2.get("reasoning"))
        else:
            print("Error in second request:", resp2.text)
            
    else:
        print("Error in first request:", resp.text)
        
except Exception as e:
    print("An exception occurred:", e)
