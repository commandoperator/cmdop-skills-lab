#!/usr/bin/env python3
"""
Setup SMTP accounts in SDKRouter email gateway.

Usage:
    # Add Gmail account (use app password, not regular password)
    python setup_account.py add-gmail --email user@gmail.com --password "xxxx xxxx xxxx xxxx"

    # Add AWS SES account
    python setup_account.py add-ses --email noreply@cmdop.com --username AKIA... --password SECRET --region us-east-1

    # Add any SMTP
    python setup_account.py add-smtp --alias myserver --host smtp.example.com --email user@example.com --username user --password pass

    # List accounts
    python setup_account.py list

    # Test connection
    python setup_account.py test --id ACCOUNT_ID

    # Delete
    python setup_account.py delete --id ACCOUNT_ID
"""

import argparse
import json
import sys
from sdkrouter import SDKRouter

API_KEY = "test-api-key"


def get_client() -> SDKRouter:
    return SDKRouter(api_key=API_KEY)


def cmd_list(args):
    client = get_client()
    accounts = client.email.list_accounts()
    if not accounts:
        print("No email accounts configured.")
        return
    print(f"{'Alias':<20} {'Email':<35} {'Host':<25} {'Default'}")
    print("-" * 90)
    for a in accounts:
        print(f"{a.alias:<20} {a.from_email:<35} {a.smtp_host:<25} {'*' if a.is_default else ''}")


def cmd_add_gmail(args):
    client = get_client()
    account = client.email.create_account(
        alias=args.alias or args.email.split("@")[0],
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username=args.email,
        smtp_password=args.password,
        from_email=args.email,
        from_name=args.name or "",
        use_tls=True,
        is_default=args.default,
    )
    print(f"Gmail account added: {account.alias} ({account.from_email})")
    print(f"Account ID: {account.id}")


def cmd_add_ses(args):
    # SES SMTP endpoint: email-smtp.{region}.amazonaws.com
    host = f"email-smtp.{args.region}.amazonaws.com"
    client = get_client()
    account = client.email.create_account(
        alias=args.alias or f"ses-{args.region}",
        smtp_host=host,
        smtp_port=587,
        smtp_username=args.username,
        smtp_password=args.password,
        from_email=args.email,
        from_name=args.name or "",
        use_tls=True,
        is_default=args.default,
    )
    print(f"SES account added: {account.alias} ({account.from_email})")
    print(f"Host: {host}")
    print(f"Account ID: {account.id}")


def cmd_add_smtp(args):
    client = get_client()
    account = client.email.create_account(
        alias=args.alias,
        smtp_host=args.host,
        smtp_port=args.port,
        smtp_username=args.username,
        smtp_password=args.password,
        from_email=args.email,
        from_name=args.name or "",
        use_tls=args.tls,
        is_default=args.default,
    )
    print(f"SMTP account added: {account.alias} ({account.from_email})")
    print(f"Account ID: {account.id}")


def cmd_test(args):
    client = get_client()
    result = client.email.test_account(args.id)
    if result.success:
        print(f"Connection OK")
    else:
        print(f"Connection FAILED: {result}")


def cmd_delete(args):
    client = get_client()
    client.email.delete_account(args.id)
    print(f"Account {args.id} deleted")


def main():
    parser = argparse.ArgumentParser(description="Manage SDKRouter email accounts")
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="List all email accounts")

    # add-gmail
    p_gmail = sub.add_parser("add-gmail", help="Add Gmail SMTP account")
    p_gmail.add_argument("--email", required=True)
    p_gmail.add_argument("--password", required=True, help="Gmail app password")
    p_gmail.add_argument("--alias", default="")
    p_gmail.add_argument("--name", default="")
    p_gmail.add_argument("--default", action="store_true")

    # add-ses
    p_ses = sub.add_parser("add-ses", help="Add AWS SES SMTP account")
    p_ses.add_argument("--email", required=True, help="Verified sender email")
    p_ses.add_argument("--username", required=True, help="SES SMTP username (AKIA...)")
    p_ses.add_argument("--password", required=True, help="SES SMTP password")
    p_ses.add_argument("--region", default="us-east-1")
    p_ses.add_argument("--alias", default="")
    p_ses.add_argument("--name", default="")
    p_ses.add_argument("--default", action="store_true")

    # add-smtp
    p_smtp = sub.add_parser("add-smtp", help="Add custom SMTP account")
    p_smtp.add_argument("--alias", required=True)
    p_smtp.add_argument("--host", required=True)
    p_smtp.add_argument("--email", required=True)
    p_smtp.add_argument("--username", required=True)
    p_smtp.add_argument("--password", required=True)
    p_smtp.add_argument("--port", type=int, default=587)
    p_smtp.add_argument("--name", default="")
    p_smtp.add_argument("--tls", action="store_true", default=True)
    p_smtp.add_argument("--default", action="store_true")

    # test
    p_test = sub.add_parser("test", help="Test account connection")
    p_test.add_argument("--id", required=True)

    # delete
    p_del = sub.add_parser("delete", help="Delete account")
    p_del.add_argument("--id", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "list": cmd_list,
        "add-gmail": cmd_add_gmail,
        "add-ses": cmd_add_ses,
        "add-smtp": cmd_add_smtp,
        "test": cmd_test,
        "delete": cmd_delete,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
