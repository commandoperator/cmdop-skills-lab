#!/usr/bin/env python3
"""Interactive CLI for sending emails via llm-email."""

import asyncio

import click

from llm_email.db import init_db, close_db
from llm_email.mailer import send_email, list_accounts


async def _send(to: str, subject: str, body: str, from_account: str, cc: str, bcc: str, draft: bool) -> dict:
    await init_db()
    try:
        return await send_email(
            to=to, subject=subject, body=body,
            from_account=from_account, cc=cc, bcc=bcc,
            draft_only=draft,
        )
    finally:
        await close_db()


async def _accounts() -> dict:
    await init_db()
    try:
        return await list_accounts()
    finally:
        await close_db()


@click.group()
def cli() -> None:
    """llm-email interactive CLI."""


@cli.command()
@click.option("--to", prompt="To (email)", help="Recipient email address.")
@click.option("--subject", prompt="Subject", help="Email subject line.")
@click.option("--body", prompt="Body", help="Email body text.")
@click.option("--from", "from_account", default="", help="Sender account (leave empty for default).")
@click.option("--cc", default="", help="CC recipients.")
@click.option("--bcc", default="", help="BCC recipients.")
@click.option("--draft", is_flag=True, help="Create draft instead of sending.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def send(to: str, subject: str, body: str, from_account: str, cc: str, bcc: str, draft: bool, yes: bool) -> None:
    """Send an email (interactive prompts for required fields)."""
    action = "draft" if draft else "send"
    click.echo(f"\n{'='*50}")
    click.echo(f"  Action:  {action}")
    click.echo(f"  To:      {to}")
    if cc:
        click.echo(f"  CC:      {cc}")
    if bcc:
        click.echo(f"  BCC:     {bcc}")
    if from_account:
        click.echo(f"  From:    {from_account}")
    click.echo(f"  Subject: {subject}")
    click.echo(f"  Body:    {body[:80]}{'...' if len(body) > 80 else ''}")
    click.echo(f"{'='*50}\n")

    if not yes and not click.confirm("Send this email?", default=True):
        click.echo("Cancelled.")
        return

    result = asyncio.run(_send(to, subject, body, from_account, cc, bcc, draft))

    if result["ok"]:
        click.secho(f"OK — {action} to {to}", fg="green")
    else:
        click.secho(f"FAILED — {result.get('error', 'unknown error')}", fg="red")


@cli.command()
def accounts() -> None:
    """List available Mail.app accounts."""
    result = asyncio.run(_accounts())
    if not result["ok"]:
        click.secho(f"Error: {result.get('error')}", fg="red")
        return
    for acc in result["accounts"]:
        default = " (default)" if acc.get("default") else ""
        name = acc.get("name", "")
        email = acc.get("email", "")
        click.echo(f"  {name} <{email}>{default}")


if __name__ == "__main__":
    cli()
