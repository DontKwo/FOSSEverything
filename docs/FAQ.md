# Frequently Asked Questions

Answers to common questions about installing, licensing, privacy, and operating FOSSEverything.

## Offline Operation & Search

**How does FOSSEverything search tools offline?**

Tool discovery in `app/core/tool_registry.py` and `app/core/tooltips.py` runs completely locally using intent keywords, normalized strings, and similarity scoring without cloud APIs.

**Does FOSSEverything send my files anywhere?**

No. All PDF, image, media, archive, and data tools run directly on your machine. See [Privacy Statement](../PRIVACY.md).

## Licensing

**What license applies to FOSSEverything?**

FOSSEverything is licensed under the [MIT License](../LICENSE) (`Copyright (c) 2026 DontKwo`). External dependencies, optional command-line binaries, pretrained neural model weights, icons, and fonts retain their own upstream licenses listed in [Third-Party Notices](../THIRD_PARTY_NOTICES.md).

## Installation Warnings

**Why do Windows SmartScreen or macOS Gatekeeper show security warnings?**

Prebuilt releases do not include commercial paid code-signing certificates. Download only from [Official Releases](https://github.com/DontKwo/FOSSEverything/releases/latest) and follow the [Desktop Installation Guide](INSTALLATION.md) at your own discretion.

## Related Documentation

- [Project Overview](../README.md)
- [User Guide](USER_GUIDE.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [Privacy Statement](../PRIVACY.md)
- [Third-Party Notices](../THIRD_PARTY_NOTICES.md)
- [Security Policy](../SECURITY.md)
