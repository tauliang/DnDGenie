from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer


CHAT_MODEL = "test-chat-model"
EMBEDDING_MODEL = "test-embedding-model"


def embedding_for(text: str) -> list[float]:
    seed = sum(ord(char) for char in text)
    return [((seed + index) % 31) / 31.0 for index in range(8)]


class MockLMStudioServer:
    def __init__(
        self,
        chat_response: str = "Encounter table: Goblin scouts in the woods.",
        readiness_response: str = "OK",
        html_pages: dict[str, str] | None = None,
        models: list[str] | None = None,
    ):
        self.chat_response = chat_response
        self.readiness_response = readiness_response
        self.html_pages = html_pages or {}
        self.models = models or [CHAT_MODEL, EMBEDDING_MODEL]
        self.requested_paths: list[str] = []

    def __enter__(self):
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def send_json(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                mock.requested_paths.append(self.path)
                if self.path == "/v1/models":
                    self.send_json(
                        200,
                        {
                            "object": "list",
                            "data": [
                                {"id": model, "object": "model"}
                                for model in mock.models
                            ],
                        },
                    )
                    return

                if self.path in mock.html_pages:
                    body = mock.html_pages[self.path].encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                self.send_json(404, {"error": "not found"})

            def do_POST(self) -> None:
                mock.requested_paths.append(self.path)
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")

                if self.path == "/v1/embeddings":
                    raw_input = payload.get("input", [])
                    inputs = raw_input if isinstance(raw_input, list) else [raw_input]
                    self.send_json(
                        200,
                        {
                            "object": "list",
                            "model": payload.get("model", EMBEDDING_MODEL),
                            "data": [
                                {
                                    "object": "embedding",
                                    "index": index,
                                    "embedding": embedding_for(str(text)),
                                }
                                for index, text in enumerate(inputs)
                            ],
                        },
                    )
                    return

                if self.path == "/v1/chat/completions":
                    request_text = json.dumps(payload)
                    content = (
                        mock.readiness_response
                        if "Reply with the word OK" in request_text
                        else mock.chat_response
                    )
                    self.send_json(
                        200,
                        {
                            "id": "chatcmpl-test",
                            "object": "chat.completion",
                            "created": 0,
                            "model": payload.get("model", CHAT_MODEL),
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": content,
                                    },
                                    "finish_reason": "stop",
                                }
                            ],
                        },
                    )
                    return

                self.send_json(404, {"error": "not found"})

            def log_message(self, format: str, *args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"
