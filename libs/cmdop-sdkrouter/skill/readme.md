# cmdop-sdkrouter

CMDOP skill wrapper for **SDKRouter** — a unified Python SDK for AI services.

## Services

| Service      | Commands | Description                                    |
|--------------|----------|------------------------------------------------|
| Chat         | 2        | LLM chat completions & streaming               |
| Vision       | 3        | Image analysis, OCR, vision model listing       |
| Audio        | 3        | Speech-to-text, text-to-speech, TTS streaming   |
| Image Gen    | 6        | AI image generation (sync/async), listing       |
| Search       | 4        | Web search, URL fetch, async deep search        |
| CDN          | 5        | File upload/download/list/delete, usage stats   |
| Translator   | 4        | Text & JSON translation, language detection     |
| Payments     | 8        | Crypto balance, deposits, payments, withdrawals |
| Proxies      | 7        | Proxy CRUD, health checks, testing              |
| Shortlinks   | 4        | URL shortening, listing, stats                  |
| Keys         | 5        | API key management (create/rotate/delete)       |
| Models       | 4        | LLM model listing, cost calculation, providers  |
| Cleaner      | 1        | HTML cleaning for LLM consumption               |
| Parse        | 1        | Structured output (Pydantic) chat completion    |

## Usage

```bash
# Chat
cmdop-sdkrouter chat --model openai/gpt-4o --message "Hello!"
cmdop-sdkrouter chat-stream --model openai/gpt-4o --message "Tell me a story"

# Vision
cmdop-sdkrouter vision-analyze --image-url https://example.com/photo.jpg
cmdop-sdkrouter vision-ocr --image-url https://example.com/document.jpg

# Search
cmdop-sdkrouter search --query "latest AI news"

# CDN
cmdop-sdkrouter cdn-upload --file ./image.png
cmdop-sdkrouter cdn-list

# Translation
cmdop-sdkrouter translate --text "Hello world" --target ru
```

## Environment

Set `SDKROUTER_API_KEY` environment variable or pass `--api-key` to any command.
