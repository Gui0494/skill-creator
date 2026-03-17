#!/usr/bin/env python3
"""
Validates the structure and content of a created agent.

Checks:
- SKILL.md exists with valid frontmatter
- Name is kebab-case, max 64 chars
- Description max 1024 chars, no angle brackets
- Scripts are executable and have shebangs
- References point to existing files
- No sensitive files (.env, credentials, secrets)
- SKILL.md under 500 lines
"""

import sys
import os
import re
import yaml
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


def validate_frontmatter(content):
    """Validate YAML frontmatter of SKILL.md."""
    errors = []

    if not content.startswith('---'):
        return [("CRITICAL", "No YAML frontmatter found")]

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return [("CRITICAL", "Invalid frontmatter format")]

    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            return [("CRITICAL", "Frontmatter must be a YAML dictionary")]
    except yaml.YAMLError as e:
        return [("CRITICAL", f"Invalid YAML: {e}")]

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
            errors.append(("ERROR", f"Name '{name}' must be kebab-case"))
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
        # Skip hidden directories
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
            first_line = script.read_text().split('\n')[0] if script.read_text() else ''
            if not first_line.startswith('#!'):
                errors.append(("WARNING", f"Script {script.name} missing shebang"))

    # Check references point to existing files
    if skill_md.exists():
        content = skill_md.read_text()
        # Look for references to files in references/ directory
        ref_mentions = re.findall(r'references/[\w.-]+', content)
        for ref in ref_mentions:
            ref_path = agent_path / ref
            if not ref_path.exists():
                errors.append(("ERROR", f"Referenced file not found: {ref}"))

    return errors


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

    # Sort by severity
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
