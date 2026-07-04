# Safe Delete Policy

Atlas does not permanently delete project files during AI-assisted work.

Any AI assistant or automation working in this repository must move files,
folders, generated experiments, obsolete docs, or replaced implementations into
the repo-local `trash/` folder before removing them from their original
location.

## Rule

Do not hard-delete files or folders.

Use:

```text
trash/<timestamp>_<short_reason>/<original_relative_path>
```

Example:

```text
trash/20260508_ui_cleanup/apps/desktop/old_panel.js
trash/20260508_docs_archive/docs/OLD_PLAN.md
```

## Applies To

- Source files.
- Documentation.
- Configs.
- Prototype folders.
- Generated AI code that may still contain useful ideas.
- Whole folders being replaced or reorganized.

## Exceptions

The only files that can be deleted directly are disposable local artifacts that
can be regenerated and should not be preserved:

- `node_modules/`
- `ui_web/dist/`
- Python caches such as `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `*.tsbuildinfo`
- temporary logs and build outputs already ignored by `.gitignore`

## Required Workflow

1. Create a timestamped folder inside `trash/`.
2. Move the target file or folder there, preserving enough path context to know
   where it came from.
3. Only then create the replacement or remove references from the active app.
4. Mention the trash location in the final response.

## Reason

Atlas is evolving quickly. Old files often contain partial designs, prompts,
UI ideas, or implementation attempts that may be useful later. Moving files to
`trash/` keeps experimentation safe while allowing the active repo to stay
clean.
