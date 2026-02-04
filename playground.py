import requests
import json

API_KEY = ""  # <-- put your key here

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    # Optional but recommended by OpenRouter
    "HTTP-Referer": "http://localhost",
    "X-Title": "OpenRouter Key Test"
}

data = {
    "model": "allenai/olmo-3.1-32b-instruct",  # cheap + good for testing
    "messages": [
        {"role": "user", "content": "Say hello in one short sentence."}
    ]
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()

    result = response.json()
    print("✅ API Key works!\n")
    print("Model reply:\n")
    print(result["choices"][0]["message"]["content"])

except requests.exceptions.HTTPError as e:
    print("❌ HTTP Error:", e)
    print(response.text)

except Exception as e:
    print("❌ Something went wrong:", e)
