from cmdop_skill import SkillCategory, SkillConfig

# version, description, requires, tags, repository_url
# автоматически подтягиваются из pyproject.toml

config = SkillConfig(
    name="tg-notify",
    category=SkillCategory.COMMUNICATION,
    visibility="public",
)
