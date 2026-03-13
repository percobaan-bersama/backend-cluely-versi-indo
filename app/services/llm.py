import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b"
]

async def get_response(conversation_history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    last_error = None
    for model in MODELS:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error with model {model}: {e}")
            last_error = e
            continue
    
    return f"Maaf, semua model LLM sedang tidak tersedia. Error terakhir: {str(last_error)}"
