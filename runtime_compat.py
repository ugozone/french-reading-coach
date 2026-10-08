"""Locate native eSpeak libraries without hard-coding a single developer's Mac.

Linux normally uses the system library loader (packages.txt installs espeak-ng).
Windows and macOS may need an explicit path to the shared library.
An explicitly configured PHONEMIZER_ESPEAK_LIBRARY takes precedence.
"""
import os
import platform
from pathlib import Path


def find_espeak_library(system=None, environ=None, is_file=None):
    """Return a usable native library path, or None to use phonemizer defaults."""
    system = system or platform.system()
    env = environ if environ is not None else os.environ
    exists = is_file if is_file is not None else os.path.isfile

    explicit = env.get("PHONEMIZER_ESPEAK_LIBRARY", "").strip()
    if explicit:
        # Honor the user-supplied path, even when a different machine owns it.
        return explicit

    candidates = []
    if system == "Darwin":
        for prefix in ("/opt/homebrew", "/usr/local"):
            for libname in ("libespeak-ng.dylib", "libespeak.dylib"):
                candidates.append(str(Path(prefix) / "lib" / libname))
                candidates.append(str(Path(prefix) / "opt" / "espeak-ng" / "lib" / libname))
    elif system == "Windows":
        install_roots = [
            env.get("ProgramFiles", ""),
            env.get("ProgramFiles(x86)", ""),
            env.get("LOCALAPPDATA", ""),
        ]
        for root in filter(None, install_roots):
            for suffix in (
                ("eSpeak NG", "libespeak-ng.dll"),
                ("eSpeak NG", "libespeak.dll"),
                ("Programs", "eSpeak NG", "libespeak-ng.dll"),
                ("Programs", "eSpeak NG", "libespeak.dll"),
            ):
                candidates.append(str(Path(root).joinpath(*suffix)))
        # Some package managers install the DLL in a directory on PATH.
        for folder in env.get("PATH", "").split(";"):
            if folder:
                for name in ("libespeak-ng.dll", "libespeak.dll"):
                    candidates.append(str(Path(folder) / name))

    return next((path for path in candidates if exists(path)), None)


def configure_espeak_library(wrapper, **kwargs):
    """Configure phonemizer when a known native library is available."""
    library = find_espeak_library(**kwargs)
    if library:
        wrapper.set_library(library)
    return library
