#!/usr/bin/env python3
"""
Test email sending via SDKRouter email gateway.

Usage:
    # Send test email (uses default account)
    python test_send.py --to markolofsen@gmail.com

    # Send via specific account
    python test_send.py --to markolofsen@gmail.com --account ses-us-east-1

    # Send HTML email
    python test_send.py --to markolofsen@gmail.com --html
"""

import argparse
from sdkrouter import SDKRouter

API_KEY = "test-api-key"


def main():
    parser = argparse.ArgumentParser(description="Test email sending")
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--account", default="", help="Account alias (uses default if empty)")
    parser.add_argument("--html", action="store_true", help="Send HTML email")
    args = parser.parse_args()

    client = SDKRouter(api_key=API_KEY)

    subject = "Test email from SDKRouter"
    body = "This is a test email sent via SDKRouter email gateway.\n\nIf you see this, the SMTP setup is working correctly."

    html = None
    if args.html:
        html = """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #00d4ff;">Cmdop — Test Email</h2>
            <p>This is a test email sent via <strong>SDKRouter email gateway</strong>.</p>
            <p>If you see this, the SMTP setup is working correctly.</p>
            <hr style="border: 1px solid #333;">
            <p style="color: #666; font-size: 12px;">
                Sent via SDKRouter | <a href="https://cmdop.com">cmdop.com</a>
            </p>
        </div>
        """

    kwargs = {
        "to": args.to,
        "subject": subject,
        "body": body,
    }
    if html:
        kwargs["html"] = html
    if args.account:
        kwargs["account_alias"] = args.account

    print(f"Sending to: {args.to}")
    print(f"Account: {args.account or '(default)'}")

    result = client.email.send(**kwargs)

    print(f"Status: {result.status}")
    print(f"Message ID: {result.message_id}")


if __name__ == "__main__":
    main()
