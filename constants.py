from enum import IntEnum, unique


@unique
class ChatType(IntEnum):
    DEEPSEEK = 0  # Deepseek
    CHATGPT = 1  # ChatGPT
    CHATGLM = 2  # ChatGLM
    ZHIPU = 3  # 智谱AI
    BARD = 4  # Bard
    OLLAMA = 5  # Ollama
    TIGERBOT = 6  # TigerBot
    XINGHUO_WEB = 7  # 讯飞星火

    @staticmethod
    def is_in_chat_types(chat_type: int) -> bool:
        if chat_type in [ChatType.TIGERBOT.value, ChatType.CHATGPT.value,
                         ChatType.XINGHUO_WEB.value, ChatType.CHATGLM.value,
                         ChatType.BARD.value, ChatType.ZHIPU.value,
                         ChatType.OLLAMA.value, ChatType.DEEPSEEK.value]:
            return True
        return False

    @staticmethod
    def help_hint() -> str:
        return f"{ChatType.DEEPSEEK}: Deepseek, {ChatType.CHATGPT}: ChatGPT, {ChatType.CHATGLM}: ChatGLM, {ChatType.ZHIPU}: 智谱AI, {ChatType.BARD}: Bard, {ChatType.OLLAMA}: Ollama, {ChatType.TIGERBOT}: TigerBot, {ChatType.XINGHUO_WEB}: 讯飞星火"
