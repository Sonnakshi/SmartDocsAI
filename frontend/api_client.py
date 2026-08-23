import requests
from typing import Optional, Dict, Any, List

API_BASE_URL = "http://127.0.0.1:8000"


class SmartDocsAPIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # ========== SYSTEM ==========

    def health_check(self) -> requests.Response:
        url = f"{self.base_url}/health"
        try:
            return requests.get(url, timeout=3)
        except Exception:
            res = requests.Response()
            res.status_code = 503
            return res

    # ========== AUTH & PROFILE ==========

    def register(self, email: str, password: str, full_name: Optional[str] = None) -> requests.Response:
        url = f"{self.base_url}/register"
        payload = {"email": email, "password": password, "full_name": full_name}
        return requests.post(url, json=payload)

    def login(self, email: str, password: str) -> requests.Response:
        url = f"{self.base_url}/login"
        data = {"username": email, "password": password}
        return requests.post(url, data=data)

    def get_me(self, token: str) -> requests.Response:
        url = f"{self.base_url}/me"
        return requests.get(url, headers=self._get_headers(token))

    def update_me(self, full_name: str, token: str) -> requests.Response:
        url = f"{self.base_url}/me"
        payload = {"full_name": full_name}
        return requests.patch(url, json=payload, headers=self._get_headers(token))

    # ========== DOCUMENTS ==========

    def upload_document(self, file_bytes: bytes, filename: str, token: str) -> requests.Response:
        url = f"{self.base_url}/documents/upload"
        files = {"file": (filename, file_bytes)}
        return requests.post(url, files=files, headers=self._get_headers(token))

    def list_documents(self, token: str, filename_filter: Optional[str] = None) -> requests.Response:
        url = f"{self.base_url}/documents"
        params = {}
        if filename_filter:
            params["filename"] = filename_filter
        return requests.get(url, params=params, headers=self._get_headers(token))

    def download_document(self, document_id: str, token: str) -> requests.Response:
        url = f"{self.base_url}/documents/{document_id}/download"
        return requests.get(url, headers=self._get_headers(token), stream=True)

    def delete_document(self, document_id: str, token: str) -> requests.Response:
        url = f"{self.base_url}/documents/{document_id}"
        return requests.delete(url, headers=self._get_headers(token))

    # ========== AI CHAT (RAG WITH MEMORY) ==========

    def chat(
        self,
        question: str,
        token: str,
        document_id: Optional[str] = None,
        top_k: int = 4,
        min_score: float = 0.20,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> requests.Response:
        url = f"{self.base_url}/chat"
        payload: Dict[str, Any] = {
            "question": question,
            "top_k": top_k,
            "min_score": min_score,
        }
        if document_id:
            payload["document_id"] = document_id
        if chat_history:
            cleaned_history = [
                {"role": m["role"], "content": m["content"]}
                for m in chat_history
                if "role" in m and "content" in m
            ]
            payload["chat_history"] = cleaned_history

        return requests.post(url, json=payload, headers=self._get_headers(token))

    # ========== PERSISTENT CHAT THREADS ==========

    def get_thread_history(self, scope_id: str, token: str) -> requests.Response:
        url = f"{self.base_url}/chats/{scope_id}"
        return requests.get(url, headers=self._get_headers(token))

    def clear_thread_history(self, scope_id: str, token: str) -> requests.Response:
        url = f"{self.base_url}/chats/{scope_id}/clear"
        return requests.post(url, headers=self._get_headers(token))

    # ========== ADMIN ==========

    def list_all_users(self, token: str) -> requests.Response:
        url = f"{self.base_url}/users/"
        return requests.get(url, headers=self._get_headers(token))