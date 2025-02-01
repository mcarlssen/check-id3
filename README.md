# Check-ID3: Audio Metadata Tag Verifier

A command-line utility to verify ID3 metadata tags in audio files against expected values. Currently supports MP3, with WAV support coming soon.

###changelog
- 2025-02-01: first release. supports mp3 only. open bug reports and feature requests at https://github.com/mcarlssen/check-id3/issues

## Features
- Verify ID3 tags in audio files across directories
- Supports CSV and TSV input files for expected tags
- Supports regex expressions for expected tag values
- Detailed validation reports
- Flexible input options (command-line arguments or interactive prompts)

## Installation

### Automated Installation
For Windows:
1. Download `check-id3.ps1` and `tag_verifier.py`, and place them in the same folder.
2. Right-click the file and select "Run with PowerShell"
3. Follow the on-screen instructions

The app will check and install the required dependencies, and then run the interactive interface. You may be prompted for administrator elevation to install python, pip, and mutagen. This elevation is only required once and is not necessary to perform the metadata analysis.

Once the dependencies are installed, a file named `settings.ini` will be created to save this status. If you experience python errors related to your environment or missing modules, delete this file and re-run `check-id3.ps1`.

### Manual Installation

### Prerequisites
- Python 3.6 or higher
- Required Python packages: `mutagen`

### Installation Steps
1. **Check Python Installation**:
   First, verify if Python is installed:
   ```bash
   python3 --version
   ```
   If Python is not installed, download and install it from [python.org](https://www.python.org/downloads/).

2. Clone the repository or download the script:
   ```bash
   git clone https://github.com/mcarlssen/check-id3.git
   cd check-id3
   ```

3. Install required dependencies:
   ```bash
   pip install mutagen
   ```
   If `pip` is not found, install it first:
   ```bash
   python3 -m ensurepip --upgrade
   ```

## Troubleshooting
- **Python not found**: Ensure Python is installed and added to your system PATH
- **pip not found**: Install pip using `python3 -m ensurepip --upgrade`
- **ModuleNotFoundError**: Verify mutagen is installed using `pip show mutagen`

## Usage

To run the app with an interactive interface, right-click `check-id3.ps1` and select "Run with PowerShell".

To run the app with command-line arguments, use the following command:

```
python tag_verifier.py --help
```
