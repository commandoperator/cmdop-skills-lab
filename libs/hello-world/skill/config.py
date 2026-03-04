from cmdop_skill import SkillCategory, SkillConfig

# version, description, requires, tags, repository_url
# all automatically pulled from pyproject.toml

config = SkillConfig(
    name="hello-world",
    category=SkillCategory.OTHER,
    visibility="public",
)
