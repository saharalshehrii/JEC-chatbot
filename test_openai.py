from dotenv import load_dotenv
import openai
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "ما هي عاصمة اليابان؟"}],
    )
    print("✅ الاتصال ناجح، الرد:", response["choices"][0]["message"]["content"])
except Exception as e:
    print("❌ فشل الاتصال بـ OpenAI:", e)
