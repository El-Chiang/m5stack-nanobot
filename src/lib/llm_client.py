"""与中继服务的 HTTP 通信"""

import ujson
import urequests


class LLMClient:

    def __init__(self, server_url):
        self._url = server_url.rstrip("/")

    def send_text(self, message, conversation_id=None):
        """发送文字消息，返回 dict 或 None"""
        payload = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        try:
            resp = urequests.post(
                self._url + "/api/chat",
                headers={"Content-Type": "application/json"},
                data=ujson.dumps(payload),
            )
            if resp.status_code == 200:
                result = resp.json()
                resp.close()
                return result
            resp.close()
        except Exception as e:
            print("llm_client send_text error:", e)
        return None

    def send_audio(self, audio_data, conversation_id=None):
        """发送录音数据，返回 dict 或 None"""
        headers = {"Content-Type": "application/octet-stream"}
        if conversation_id:
            headers["X-Conversation-Id"] = conversation_id

        try:
            resp = urequests.post(
                self._url + "/api/voice",
                headers=headers,
                data=audio_data,
            )
            if resp.status_code == 200:
                result = resp.json()
                resp.close()
                return result
            resp.close()
        except Exception as e:
            print("llm_client send_audio error:", e)
        return None

    def fetch_audio(self, audio_url):
        """下载音频文件，返回 bytes 或 None"""
        try:
            url = audio_url if audio_url.startswith("http") else self._url + audio_url
            resp = urequests.get(url)
            if resp.status_code == 200:
                data = resp.content
                resp.close()
                return data
            resp.close()
        except Exception as e:
            print("llm_client fetch_audio error:", e)
        return None
