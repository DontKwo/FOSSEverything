# Desktop Installation Guide

Install and launch `FOSSEverything` on your computer without Python or terminal setup.

## Safety & Authenticity Warning

- **Official `main` Releases Only**: Download `FOSSEverything` exclusively from [DontKwo/FOSSEverything Releases](https://github.com/DontKwo/FOSSEverything/releases/latest).
- **Fork Warning**: Do **not** download or run executables from forked repositories unless you have verified the source code yourself and confirmed they contain no malware. Only official `main` releases are maintained by the author, and I make no promises.
- **Bypassing Security Prompts**: Because independent open-source executables do not carry paid commercial signing certificates, Windows and macOS will warn that the app is unrecognized or potentially unsafe. Bypassing these prompts is strictly at your own discretion, and the software is provided "AS IS" with zero liability.

---

## Windows

1. Download `FOSSEverything-Windows.exe` from [Latest Releases](https://github.com/DontKwo/FOSSEverything/releases/latest).
2. Double-click `FOSSEverything-Windows.exe` to run the setup wizard (choose install folder, optional right-click menu entries, Start Menu shortcut, theme, and interface size).
3. If **Microsoft Defender SmartScreen** displays *"Windows protected your PC"*:
   - Click **More info**.
   - Confirm the file came from `DontKwo/FOSSEverything`, then click **Run anyway** at your own discretion.
4. Alternative unblock method: Right-click `FOSSEverything-Windows.exe` -> **Properties** -> check **Unblock** under Security -> click **Apply** and **OK** -> run installer normally.

---

## macOS

1. Download `FOSSEverything-macOS.dmg` from [Latest Releases](https://github.com/DontKwo/FOSSEverything/releases/latest).
2. Open the DMG and drag **FOSSEverything** into **Applications**.
3. On macOS Sonoma and Sequoia, approve an independently distributed app in **System Settings**:
   - Double-click `FOSSEverything` once so macOS shows the blocked notice, then click **OK** (or **Done**).
   - Open **System Settings** -> **Privacy & Security** -> scroll to the **Security** section.
   - Next to the blocked notice, click **Open Anyway** and authenticate at your own discretion.
4. Developer Terminal Alternative: run `xattr -cr /Applications/FOSSEverything.app` and open normally.

---

## Linux

1. Download `FOSSEverything-Linux.tar.gz` from [Latest Releases](https://github.com/DontKwo/FOSSEverything/releases/latest).
2. Extract the archive in your file manager (or run `tar -xzf FOSSEverything-Linux.tar.gz`).
3. Run `./install.sh` (or run `./FOSSEverything` directly from the extracted directory).

---

## Related Documentation

- [Project Overview](../README.md)
- [User Guide](USER_GUIDE.md)
- [Frequently Asked Questions](FAQ.md)
- [Privacy Statement](../PRIVACY.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
