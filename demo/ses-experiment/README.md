# SES Email Experiment

Test email sending via SDKRouter email gateway (SMTP accounts).

## Setup

1. Add SMTP account via `setup_account.py`
2. Test sending via `test_send.py`
3. Benchmark deliverability vs Mail.app

## Supported Providers

- **AWS SES** — $0.10/1000 emails, 50K/day
- **Gmail SMTP** — 500/day (app password)
- **Any SMTP** — custom provider
