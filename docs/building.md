# Packaging and deployment

## Python package

```bash
python -m build
python -m pip install dist/hust_helper-0.1.0-py3-none-any.whl
```

## Desktop

Flet desktop builds must be produced on, or configured for, the target platform.
The Windows command creates an application bundle containing an `.exe`; Linux and
macOS use their corresponding targets.

```bash
flet build windows src --product "HUST Helper"
flet build linux src --product "HUST Helper"
flet build macos src --product "HUST Helper"
```

## Android

Flet installs missing Android/Flutter tooling when supported, but a Java JDK and
Android SDK/accepted licenses may be required. For local install/testing:

```bash
flet build apk src --split-per-abi --product "HUST Helper"
```

For store distribution, prefer AAB and configure signing before release:

```bash
flet build aab src --product "HUST Helper"
```

## Secrets

Do not compile API keys into desktop or mobile applications. Accept them at runtime,
use environment variables for desktop/notebook use, or connect the app to a trusted
backend that owns the vendor key.
