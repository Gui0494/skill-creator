#!/usr/bin/env python3
"""
Validates the structure and content of a created agent.

Checks:
- SKILL.md exists with valid frontmatter
- Name is kebab-case, max 64 chars
- Description max 1024 chars, no angle brackets
- Scripts have shebangs
- References point to existing files
- No sensitive files (.env, credentials, secrets)
- SKILL.md under 500 lines

No external dependencies required (no PyYAML).
"""

import sys
import os
import re
from pathlib import Path


SENSITIVE_PATTERNS = [
    '.env', '.env.local', '.env.production',
    'credentials', 'secret', 'token', 'api_key',
    'private_key', 'password', '.pem', '.key'
]

ALLOWED_FRONTMATTER_KEYS = {
    'name', 'description', 'license',
    'allowed-tools', 'metadata', 'compatibility'
}


def parse_frontmatter(content):
    """Parse YAML frontmatter without PyYAML dependency.

    Handles simple key: value pairs and multiline values using
    YAML block scalar indicators (|, >, |-, >-) or continuation
    via indentation. Sufficient for SKILL.md frontmatter validation.
    """
    if not content.startswith('---'):
        return None

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    fm = {}
    current_key = None
    current_value_lines = []
    is_multiline = False

    for line in match.group(1).split('\n'):
        # Check if this is a new key: value pair (not indented)
        key_match = re.match(r'^([a-zA-Z][a-zA-Z0-9_-]*)\s*:\s*(.*)', line)

        if key_match and not line.startswith((' ', '\t')):
            # Save previous key if exists
            if current_key is not None:
                if is_multiline:
                    fm[current_key] = ' '.join(current_value_lines).strip()
                else:
                    fm[current_key] = current_value_lines[0] if current_value_lines else ''

            current_key = key_match.group(1)
            value = key_match.group(2).strip()

            # Check for multiline indicators
            if value in ('|', '>', '|-', '>-'):
                is_multiline = True
                current_value_lines = []
            else:
                is_multiline = False
                current_value_lines = [value]

        elif current_key and line.startswith((' ', '\t')):
            # Continuation line for multiline value
            current_value_lines.append(line.strip())
            if not is_multiline:
                is_multiline = True

    # Save last key
    if current_key is not None:
        if is_multiline:
            fm[current_key] = ' '.join(current_value_lines).strip()
        else:
            fm[current_key] = current_value_lines[0] if current_value_lines else ''

    return fm


def validate_frontmatter(content):
    """Validate YAML frontmatter of SKILL.md."""
    errors = []

    fm = parse_frontmatter(content)
    if fm is None:
        return [("CRITICAL", "No valid YAML frontmatter found (must start with --- and end with ---)")]

    # Check required fields
    if 'name' not in fm:
        errors.append(("CRITICAL", "Missing 'name' in frontmatter"))
    if 'description' not in fm:
        errors.append(("CRITICAL", "Missing 'description' in frontmatter"))

    # Validate name
    name = fm.get('name', '')
    if isinstance(name, str) and name.strip():
        name = name.strip()
        if not re.match(r'^[a-z0-9-]+$', name):
            errors.append(("ERROR", f"Name '{name}' must be kebab-case (lowercase, digits, hyphens)"))
        if name.startswith('-') or name.endswith('-') or '--' in name:
            errors.append(("ERROR", f"Name '{name}' has invalid hyphens"))
        if len(name) > 64:
            errors.append(("ERROR", f"Name too long ({len(name)} chars, max 64)"))

    # Validate description
    desc = fm.get('description', '')
    if isinstance(desc, str) and desc.strip():
        desc = desc.strip()
        if '<' in desc or '>' in desc:
            errors.append(("ERROR", "Description contains angle brackets"))
        if len(desc) > 1024:
            errors.append(("ERROR", f"Description too long ({len(desc)} chars, max 1024)"))

    # Check for unexpected keys
    unexpected = set(fm.keys()) - ALLOWED_FRONTMATTER_KEYS
    if unexpected:
        errors.append(("WARNING", f"Unexpected frontmatter keys: {', '.join(sorted(unexpected))}"))

    return errors


def validate_structure(agent_path):
    """Validate the directory structure of an agent."""
    errors = []
    agent_path = Path(agent_path)

    # SKILL.md must exist
    skill_md = agent_path / 'SKILL.md'
    if not skill_md.exists():
        return [("CRITICAL", "SKILL.md not found")]

    # Check SKILL.md line count
    content = skill_md.read_text()
    line_count = len(content.splitlines())
    if line_count > 500:
        errors.append(("WARNING", f"SKILL.md has {line_count} lines (recommended max 500)"))

    # Validate frontmatter
    errors.extend(validate_frontmatter(content))

    # Check for sensitive files
    for root, dirs, files in os.walk(agent_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            f_lower = f.lower()
            for pattern in SENSITIVE_PATTERNS:
                if pattern in f_lower:
                    rel_path = os.path.relpath(os.path.join(root, f), agent_path)
                    errors.append(("CRITICAL", f"Sensitive file detected: {rel_path}"))

    # Check scripts have shebangs
    scripts_dir = agent_path / 'scripts'
    if scripts_dir.exists():
        for script in scripts_dir.glob('*.py'):
            try:
                first_line = script.read_text().split('\n')[0]
            except (OSError, UnicodeDecodeError):
                errors.append(("WARNING", f"Cannot read script: {script.name}"))
                continue
            if not first_line.startswith('#!'):
                errors.append(("WARNING", f"Script {script.name} missing shebang"))

    # Check references point to existing files
    ref_mentions = re.findall(r'references/[\w.-]+', content)
    for ref in ref_mentions:
        ref_path = agent_path / ref
        if not ref_path.exists():
            errors.append(("ERROR", f"Referenced file not found: {ref}"))

    return errors


def validate_agent(agent_path):
    """Validate an agent and return (is_valid, message) tuple.

    Compatible with quick_validate.validate_skill() interface.
    """
    errors = validate_structure(agent_path)
    if not errors:
        return True, "Agent structure is valid!"

    has_critical = any(sev == "CRITICAL" for sev, _ in errors)
    has_error = any(sev == "ERROR" for sev, _ in errors)

    messages = [f"[{sev}] {msg}" for sev, msg in errors]
    detail = "\n".join(messages)

    if has_critical:
        return False, f"Critical issues found:\n{detail}"
    elif has_error:
        return False, f"Errors found:\n{detail}"
    else:
        return True, f"Valid with warnings:\n{detail}"


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_agent.py <agent_directory>")
        sys.exit(1)

    agent_path = Path(sys.argv[1])
    if not agent_path.exists():
        print(f"ERROR: Directory not found: {agent_path}")
        sys.exit(1)

    if not agent_path.is_dir():
        print(f"ERROR: Not a directory: {agent_path}")
        sys.exit(1)

    errors = validate_structure(agent_path)

    if not errors:
        print("VALID: Agent structure is correct!")
        sys.exit(0)

    severity_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2}
    errors.sort(key=lambda e: severity_order.get(e[0], 3))

    has_critical = False
    for severity, message in errors:
        print(f"[{severity}] {message}")
        if severity == "CRITICAL":
            has_critical = True

    if has_critical:
        print("\nFAILED: Critical issues found. Fix them before proceeding.")
        sys.exit(1)
    else:
        print("\nPASSED with warnings. Review warnings above.")
        sys.exit(0)


if __name__ == "__main__":
    main()
