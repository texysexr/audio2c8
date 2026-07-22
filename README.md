# HackRF & PortaPack Audio-to-C8 Converter

A highly optimized, feature-rich CLI tool to convert standard audio files (MP3, WAV, FLAC, M4A) directly into `.c8` (IQ format) for transmission via HackRF One or a PortaPack (Mayhem Firmware).

## Features
- **Beautiful CLI UI:** Uses `rich` for formatted tables, styled prompts, and live progress bars.
- **Fast DSP Engine:** Fully vectorized NumPy and SciPy implementations for normalization, pre-emphasis, and IQ phase modulation.
- **Pre-emphasis Filtering:** Built-in FM pre-emphasis drastically improves transmission clarity over distance.
- **PortaPack Ready:** Automatically generates the required `.txt` metadata sidecar files for native PortaPack SD card playback.
- **Presets:** Quick selection profiles for high-fidelity, balanced, or low-storage configurations.

## Prerequisites

1. **Python 3.8+**
2. **FFmpeg**: Must be installed and accessible in your system PATH to read MP3/FLAC/M4A files.
   - **Debian/Ubuntu:** `sudo apt install ffmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Windows:** Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to PATH.

## Installation

Clone the repository and install the Python dependencies:

```bash
git clone [https://github.com/texysexr/audio2c8.git](https://github.com/texysexr/audio2c8.git)
cd audio2c8
pip install -r requirements.txt