"""CMDOP skill definition for ssl-cert-checker."""

import sys

from cmdop_skill import Arg, Skill

from ssl_cert_checker._checker import check_certs
from ssl_cert_checker._models import status_emoji

skill = Skill()


@skill.command
def check(
    domains: str = Arg(help="Domains to check", required=True, nargs="+"),
    json: bool = Arg("--json", help="JSON output", action="store_true", default=False),
) -> dict:
    """Check SSL certificate expiry for domains."""
    domain_list = domains if isinstance(domains, list) else [domains]
    results = check_certs(domain_list)

    if not json:
        for r in results:
            if r.error:
                print(f"\u274c  {r.domain}: {r.error}")
            else:
                e = status_emoji(r.days_left)
                print(f"{e}  {r.domain}: expires {r.expires} ({r.days_left} days) \u2014 {r.issuer}")
        sys.exit(0)

    return {
        "results": [
            {
                **r.model_dump(),
                "status": status_emoji(r.days_left) if r.error is None else "\u274c",
            }
            for r in results
        ],
    }


def main() -> None:
    """CLI entry point."""
    skill.run()
