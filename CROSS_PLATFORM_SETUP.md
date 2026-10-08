# French Reading Coach: cross-platform setup

French Reading Coach is a **browser-based Streamlit application**. Students and teachers can use the same hosted URL on Windows, macOS, Linux, Android, iPadOS, or iOS using a modern browser. They do **not** install Whisper, PyTorch, eSpeak NG, Python, or Praat on their devices. Only the hosting **server** needs those dependencies.

For contributors who wish to run the **server locally**, the supported, automated test environments are:

| Local development platform | Python | Notes |
|---|---|---|
| Linux x86-64 (Ubuntu) | 3.12 | CPU-only PyTorch wheel; native tools via apt |
| macOS Apple Silicon (arm64) | 3.12 | PyTorch macOS arm64; native tools via Homebrew |
| Windows x86-64 | 3.12 | PyTorch Windows; native tools via Chocolatey or official installers |

Other Linux distributions and architectures may also work but have not been verified by this test matrix. Older Intel Macs are **not** in the tested matrix, and the pinned PyTorch wheel may need a different compatible version. The same public Streamlit URL works regardless of the visitor's computer architecture.

## 1. Install native audio dependencies on the machine running Streamlit

**macOS (with Homebrew)**

```bash
brew install ffmpeg espeak-ng
```

**Ubuntu/Debian Linux**

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg espeak-ng
```

**Windows PowerShell (with Chocolatey, administrator)**

```powershell
choco install ffmpeg espeak-ng -y
```

Alternatively install the Windows x64 eSpeak NG MSI from [official releases](https://github.com/espeak-ng/espeak-ng/releases) and FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html).

For Windows, if IPA reports that eSpeak is unavailable, set an **environment variable** such as:

```powershell
$env:PHONEMIZER_ESPEAK_LIBRARY = "C:\Program Files\eSpeak NG\libespeak-ng.dll"
```

Change the path if your eSpeak NG installation uses a different directory. The library must actually exist on that machine. For a **persistent** Windows user environment variable, use Windows Environment Variables settings.

On Mac, `runtime_compat.py` checks the conventional Homebrew locations for Apple Silicon and Intel. On Linux, the operating system generally finds the shared library automatically. You can override detection with `PHONEMIZER_ESPEAK_LIBRARY` on any platform.

## 2. Set up Python in a virtual environment

Install Python **3.12**. Then clone the project and make a local virtual environment.

**macOS or Linux**

```bash
git clone https://github.com/ugozone/french-reading-coach.git
cd french-reading-coach
git checkout stability-fix
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**Windows PowerShell**

```powershell
git clone https://github.com/ugozone/french-reading-coach.git
cd french-reading-coach
git checkout stability-fix
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The pinned `requirements.txt` selects a Linux-specific CPU-only torch wheel on Linux x86-64 and the regular platform wheel elsewhere. Do not copy Linux `apt` commands onto a Mac or Windows PC.

## 3. Configure secrets without committing them

For local development create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`. Insert **your own** Supabase credentials; never upload real credentials, passwords or secret keys to GitHub. On Streamlit Community Cloud, configure secrets in the app's dashboard. Use a separate Supabase test project where possible.

## 4. Verify the environment

```bash
python -m pip check
python -m unittest discover -s tests -v
python -c "from speech import get_ipa; print(get_ipa('bonjour'))"
ffmpeg -version
espeak-ng --version
```

For the IPA test, a French IPA string is expected rather than `IPA unavailable`. In hosted usage, speech recognition, voice generation and database access still require internet connectivity; a local offline run is not equivalent to a fully offline app.

The GitHub Actions [stability workflow](.github/workflows/stability-smoke.yml) runs on Linux, Apple Silicon macOS and Windows and checks dependency installation, Python syntax, native IPA and unit tests.

## 5. Deploy safely

Community Cloud hosts the server on **Linux**. The visitors' operating systems are irrelevant to deployment. To test this branch, create a **separate** Streamlit app that points to `stability-fix`, uses Python **3.12** and has appropriate secrets. Do not change the existing production `main` deployment until platform tests and classroom acceptance tests have passed.

**Note:** cross-platform support does not prevent server resource crashes or Streamlit Community Cloud from hibernating an inactive app. Those are hosting/operations concerns.
