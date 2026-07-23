# Security Policy

## Supported Versions

We currently support the latest release with security updates.

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

1. **Do NOT** open a public issue — this could put users at risk
2. Email the maintainers directly or open a [security advisory](https://github.com/jadhav-prathamesh/New-Projects/security/advisories/new)
3. Include a detailed description, steps to reproduce, and potential impact

We will:
- Acknowledge receipt within 48 hours
- Investigate and provide a timeline for a fix
- Credit you in the release notes (if desired)

## Security Measures

This project processes log files that may contain sensitive data. Key security considerations:

- **No network calls**: The analyzer operates entirely offline — no data is sent anywhere
- **No persistence**: Reports are generated in-memory and not stored unless explicitly exported
- **No external dependencies**: Zero packages from PyPI means a minimal attack surface
- **Input sanitization**: File uploads are validated and parsed safely

## Best Practices for Users

- Sanitize sensitive data from log files before sharing them
- Review exported reports before posting to public channels
- Keep your Python environment updated

