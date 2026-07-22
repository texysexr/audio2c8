# 🎙️ HackRF & PortaPack Audio-to-C8 Converter

A fast, feature-rich command-line tool that converts standard audio files (MP3, WAV, FLAC, and M4A) into **HackRF/PortaPack `.c8` IQ files** for playback using **HackRF One** and **PortaPack (Mayhem Firmware)**.

Built with **NumPy**, **SciPy**, and **Rich** for maximum performance and an easy-to-use interface.

---

## ✨ Features

- 🎵 Convert **MP3, WAV, FLAC, and M4A** directly to `.c8`
- ⚡ Highly optimized DSP pipeline using **NumPy**
- 📈 FM **Pre-emphasis** filtering for improved audio quality
- 📊 Beautiful terminal interface powered by **Rich**
- 📁 Automatically creates PortaPack `.txt` metadata files
- 💾 Estimates output file size before conversion
- 🎚️ Built-in processing presets:
  - PortaPack FM Broadcast (500 kHz)
  - High Fidelity (1 MHz)
  - Low Storage (250 kHz)
  - Fully Custom
- 🔄 Automatic audio conversion using **FFmpeg**
- 📻 Displays the required `hackrf_transfer` command after conversion
- 🖥️ Works on **Windows, Linux, and macOS**

---

## 📋 Prerequisites

- Python **3.8+**
- FFmpeg installed and available in your system `PATH`

### Install FFmpeg

#### Windows

Download FFmpeg from:

https://www.gyan.dev/ffmpeg/builds/

Extract it and add the **bin** folder to your system PATH.

#### Ubuntu / Debian

```bash
sudo apt install ffmpeg
```

#### macOS

```bash
brew install ffmpeg
```

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/texysexr/audio2c8.git
cd audio2c8
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

1. Place your audio files in the same folder as the script.
2. Run the converter:

```bash
python audio2c8.py
```

3. Select the audio file from the list.

4. Choose one of the processing presets:

| Option | Preset | Sample Rate | Description |
|--------|---------|-------------|-------------|
| **1** | PortaPack FM Broadcast | 500 kHz | Recommended for most users |
| **2** | High Fidelity | 1 MHz | Highest quality output |
| **3** | Low Storage | 250 kHz | Smallest file size |
| **4** | Custom | User Defined | Choose your own settings |

5. Enter:

- Center Frequency (MHz)
- Output filename

The converter will then:

- Convert the audio to WAV (if necessary)
- Normalize audio
- Apply FM pre-emphasis
- Resample audio
- Generate FM IQ data
- Save a `.c8` file
- Create the required `.txt` PortaPack metadata file

---

## 📂 Output

Example:

```
music.c8
music.txt
```

The metadata file contains:

```text
center_frequency=107900000
sample_rate=500000
```

---

## 📻 Playing on PortaPack

Copy both files to your PortaPack SD card:

```
/REPLAY
```

or

```
/LOOKOUT
```

Then select the `.c8` file from the Replay application.

---

## 💻 Using with HackRF

After conversion, the program displays a ready-to-use command such as:

```bash
hackrf_transfer -t output.c8 -f 107900000 -s 500000 -a 1 -x 47
```

---

## 📦 Supported Formats

Input:

- WAV
- MP3
- FLAC
- M4A

Output:

- `.c8`
- `.txt` (PortaPack metadata)

---

## 🛠 Built With

- Python
- NumPy
- SciPy
- Rich
- FFmpeg

---

## 📄 License

This project is licensed under the MIT License.

---

## ⭐ Contributing

Pull requests and feature suggestions are welcome.

If you find a bug or have an idea for an improvement, feel free to open an issue.

---

## ❤️ Acknowledgements

- Great Scott Gadgets
- HackRF One Community
- PortaPack Mayhem Firmware
- NumPy
- SciPy
- Rich