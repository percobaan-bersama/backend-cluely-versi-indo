import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

MEMORY_WINDOW_TURNS = 4


def trim_history_to_window(history: list[dict], k: int = MEMORY_WINDOW_TURNS) -> list[dict]:
    """
    Memangkas riwayat percakapan menjadi hanya k turn terakhir.
    1 turn = 1 pesan user + 1 pesan assistant (total 2 * k pesan).
    History yang dikembalikan tidak termasuk system prompt.
    """
    non_system = [m for m in history if m.get("role") != "system"]
    windowed = non_system[-(2 * k):]
    return windowed


def build_langchain_messages(system_prompt: str, history: list[dict]) -> list:
    """
    Konversi history (list of dict) ke format LangChain messages.
    History sudah diharapkan sudah di-trim oleh trim_history_to_window.
    """
    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


class LLM:
    def __init__(self):
        self.models = [
            "llama-3.1-8b-instant"
        ]
        self.SYSTEM_PROMPT = (
            "Anda berperan sebagai seorang Calon Karyawan (Candidate/Interviewee) yang sedang menjalani proses wawancara kerja. "
            "Lawan bicara Anda adalah pihak HR (Human Resources) atau pewawancara. "
            "Tugas Anda adalah menjawab pertanyaan wawancara dengan profesional, sopan, jujur, dan antusias. "
            "Berikan jawaban dalam Bahasa Indonesia yang formal namun tetap ramah. "
            "Tetaplah rendah hati namun percaya diri dalam memaparkan kualifikasi dan pengalaman Anda."
        )

    def _get_chat_model(self, model_name: str) -> ChatGroq:
        return ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7,
            max_tokens=2048,
        )

    async def get_response(self, conversation_history: list[dict]) -> str:
        """
        Mengambil respons LLM. Hanya 4 turn terakhir dari conversation_history
        yang akan dikirim ke model.
        """
        windowed = trim_history_to_window(conversation_history, k=MEMORY_WINDOW_TURNS)
        messages = build_langchain_messages(self.SYSTEM_PROMPT, windowed)

        last_error = None
        for model_name in self.models:
            try:
                llm = self._get_chat_model(model_name)
                response = await llm.ainvoke(messages)
                return response.content
            except Exception as e:
                print(f"Error with model {model_name}: {e}")
                last_error = e
                continue

        return f"Maaf, semua model LLM sedang tidak tersedia. Error terakhir: {str(last_error)}"

    async def get_streaming_response(self, conversation_history: list[dict]):
        """
        Streaming response dari LLM. Hanya 4 turn terakhir dari conversation_history
        yang akan dikirim ke model.
        """
        windowed = trim_history_to_window(conversation_history, k=MEMORY_WINDOW_TURNS)
        messages = build_langchain_messages(self.SYSTEM_PROMPT, windowed)

        last_error = None
        for model_name in self.models:
            try:
                llm = self._get_chat_model(model_name)
                async for chunk in llm.astream(messages):
                    token = chunk.content
                    if token:
                        yield token
                return
            except Exception as e:
                print(f"Error with model {model_name} (streaming): {e}")
                last_error = e
                continue

        yield f"Maaf, semua model LLM sedang tidak tersedia. Error: {str(last_error)}"
