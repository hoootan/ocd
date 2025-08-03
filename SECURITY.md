# Security Policy

## Supported Versions

We actively support the latest version of OCD with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Features

### 🔒 Privacy-First Design
- **Local Processing**: Complete file analysis using offline AI models
- **No Data Transmission**: Local-only mode keeps all data on your machine
- **Credential Security**: OS-native credential storage (Keychain, Windows Credential Manager)
- **No Telemetry**: No usage data collection or transmission

### 🛡️ Safe File Operations
- **Dry-Run Mode**: Preview all changes before execution
- **Operation Validation**: Comprehensive safety checks before file operations
- **Rollback Capability**: Undo operations if needed
- **Permission Validation**: Check file system permissions before operations
- **Path Validation**: Block operations on system directories

### 🔍 Input Validation
- **Path Sanitization**: All file paths are validated and sanitized
- **Command Injection Prevention**: No shell command execution from user input
- **File Type Validation**: Verify file types before processing
- **Size Limits**: Reasonable limits on file sizes for processing

### 🏠 Sandboxed Execution
- **Isolated Environment**: File operations run in controlled environment
- **Resource Limits**: Memory and disk usage monitoring
- **Time Limits**: Execution timeouts to prevent runaway processes
- **Safe Defaults**: Conservative safety settings by default

## Reporting a Vulnerability

If you discover a security vulnerability in OCD, please report it responsibly:

### 📧 Contact
- **Email**: me@hootan.dev
- **Subject**: [SECURITY] OCD Vulnerability Report
- **Response Time**: We aim to respond within 48 hours

### 📋 Report Format
Please include:
- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and severity assessment
- **Steps to Reproduce**: Detailed reproduction steps
- **Suggested Fix**: If you have suggestions for remediation
- **Disclosure Timeline**: Your preferred disclosure timeline

### 🤝 Responsible Disclosure Process

1. **Initial Report**: Submit vulnerability report via email
2. **Acknowledgment**: We acknowledge receipt within 48 hours
3. **Investigation**: We investigate and assess the vulnerability
4. **Fix Development**: We develop and test a fix
5. **Fix Release**: We release a patched version
6. **Public Disclosure**: We coordinate public disclosure

### 🏆 Recognition
- Security researchers will be credited in release notes
- Appropriate recognition in SECURITY.md
- GitHub security advisory if applicable

## Security Best Practices for Users

### 🔐 Installation Security
```bash
# Always verify installation source
git clone https://github.com/hoootan/ocd.git
cd ocd

# Use virtual environment
python install.py  # Creates isolated environment

# Verify installation
ocd --version
```

### 🛡️ Safe Usage
```bash
# Always use dry-run first
ocd organize ~/folder --dry-run

# Use local-only mode for sensitive files
ocd organize ~/private --mode local-only

# Review operations before executing
ocd organize ~/folder --strategy smart --dry-run
# Review output, then:
ocd organize ~/folder --strategy smart --execute
```

### 🔒 Sensitive Data Handling
- **Private Files**: Use `--mode local-only` for sensitive documents
- **API Keys**: Store in environment variables, not in files
- **Backups**: Create backups before major organization operations
- **Permissions**: Run with minimal required permissions

### ⚠️ Security Warnings
OCD will warn you about:
- **System Directories**: Operations on system folders
- **Permission Issues**: Insufficient file permissions
- **Large Operations**: Operations affecting many files
- **Destructive Actions**: Operations that might cause data loss

Example security warning:
```
⚠️  Security Alert: Attempting to organize system directory
❌  Operation blocked for safety
💡  Use --force flag only if you're absolutely certain
```

## Threat Model

### ✅ Protected Against
- **Data Exfiltration**: Local processing prevents data leakage
- **Command Injection**: No shell command execution from user input
- **Path Traversal**: Strict path validation and sanitization
- **Resource Exhaustion**: Memory and CPU limits
- **Unauthorized Access**: OS-native credential protection

### ⚠️ Assumptions
- **System Security**: Assumes underlying OS is not compromised
- **User Intent**: Assumes user has legitimate access to files being organized
- **File System**: Assumes file system permissions are properly configured
- **Dependencies**: Assumes Python and system dependencies are secure

### 🎯 Out of Scope
- **System-Level Attacks**: OS vulnerabilities, kernel exploits
- **Network Attacks**: Since local processing doesn't require network
- **Physical Access**: Physical machine compromise
- **Social Engineering**: User credential compromise

## Security Configuration

### 🔧 Safety Levels
```bash
# Maximum security (default for sensitive operations)
ocd organize ~/documents --safety maximum

# Balanced security (default)
ocd organize ~/downloads --safety balanced

# Minimal security (for trusted environments)
ocd organize ~/temp --safety minimal
```

### 🔒 Local-Only Mode
```bash
# Complete privacy - no internet access
ocd organize ~/private --mode local-only

# Specify local provider explicitly
ocd organize ~/sensitive --provider local_slm
```

### 📊 Audit Logging
All operations are logged with:
- Timestamp and user
- Files accessed and modified
- Operations performed
- Success/failure status
- Security warnings triggered

Log location: `~/.ocd/logs/ocd.log`

## Vulnerability History

No vulnerabilities have been reported or discovered at this time.

## Security Contact

For security-related questions or concerns:
- **Issues**: Use GitHub Issues for non-sensitive security questions
- **Vulnerabilities**: Use responsible disclosure process above
- **General Security**: Include [SECURITY] tag in issue titles

## Compliance

OCD follows security best practices:
- **OWASP**: Follows OWASP secure coding practices
- **Privacy**: Designed with privacy-by-design principles
- **Data Minimization**: Processes only necessary data
- **Transparency**: Open source for security review

## Regular Security Updates

- Dependencies are regularly updated
- Security patches are prioritized
- Security advisories are published for significant issues
- Users are notified of security updates through release notes

---

**Last Updated**: August 3, 2025  
**Version**: 0.1.0