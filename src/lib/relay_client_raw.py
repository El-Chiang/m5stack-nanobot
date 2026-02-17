"""与 relay 服务通信（raw socket HTTP）。"""

import ujson


class RelayClientRaw:

    def __init__(self, relay_server):
        self._relay_server = relay_server
        self._session_id = None

    def clear_session(self):
        self._session_id = None

    def send_chat(self, message):
        payload = {"message": message}
        if self._session_id:
            payload["session_id"] = self._session_id

        host, port = self._parse_relay()
        resp_body = self._http_post(host, port, "/api/chat", ujson.dumps(payload))
        data = ujson.loads(resp_body)

        self._session_id = data.get("session_id", self._session_id)
        reply = data.get("reply", "")
        mood = data.get("mood") or data.get("emotion")
        return reply, mood

    def _parse_relay(self):
        url = self._relay_server.replace("http://", "")
        if ":" in url:
            host, port = url.split(":", 1)
            return host, int(port.split("/")[0])
        return url.split("/")[0], 80

    def _http_post(self, host, port, path, body):
        import socket

        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket()
        sock.connect(addr)

        body_bytes = body.encode("utf-8")
        header = (
            "POST %s HTTP/1.0\r\n"
            "Host: %s:%d\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: %d\r\n"
            "\r\n"
        ) % (path, host, port, len(body_bytes))
        sock.send(header.encode("utf-8"))
        sock.send(body_bytes)

        chunks = []
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            chunks.append(chunk)
        sock.close()

        raw = b"".join(chunks).decode()
        idx = raw.find("\r\n\r\n")
        if idx >= 0:
            return raw[idx + 4:]
        return raw
