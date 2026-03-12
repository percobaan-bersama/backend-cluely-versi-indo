import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

LLM_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Kamu adalah asisten meeting dan interview yang cerdas bernama Cluely. 
Tugasmu adalah:
1. Memahami konteks percakapan meeting atau interview yang sedang berlangsung
2. Memberikan jawaban yang relevan, informatif, dan profesional
3. Membantu menjawab pertanyaan-pertanyaan yang diajukan selama meeting/interview
4. Memberikan insight dan saran yang berguna berdasarkan konteks percakapan

Aturan:
- Jawab dalam bahasa yang sama dengan pertanyaan (Indonesia atau English)
- Berikan jawaban yang concise tapi komprehensif
- Jika pertanyaan tidak jelas, minta klarifikasi
- Gunakan format yang mudah dibaca (bullet points jika perlu)
- Pertahankan konteks dari percakapan sebelumnya"""

async def get_response(conversation_history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=LLM_MODEL,
        temperature=0.7,
        max_tokens=2048,
        top_p=0.9,
        stream=True
    )

    return chat_completion.choices[0].message.content
