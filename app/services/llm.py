import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

MODELS = [
   "llama-3.1-8b-instant"
]

SYSTEM_PROMPT = (
    "Anda berperan sebagai seorang Calon Karyawan (Candidate/Interviewee) yang sedang menjalani proses wawancara kerja. "
    "Lawan bicara Anda adalah pihak HR (Human Resources) atau pewawancara. "
    "Tugas Anda adalah menjawab pertanyaan wawancara dengan profesional, sopan, jujur, dan antusias. "
    "Berikan jawaban dalam Bahasa Indonesia yang formal namun tetap ramah. "
    "Tetaplah rendah hati namun percaya diri dalam memaparkan kualifikasi dan pengalaman Anda."
)

async def get_response(conversation_history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    last_error = None
    for model in MODELS:
        try:
            chat_completion = await client.chat.completions.create(
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

async def get_streaming_response(conversation_history: list[dict]):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)

    last_error = None
    for model in MODELS:
        try:
            completion = await client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
                stream=True
            )
            async for chunk in completion:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
            return 
        except Exception as e:
            print(f"Error with model {model} (streaming): {e}")
            last_error = e
            continue
    
    yield f"Maaf, semua model LLM sedang tidak tersedia. Error: {str(last_error)}"
