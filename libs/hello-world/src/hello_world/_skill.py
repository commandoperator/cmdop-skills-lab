"""hello-world CMDOP skill — greets users by name."""

from __future__ import annotations

from cmdop_skill import Arg, Skill

skill = Skill(
    name="hello-world",
    description="Demo CMDOP skill — greets users by name",
    version="0.1.0",
)


@skill.command
def greet(
    name: str = Arg(help="Name to greet", required=True),
    shout: bool = Arg("--shout", action="store_true", default=False, help="UPPERCASE output"),
) -> dict:
    """Say hello to someone."""
    message = f"Hello, {name}!"
    if shout:
        message = message.upper()
    return {"message": message}


@skill.command
def goodbye(
    name: str = Arg(help="Name to say goodbye to", required=True),
) -> dict:
    """Say goodbye to someone."""
    return {"message": f"Goodbye, {name}!"}


def main() -> None:
    skill.run()


if __name__ == "__main__":
    main()
