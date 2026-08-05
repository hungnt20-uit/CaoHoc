from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

from traffic_es.llm.client import LLMClient


def _load_dotenv_if_present() -> None:
    """Load variables from .env if present, without requiring python-dotenv."""
    env_candidates = []
    cwd = Path.cwd()
    env_candidates.append(cwd / ".env")
    env_candidates.append(Path(__file__).resolve().parents[2] / ".env")

    for env_path in env_candidates:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv_if_present()


class OpenAILLM(LLMClient):
    """Provider OpenAI. Import `openai` trễ để test/heuristic không cần thư viện."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from openai import OpenAI

        self.model = model or os.environ.get("TRAFFIC_ES_LLM_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, system: str, user: str, **kw) -> str:
        r = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""


class AnthropicLLM(LLMClient):
    """Provider Anthropic (Claude). Dùng Messages API; import `anthropic` trễ."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        import anthropic

        # Mặc định Opus 4.8; đổi rẻ hơn bằng TRAFFIC_ES_LLM_MODEL=claude-haiku-4-5
        self.model = model or os.environ.get("TRAFFIC_ES_LLM_MODEL", "claude-opus-4-8")
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def complete(self, system: str, user: str, **kw) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system + "\nChỉ trả về JSON hợp lệ, không kèm giải thích.",
            messages=[{"role": "user", "content": user}],
        )
        # Lấy khối text đầu tiên (Opus 4.8 không kèm thinking khi bỏ tham số thinking)
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""


DEFAULT_LOCAL_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
DEFAULT_LOCAL_BASE_URL = "http://localhost:8000/v1"


_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")


def normalize_base_url(url: str) -> str:
    """Chuẩn hóa URL người dùng dán vào thành gốc API tương thích OpenAI (…/v1).

    Chấp nhận cả URL Colab/cloudflared dán thiếu scheme hoặc thiếu hậu tố `/v1`,
    và cả trường hợp dán nguyên đường dẫn endpoint.
    """
    u = (url or "").strip().rstrip("/")
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        # Máy cục bộ không có chứng chỉ TLS; đoán https ở đây sẽ vỡ bắt tay SSL.
        scheme = "http" if u.split("/", 1)[0].split(":", 1)[0] in _LOCAL_HOSTS else "https"
        u = f"{scheme}://{u}"
    for suffix in ("/chat/completions", "/completions"):
        if u.endswith(suffix):
            u = u[: -len(suffix)]
            break
    if not u.endswith("/v1"):
        u += "/v1"
    return u


class LocalOpenAICompatLLM(LLMClient):
    """LLM local qua API tương thích OpenAI (Colab + Qwen, vLLM, Ollama, LM Studio…).

    Máy chủ tự dựng thường không hỗ trợ `response_format=json_object`, nên yêu cầu JSON
    được đưa vào system prompt; tầng phân tích JSON phía trên đã có sẵn cơ chế bóc
    ```-fence và trích khối {...} nên vẫn an toàn.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 300.0,
        max_tokens: int = 1024,
    ):
        from openai import OpenAI

        self.base_url = normalize_base_url(
            base_url or os.environ.get("TRAFFIC_ES_LOCAL_BASE_URL", DEFAULT_LOCAL_BASE_URL)
        )
        # Để trống nghĩa là tự dò từ server; xem resolved_model().
        self.model = model or os.environ.get("TRAFFIC_ES_LOCAL_MODEL") or None
        self.max_tokens = max_tokens
        self.client = OpenAI(
            base_url=self.base_url,
            # Server local không kiểm khóa, nhưng SDK bắt buộc phải có giá trị.
            api_key=api_key or os.environ.get("TRAFFIC_ES_LOCAL_API_KEY") or "local",
            timeout=timeout,
            max_retries=1,
        )

    def served_models(self) -> List[str]:
        return [m.id for m in getattr(self.client.models.list(), "data", [])]

    def resolved_model(self) -> str:
        """Tên model để gửi lên server, tự dò nếu người dùng không chỉ định.

        Mỗi máy chủ đặt tên một kiểu — vLLM theo `--served-model-name` (ví dụ `coder-7b`
        cho `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`), Ollama theo tag, LM Studio theo đường
        dẫn — nên đoán tên là dính 404. Hỏi thẳng server rồi nhớ lại cho các lần sau.
        """
        if self.model:
            return self.model
        try:
            served = self.served_models()
        except Exception:
            served = []
        self.model = served[0] if served else DEFAULT_LOCAL_MODEL
        return self.model

    def complete(self, system: str, user: str, **kw) -> str:
        r = self.client.chat.completions.create(
            model=self.resolved_model(),
            temperature=0,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": system + "\nChỉ trả về JSON hợp lệ, không kèm giải thích.",
                },
                {"role": "user", "content": user},
            ],
        )
        return r.choices[0].message.content or ""

    def health(self) -> Tuple[bool, str]:
        """Kiểm tra server có sống không — dùng cho nút thử kết nối trên UI."""
        try:
            served = self.served_models()
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
        if self.model and served and self.model not in served:
            return False, (
                f"Server sống nhưng không có model '{self.model}'. "
                f"Tên đúng: {', '.join(served)} (hoặc để trống ô Model để tự dò)."
            )
        return True, "kết nối OK · sẽ gọi model: " + (
            self.model or (served[0] if served else DEFAULT_LOCAL_MODEL)
        )


def make_default_llm() -> Optional[LLMClient]:
    """Chọn LLMClient theo môi trường; None nếu không có gì khả dụng (→ heuristic).

    Ưu tiên theo TRAFFIC_ES_LLM_PROVIDER (anthropic|openai|local) nếu đặt; ngược lại
    dùng cái nào có sẵn — key Anthropic, key OpenAI, rồi tới server local.
    """
    provider = os.environ.get("TRAFFIC_ES_LLM_PROVIDER", "").strip().lower()
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_local = bool(os.environ.get("TRAFFIC_ES_LOCAL_BASE_URL"))

    order: Tuple[str, ...]
    if provider in ("anthropic", "openai", "local"):
        order = (provider,)
    else:
        order = ("anthropic", "openai", "local")

    for name in order:
        try:
            if name == "anthropic" and has_anthropic:
                return AnthropicLLM()
            if name == "openai" and has_openai:
                return OpenAILLM()
            # Provider "local" chỉ định rõ thì chạy dù chưa đặt base URL (dùng mặc định).
            if name == "local" and (has_local or provider == "local"):
                return LocalOpenAICompatLLM()
        except Exception:
            continue
    return None


def default_mode_label() -> str:
    """Nhãn chế độ để hiển thị trên UI (không khởi tạo client)."""
    provider = os.environ.get("TRAFFIC_ES_LLM_PROVIDER", "").strip().lower()
    local_label = "LLM local (Colab · {})".format(
        os.environ.get("TRAFFIC_ES_LOCAL_MODEL", DEFAULT_LOCAL_MODEL)
    )
    if provider == "local":
        return local_label
    if (provider == "anthropic" or not provider) and os.environ.get("ANTHROPIC_API_KEY"):
        model = os.environ.get("TRAFFIC_ES_LLM_MODEL", "claude-opus-4-8")
        return f"LLM (Anthropic · {model})"
    if provider in ("", "openai") and os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("TRAFFIC_ES_LLM_MODEL", "gpt-4o-mini")
        return f"LLM (OpenAI · {model})"
    if not provider and os.environ.get("TRAFFIC_ES_LOCAL_BASE_URL"):
        return local_label
    return "Heuristic offline"
