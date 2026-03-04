"""cmdop-sdkrouter — CMDOP skill wrapper for SDKRouter unified AI SDK."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from cmdop_skill import Arg, Skill

skill = Skill()

# ---------------------------------------------------------------------------
# Lazy client
# ---------------------------------------------------------------------------

_client = None


def _get_client(api_key: str | None = None):
    """Get or create SDKRouter client (lazy singleton)."""
    global _client
    if _client is None:
        from sdkrouter import SDKRouter

        _client = SDKRouter(api_key=api_key) if api_key else SDKRouter()
    return _client


# ═══════════════════════════════════════════════════════════════════════════
# CHAT (2 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def chat(
    message: str = Arg(help="User message", required=True),
    model: str = Arg("--model", help="Model ID", default="openai/gpt-4o"),
    system: str = Arg("--system", help="System prompt", default=None),
    temperature: float = Arg("--temperature", help="Sampling temperature", default=None),
    max_tokens: int = Arg("--max-tokens", help="Max tokens", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Send a chat completion request."""
    client = _get_client(api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    kwargs = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**kwargs)
    return {
        "model": resp.model,
        "content": resp.choices[0].message.content,
        "usage": resp.usage.model_dump() if resp.usage else None,
    }


@skill.command
def chat_stream(
    message: str = Arg(help="User message", required=True),
    model: str = Arg("--model", help="Model ID", default="openai/gpt-4o"),
    system: str = Arg("--system", help="System prompt", default=None),
    temperature: float = Arg("--temperature", help="Sampling temperature", default=None),
    max_tokens: int = Arg("--max-tokens", help="Max tokens", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Stream a chat completion (prints tokens to stdout)."""
    client = _get_client(api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    kwargs = {"model": model, "messages": messages, "stream": True}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    chunks = []
    for chunk in client.chat.completions.create(**kwargs):
        delta = chunk.choices[0].delta.content if chunk.choices[0].delta else None
        if delta:
            print(delta, end="", flush=True)
            chunks.append(delta)
    print()
    sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════
# VISION (3 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def vision_analyze(
    image_url: str = Arg("--image-url", help="Image URL to analyze", default=None),
    image_path: str = Arg("--image-path", help="Local image path", default=None),
    prompt: str = Arg("--prompt", help="Analysis prompt", default=None),
    model: str = Arg("--model", help="Vision model", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Analyze an image using vision AI."""
    client = _get_client(api_key)
    kwargs = {}
    if image_url:
        kwargs["image_url"] = image_url
    if image_path:
        kwargs["image_path"] = image_path
    if prompt:
        kwargs["prompt"] = prompt
    if model:
        kwargs["model"] = model
    result = client.vision.analyze(**kwargs)
    return result.model_dump()


@skill.command
def vision_ocr(
    image_url: str = Arg("--image-url", help="Image URL for OCR", default=None),
    image_path: str = Arg("--image-path", help="Local image path", default=None),
    mode: str = Arg("--mode", help="OCR mode", default=None),
    language_hint: str = Arg("--language-hint", help="Language hint", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Extract text from an image via OCR."""
    client = _get_client(api_key)
    kwargs = {}
    if image_url:
        kwargs["image_url"] = image_url
    if image_path:
        kwargs["image_path"] = image_path
    if mode:
        kwargs["mode"] = mode
    if language_hint:
        kwargs["language_hint"] = language_hint
    result = client.vision.ocr(**kwargs)
    return result.model_dump()


@skill.command
def vision_models(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List available vision models."""
    client = _get_client(api_key)
    result = client.vision.models()
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO (3 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def audio_transcribe(
    file: str = Arg(help="Audio file path", required=True),
    model: str = Arg("--model", help="STT model", default="whisper-1"),
    language: str = Arg("--language", help="Language code", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Transcribe audio to text (speech-to-text)."""
    client = _get_client(api_key)
    kwargs = {"model": model}
    if language:
        kwargs["language"] = language
    result = client.audio.transcribe(file, **kwargs)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return {"text": str(result)}


@skill.command
def audio_speech(
    text: str = Arg(help="Text to convert to speech", required=True),
    output: str = Arg("--output", help="Output file path", default="speech.mp3"),
    model: str = Arg("--model", help="TTS model", default="tts-1"),
    voice: str = Arg("--voice", help="Voice name", default="nova"),
    speed: float = Arg("--speed", help="Speech speed", default=1.0),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Convert text to speech audio file."""
    client = _get_client(api_key)
    result = client.audio.speech(
        input=text, model=model, voice=voice, speed=speed,
    )
    out_path = Path(output)
    out_path.write_bytes(result.content)
    return {"file": str(out_path), "size": out_path.stat().st_size}


@skill.command
def audio_speech_stream(
    text: str = Arg(help="Text to convert to speech", required=True),
    output: str = Arg("--output", help="Output file path", default="speech.mp3"),
    model: str = Arg("--model", help="TTS model", default="tts-1"),
    voice: str = Arg("--voice", help="Voice name", default="nova"),
    speed: float = Arg("--speed", help="Speech speed", default=1.0),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Stream text-to-speech to a file."""
    client = _get_client(api_key)
    out_path = Path(output)
    total = 0
    with out_path.open("wb") as f:
        for chunk in client.audio.speech_stream(
            input=text, model=model, voice=voice, speed=speed,
        ):
            if hasattr(chunk, "data"):
                f.write(chunk.data)
                total += len(chunk.data)
    return {"file": str(out_path), "size": total}


# ═══════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION (6 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def image_generate(
    prompt: str = Arg(help="Image generation prompt", required=True),
    negative_prompt: str = Arg("--negative-prompt", help="Negative prompt", default=None),
    model: str = Arg("--model", help="Image gen model", default=None),
    size: str = Arg("--size", help="Image size (e.g. 1024x1024)", default=None),
    quality: str = Arg("--quality", help="Quality level", default=None),
    style: str = Arg("--style", help="Style", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Generate an image synchronously."""
    client = _get_client(api_key)
    kwargs = {"prompt": prompt}
    if negative_prompt:
        kwargs["negative_prompt"] = negative_prompt
    if model:
        kwargs["model"] = model
    if size:
        kwargs["size"] = size
    if quality:
        kwargs["quality"] = quality
    if style:
        kwargs["style"] = style
    result = client.image_gen.generate(**kwargs)
    return result.model_dump()


@skill.command
def image_generate_async(
    prompt: str = Arg(help="Image generation prompt", required=True),
    negative_prompt: str = Arg("--negative-prompt", help="Negative prompt", default=None),
    model: str = Arg("--model", help="Image gen model", default=None),
    size: str = Arg("--size", help="Image size", default=None),
    quality: str = Arg("--quality", help="Quality level", default=None),
    style: str = Arg("--style", help="Style", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Start async image generation (returns job ID)."""
    client = _get_client(api_key)
    kwargs = {"prompt": prompt}
    if negative_prompt:
        kwargs["negative_prompt"] = negative_prompt
    if model:
        kwargs["model"] = model
    if size:
        kwargs["size"] = size
    if quality:
        kwargs["quality"] = quality
    if style:
        kwargs["style"] = style
    result = client.image_gen.generate_async(**kwargs)
    return result.model_dump()


@skill.command
def image_wait(
    generation_id: str = Arg(help="Generation ID to wait for", required=True),
    timeout: float = Arg("--timeout", help="Timeout in seconds", default=300.0),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Wait for async image generation to complete."""
    client = _get_client(api_key)
    result = client.image_gen.wait_for_completion(generation_id, timeout=timeout)
    return result.model_dump()


@skill.command
def image_list(
    search: str = Arg("--search", help="Search filter", default=None),
    ordering: str = Arg("--ordering", help="Ordering", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List image generations."""
    client = _get_client(api_key)
    kwargs = {}
    if search:
        kwargs["search"] = search
    if ordering:
        kwargs["ordering"] = ordering
    result = client.image_gen.list(**kwargs)
    return {"items": [r.model_dump() for r in result]}


@skill.command
def image_get(
    generation_id: str = Arg(help="Generation ID", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get image generation details."""
    client = _get_client(api_key)
    result = client.image_gen.get(generation_id)
    return result.model_dump()


@skill.command
def image_options(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List available image generation options (models, sizes, styles)."""
    client = _get_client(api_key)
    result = client.image_gen.options()
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# SEARCH (4 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def search(
    query: str = Arg(help="Search query", required=True),
    model: str = Arg("--model", help="Model for answer synthesis", default=None),
    max_tokens: int = Arg("--max-tokens", help="Max tokens", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Perform a web search with AI-synthesized answer."""
    client = _get_client(api_key)
    kwargs = {"query": query}
    if model:
        kwargs["model"] = model
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    result = client.search.query(**kwargs)
    return result.model_dump()


@skill.command
def search_fetch(
    url: str = Arg(help="URL to fetch and analyze", required=True),
    prompt: str = Arg("--prompt", help="Analysis prompt", default=None),
    model: str = Arg("--model", help="Model", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Fetch a URL and analyze its content."""
    client = _get_client(api_key)
    kwargs = {"url": url}
    if prompt:
        kwargs["prompt"] = prompt
    if model:
        kwargs["model"] = model
    result = client.search.fetch(**kwargs)
    return result.model_dump()


@skill.command
def search_async(
    query: str = Arg(help="Search query", required=True),
    wait: bool = Arg("--wait", help="Wait for completion", action="store_true", default=False),
    mode: str = Arg("--mode", help="Search mode", default=None),
    task_prompt: str = Arg("--task-prompt", help="Task prompt for deep search", default=None),
    model: str = Arg("--model", help="Model", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Start async deep search (returns job UUID or waits)."""
    client = _get_client(api_key)
    kwargs = {"query": query, "wait": wait}
    if mode:
        kwargs["mode"] = mode
    if task_prompt:
        kwargs["task_prompt"] = task_prompt
    if model:
        kwargs["model"] = model
    result = client.search.query_async(**kwargs)
    return result.model_dump()


@skill.command
def search_list(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List search requests."""
    client = _get_client(api_key)
    result = client.search.list()
    return {"items": [r.model_dump() for r in result]}


# ═══════════════════════════════════════════════════════════════════════════
# CDN (5 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def cdn_upload(
    file: str = Arg("--file", help="File path to upload", default=None),
    url: str = Arg("--url", help="URL to upload from", default=None),
    filename: str = Arg("--filename", help="Override filename", default=None),
    ttl: str = Arg("--ttl", help="Time-to-live (e.g. 7d, 30d)", default=None),
    public: bool = Arg("--public", help="Make file public", action="store_true", default=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Upload a file to CDN."""
    client = _get_client(api_key)
    kwargs = {"is_public": public}
    if file:
        kwargs["file"] = Path(file)
    if url:
        kwargs["url"] = url
    if filename:
        kwargs["filename"] = filename
    if ttl:
        kwargs["ttl"] = ttl
    result = client.cdn.upload(**kwargs)
    return result.model_dump()


@skill.command
def cdn_get(
    uuid: str = Arg(help="File UUID", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get CDN file details."""
    client = _get_client(api_key)
    result = client.cdn.get(uuid)
    return result.model_dump()


@skill.command
def cdn_list(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List CDN files."""
    client = _get_client(api_key)
    result = client.cdn.list(page=page, page_size=page_size)
    return result.model_dump()


@skill.command
def cdn_delete(
    uuid: str = Arg(help="File UUID to delete", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Delete a CDN file."""
    client = _get_client(api_key)
    ok = client.cdn.delete(uuid)
    return {"deleted": ok, "uuid": uuid}


@skill.command
def cdn_stats(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get CDN usage statistics."""
    client = _get_client(api_key)
    result = client.cdn.stats()
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# TRANSLATOR (4 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def translate(
    text: str = Arg(help="Text to translate", required=True),
    target: str = Arg("--target", help="Target language code", default="en"),
    source: str = Arg("--source", help="Source language (auto-detect)", default="auto"),
    model: str = Arg("--model", help="Model override", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Translate text to target language."""
    client = _get_client(api_key)
    kwargs = {"text": text, "target_language": target, "source_language": source}
    if model:
        kwargs["model"] = model
    result = client.translator.translate(**kwargs)
    return {"translated": result, "target": target}


@skill.command
def translate_json(
    data: str = Arg(help="JSON string to translate", required=True),
    target: str = Arg("--target", help="Target language code", default="en"),
    source: str = Arg("--source", help="Source language (auto-detect)", default="auto"),
    model: str = Arg("--model", help="Model override", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Translate JSON object values to target language."""
    client = _get_client(api_key)
    parsed = json.loads(data)
    kwargs = {"data": parsed, "target_language": target, "source_language": source}
    if model:
        kwargs["model"] = model
    result = client.translator.translate_json(**kwargs)
    return {"translated": result, "target": target}


@skill.command
def detect_language(
    text: str = Arg(help="Text to detect language of", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Detect the language of text."""
    client = _get_client(api_key)
    lang = client.translator.detect_language(text)
    return {"language": lang, "text_preview": text[:100]}


@skill.command
def translate_stats(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get translator cache statistics."""
    client = _get_client(api_key)
    stats = client.translator.get_stats()
    return stats


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENTS (8 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def balance(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get account balance."""
    client = _get_client(api_key)
    result = client.payments.get_balance()
    return result.model_dump()


@skill.command
def currencies(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=50),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List available payment currencies."""
    client = _get_client(api_key)
    result = client.payments.list_currencies(page=page, page_size=page_size)
    return result.model_dump()


@skill.command
def deposit_estimate(
    currency: str = Arg(help="Currency code", required=True),
    amount: float = Arg(help="Amount in USD", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get deposit estimate for a currency amount."""
    client = _get_client(api_key)
    result = client.payments.get_deposit_estimate(currency, amount)
    return result.model_dump()


@skill.command
def payment_create(
    amount: float = Arg(help="Amount in USD", required=True),
    currency: str = Arg(help="Currency code", required=True),
    description: str = Arg("--description", help="Payment description", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Create a new payment."""
    client = _get_client(api_key)
    kwargs = {"amount_usd": amount, "currency_code": currency}
    if description:
        kwargs["description"] = description
    result = client.payments.create(**kwargs)
    return result.model_dump()


@skill.command
def payment_status(
    payment_id: str = Arg(help="Payment ID", required=True),
    refresh: bool = Arg("--refresh", help="Force refresh", action="store_true", default=False),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Check payment status."""
    client = _get_client(api_key)
    result = client.payments.check_status(payment_id, refresh=refresh)
    return result.model_dump()


@skill.command
def transactions(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    transaction_type: str = Arg("--type", help="Transaction type filter", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List transactions."""
    client = _get_client(api_key)
    kwargs = {"page": page, "page_size": page_size}
    if transaction_type:
        kwargs["transaction_type"] = transaction_type
    result = client.payments.list_transactions(**kwargs)
    return result.model_dump()


@skill.command
def withdrawal_create(
    amount: float = Arg(help="Amount in USD", required=True),
    currency: str = Arg(help="Currency code", required=True),
    wallet: str = Arg(help="Wallet address", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Create a withdrawal."""
    client = _get_client(api_key)
    result = client.payments.create_withdrawal(
        amount_usd=amount, currency_code=currency, wallet_address=wallet,
    )
    return result.model_dump()


@skill.command
def withdrawals(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    status: str = Arg("--status", help="Status filter", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List withdrawals."""
    client = _get_client(api_key)
    kwargs = {"page": page, "page_size": page_size}
    if status:
        kwargs["status"] = status
    result = client.payments.list_withdrawals(**kwargs)
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# PROXIES (7 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def proxy_list(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    search: str = Arg("--search", help="Search filter", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List proxies."""
    client = _get_client(api_key)
    kwargs = {"page": page, "page_size": page_size}
    if search:
        kwargs["search"] = search
    result = client.proxies.list(**kwargs)
    return result.model_dump()


@skill.command
def proxy_get(
    proxy_id: str = Arg(help="Proxy ID", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get proxy details."""
    client = _get_client(api_key)
    result = client.proxies.get(proxy_id)
    return result.model_dump()


@skill.command
def proxy_create(
    host: str = Arg(help="Proxy host", required=True),
    port: int = Arg(help="Proxy port", required=True),
    proxy_type: str = Arg("--type", help="Proxy type (http/socks5)", default=None),
    username: str = Arg("--username", help="Auth username", default=None),
    password: str = Arg("--password", help="Auth password", default=None),
    country: str = Arg("--country", help="Country code", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Create a new proxy."""
    client = _get_client(api_key)
    kwargs = {"host": host, "port": port}
    if proxy_type:
        kwargs["proxy_type"] = proxy_type
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password
    if country:
        kwargs["country"] = country
    result = client.proxies.create(**kwargs)
    return result.model_dump()


@skill.command
def proxy_update(
    proxy_id: str = Arg(help="Proxy ID", required=True),
    host: str = Arg("--host", help="New host", default=None),
    port: int = Arg("--port", help="New port", default=None),
    username: str = Arg("--username", help="New username", default=None),
    password: str = Arg("--password", help="New password", default=None),
    country: str = Arg("--country", help="New country", default=None),
    is_active: bool = Arg("--active", help="Set active status", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Update a proxy."""
    client = _get_client(api_key)
    kwargs = {}
    if host:
        kwargs["host"] = host
    if port:
        kwargs["port"] = port
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password
    if country:
        kwargs["country"] = country
    if is_active is not None:
        kwargs["is_active"] = is_active
    result = client.proxies.update(proxy_id, **kwargs)
    return result.model_dump()


@skill.command
def proxy_delete(
    proxy_id: str = Arg(help="Proxy ID to delete", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Delete a proxy."""
    client = _get_client(api_key)
    ok = client.proxies.delete(proxy_id)
    return {"deleted": ok, "proxy_id": proxy_id}


@skill.command
def proxy_healthy(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List healthy proxies."""
    client = _get_client(api_key)
    result = client.proxies.get_healthy()
    return {"items": [r.model_dump() for r in result]}


@skill.command
def proxy_test(
    proxy_id: str = Arg(help="Proxy ID to test", required=True),
    test_url: str = Arg("--url", help="Test URL", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Test a proxy connection."""
    client = _get_client(api_key)
    kwargs = {"proxy": proxy_id}
    if test_url:
        kwargs["test_url"] = test_url
    result = client.proxies.create_test(**kwargs)
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# SHORTLINKS (4 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def shortlink_create(
    url: str = Arg(help="Target URL to shorten", required=True),
    slug: str = Arg("--slug", help="Custom short slug", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Create a short link."""
    client = _get_client(api_key)
    kwargs = {}
    if slug:
        kwargs["custom_slug"] = slug
    result = client.shortlinks.create(url, **kwargs)
    return result.model_dump()


@skill.command
def shortlink_get(
    code: str = Arg(help="Short link code", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get short link details."""
    client = _get_client(api_key)
    result = client.shortlinks.get(code)
    return result.model_dump()


@skill.command
def shortlink_list(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List short links."""
    client = _get_client(api_key)
    result = client.shortlinks.list(page=page, page_size=page_size)
    return result.model_dump()


@skill.command
def shortlink_delete(
    code: str = Arg(help="Short link code to delete", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Delete a short link."""
    client = _get_client(api_key)
    ok = client.shortlinks.delete(code)
    return {"deleted": ok, "code": code}


# ═══════════════════════════════════════════════════════════════════════════
# KEYS (5 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def key_create(
    name: str = Arg(help="Key name", required=True),
    permission: str = Arg("--permission", help="Permission level (read/write)", default="write"),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Create a new API key."""
    client = _get_client(api_key)
    result = client.keys.create(name, permission=permission)
    return result.model_dump()


@skill.command
def key_list(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List API keys."""
    client = _get_client(api_key)
    result = client.keys.list(page=page, page_size=page_size)
    return result.model_dump()


@skill.command
def key_get(
    key_id: str = Arg(help="Key ID", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get API key details."""
    client = _get_client(api_key)
    result = client.keys.get(key_id)
    return result.model_dump()


@skill.command
def key_rotate(
    key_id: str = Arg(help="Key ID to rotate", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Rotate an API key (generates new secret)."""
    client = _get_client(api_key)
    result = client.keys.rotate(key_id)
    return result.model_dump()


@skill.command
def key_delete(
    key_id: str = Arg(help="Key ID to delete", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Delete an API key."""
    client = _get_client(api_key)
    ok = client.keys.delete(key_id)
    return {"deleted": ok, "key_id": key_id}


# ═══════════════════════════════════════════════════════════════════════════
# MODELS (4 commands)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def models_list(
    page: int = Arg("--page", help="Page number", default=1),
    page_size: int = Arg("--page-size", help="Items per page", default=20),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List available LLM models."""
    client = _get_client(api_key)
    result = client.llm_models.list(page=page, page_size=page_size)
    return result.model_dump()


@skill.command
def models_get(
    model_id: str = Arg(help="Model ID", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Get model details."""
    client = _get_client(api_key)
    result = client.llm_models.get(model_id)
    return result.model_dump()


@skill.command
def models_cost(
    model_id: str = Arg(help="Model ID", required=True),
    input_tokens: int = Arg(help="Input token count", required=True),
    output_tokens: int = Arg(help="Output token count", required=True),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Calculate cost for model usage."""
    client = _get_client(api_key)
    result = client.llm_models.calculate_cost(
        model_id, input_tokens=input_tokens, output_tokens=output_tokens,
    )
    return result.model_dump()


@skill.command
def models_providers(
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """List LLM providers."""
    client = _get_client(api_key)
    result = client.llm_models.providers()
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# CLEANER (1 command)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def clean_html(
    file: str = Arg("--file", help="HTML file path", default=None),
    html: str = Arg("--html", help="Raw HTML string", default=None),
    output_format: str = Arg("--format", help="Output format (html/markdown/text)", default="html"),
    max_tokens: int = Arg("--max-tokens", help="Max output tokens", default=10000),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Clean HTML for LLM consumption."""
    client = _get_client(api_key)
    if file:
        result = client.api_cleaner.clean_file(file, output_format=output_format, max_tokens=max_tokens)
    elif html:
        result = client.api_cleaner.clean(html, output_format=output_format, max_tokens=max_tokens)
    else:
        return {"error": "Provide --file or --html"}
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# PARSE (1 command)
# ═══════════════════════════════════════════════════════════════════════════


@skill.command
def parse(
    message: str = Arg(help="User message", required=True),
    schema: str = Arg(help="JSON Schema string for response format", required=True),
    model: str = Arg("--model", help="Model ID", default="openai/gpt-4o"),
    system: str = Arg("--system", help="System prompt", default=None),
    temperature: float = Arg("--temperature", help="Temperature", default=None),
    api_key: str = Arg("--api-key", help="API key override", default=None),
) -> dict:
    """Chat completion with structured output (JSON Schema)."""
    from pydantic import create_model
    from pydantic.fields import FieldInfo

    client = _get_client(api_key)

    # Build a dynamic Pydantic model from the JSON schema
    schema_dict = json.loads(schema)
    fields = {}
    for field_name, field_def in schema_dict.get("properties", {}).items():
        field_type = str  # default
        type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
        field_type = type_map.get(field_def.get("type", "string"), str)
        required = field_name in schema_dict.get("required", [])
        if required:
            fields[field_name] = (field_type, FieldInfo(default=...))
        else:
            fields[field_name] = (Optional[field_type], FieldInfo(default=None))

    DynamicModel = create_model("DynamicModel", **fields)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    kwargs = {"model": model, "messages": messages, "response_format": DynamicModel}
    if temperature is not None:
        kwargs["temperature"] = temperature

    result = client.parse(**kwargs)
    parsed = result.choices[0].message.parsed
    return {"parsed": parsed.model_dump() if parsed else None, "model": result.model}


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    skill.run()


if __name__ == "__main__":
    main()
