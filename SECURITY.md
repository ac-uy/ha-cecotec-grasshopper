# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please **do not** open a public issue. Instead:

1. Email the details to the maintainer
2. Include a description of the vulnerability
3. Provide steps to reproduce (if possible)
4. Allow time for a fix before public disclosure

## Security Considerations

### Credentials

- **Never** commit credentials, API keys, or passwords
- Use environment variables or secure config flows
- The integration uses OAuth2 for secure authentication

### Data Privacy

- The integration communicates with `server.sk-robot.com`
- Your Cecotec credentials are stored locally in Home Assistant
- No data is sent to third parties beyond the official API

### Updates

Keep your Home Assistant and this integration updated to receive security patches.

## Supported Versions

| Version | Status |
|---------|--------|
| 0.1.x   | Current |

## Security Best Practices

1. **Use strong passwords** for your Cecotec account
2. **Enable 2FA** on your Cecotec account if available
3. **Keep HA updated** for security patches
4. **Review logs** for suspicious activity
5. **Report issues** responsibly

## Questions?

For security questions, please reach out privately rather than opening public issues.
