.PHONY: help claude commit install-sdk

SDK_ROOT := $(shell cd ../.. && pwd)/cmdop_sdk
SDK_SKILL := $(SDK_ROOT)/python/cmdop_skill
SDK_CMDOP := $(SDK_ROOT)/python/cmdop

help:
	@echo "Available commands:"
	@echo "  make install-sdk  - Install local SDK into all skills in libs/"
	@echo "  make claude       - Start Claude Code"
	@echo "  make commit       - Stage and commit with AI message"

# Install local cmdop-skill + cmdop into all skills via [tool.uv.sources]
install-sdk:
	@test -d $(SDK_SKILL) || (echo "ERROR: cmdop_sdk not found at $(SDK_ROOT)" && exit 1)
	@for dir in libs/*/; do \
		[ -f "$$dir/pyproject.toml" ] || continue; \
		echo "==> $$dir"; \
		cd "$$dir" && \
		grep -q '^\[tool\.uv\.sources\]' pyproject.toml && \
			sed -i '' '/^\[tool\.uv\.sources\]/,/^$$/d' pyproject.toml || true; \
		echo '' >> pyproject.toml; \
		echo '[tool.uv.sources]' >> pyproject.toml; \
		echo 'cmdop-skill = { path = "$(SDK_SKILL)", editable = true }' >> pyproject.toml; \
		if [ -d "$(SDK_CMDOP)" ]; then \
			echo 'cmdop = { path = "$(SDK_CMDOP)", editable = true }' >> pyproject.toml; \
		fi; \
		echo '' >> pyproject.toml; \
		uv sync --all-extras; \
		cd - > /dev/null; \
		echo ""; \
	done
	@echo "Done. All skills linked to local SDK."

# Start Claude Code with dangerously-skip-permissions flag
claude:
	claude --dangerously-skip-permissions --chrome

# Stage all changes and commit with AI-generated message using orc
commit:
	git add . && orc commit
