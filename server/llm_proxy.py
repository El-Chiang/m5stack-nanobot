"""Anthropic API 转发"""

import os
from anthropic import Anthropic


class LLMProxy:

    def __init__(self):
        self._client = Anthropic()  # 使用 ANTHROPIC_API_KEY 环境变量
        self._conversations: dict[str, list] = {}

    def chat(self, message: str, conversation_id: str) -> str:
        """发送消息并返回回复文字"""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        history = self._conversations[conversation_id]
        history.append({"role": "user", "content": message})

        response = self._client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=1024,
            system="你是一个运行在 M5Stack 设备上的 AI 助手。请用简洁的中文回复，每次回复控制在 100 字以内。",
            messages=history,
        )

        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})

        return reply
