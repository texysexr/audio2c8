#!/usr/bin/env python3
import os
import sys
import wave
import shutil
import subprocess
import numpy as np

# --- Dependency Check & Graceful Fallback ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("[!] 'rich' library not found. Falling back to basic text output.")
    print("[!] For the full experience, run: pip install rich")

try:
    from scipy.signal import lfilter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def print_msg(msg, style="bold white"):
    if RICH_AVAILABLE:
        console.print(msg, style=style)
    else:
        print(msg)

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def find_audio_files():
    extensions = ('.mp3', '.wav', '.flac', '.m4a')
    return sorted([f for f in os.listdir('.') if f.lower().endswith(extensions)])

def convert_to_wav(input_file):
    if input_file.lower().endswith('.wav'):
        return input_file
    
    output_wav = os.path.splitext(input_file)[0] + "_temp.wav"
    print_msg(f"[cyan]Converting '{input_file}' to WAV via FFmpeg...[/cyan]")
    subprocess.run(['ffmpeg', '-y', '-i', input_file, output_wav], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_wav

def apply_pre_emphasis_vectorized(audio_signal, sample_rate, tau=75e-6):
    """Vectorized FM Pre-emphasis filter for speed."""
    alpha = np.exp(-1.0 / (sample_rate * tau))
    if SCIPY_AVAILABLE:
        # Fast IIR filter via scipy
        b = [1.0, -alpha]
        a = [1.0 - alpha]
        return lfilter(b, a, audio_signal)
    else:
        # Fast FIR approximation fallback using pure numpy
        output = audio_signal - alpha * np.roll(audio_signal, 1)
        output[0] = audio_signal[0]
        return output

def create_portapack_metadata(c8_file, freq_hz, sample_rate):
    txt_file = os.path.splitext(c8_file)[0] + ".txt"
    with open(txt_file, 'w') as f:
        f.write(f"center_frequency={freq_hz}\nsample_rate={sample_rate}\n")
    return txt_file

def process_audio(wav_file, c8_output_file, target_samp_rate, freq_mhz):
    with wave.open(wav_file, 'rb') as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        audio_rate = w.getframerate()
        n_frames = w.getnframes()
        duration = n_frames / audio_rate
        
        # Disk space validation (C8 uses 2 bytes per sample: 8-bit I, 8-bit Q)
        required_bytes = int(duration * target_samp_rate * 2)
        free_bytes = shutil.disk_usage(".").free
        if required_bytes > free_bytes:
            print_msg(f"[red]Error: Not enough disk space! Need {required_bytes / 1e6:.1f} MB, have {free_bytes / 1e6:.1f} MB.[/red]")
            sys.exit(1)
            
        chunk_size = 44100 * 2  
        deviation = 75000.0     
        dt = 1.0 / target_samp_rate
        phase_offset = 0.0

        if RICH_AVAILABLE:
            progress_ctx = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn()
            )
        else:
            class DummyProgress:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def add_task(self, *args, **kwargs): return 1
                def update(self, *args, **kwargs): pass
            progress_ctx = DummyProgress()

        print_msg(f"\n[cyan]Starting DSP pipeline: {target_samp_rate/1000:.0f} kHz IQ output...[/cyan]")
        
        with open(c8_output_file, 'wb') as f_out:
            with progress_ctx as progress:
                task = progress.add_task("[green]Processing...", total=n_frames)
                
                for start_frame in range(0, n_frames, chunk_size):
                    frames_to_read = min(chunk_size, n_frames - start_frame)
                    raw_data = w.readframes(frames_to_read)
                    
                    # 1. Vectorized Decoding
                    if sampwidth == 1:
                        audio = (np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
                    elif sampwidth == 2:
                        audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                    elif sampwidth == 4:
                        audio = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0
                    else:
                        audio = np.frombuffer(raw_data, dtype=np.float32)

                    # 2. Vectorized Downmix
                    if n_channels > 1:
                        audio = audio.reshape(-1, n_channels).mean(axis=1)

                    # 3. Vectorized Normalization
                    max_val = np.max(np.abs(audio))
                    if max_val > 0:
                        audio = (audio / max_val) * 0.95

                    # 4. Vectorized Pre-emphasis
                    audio = apply_pre_emphasis_vectorized(audio, audio_rate)

                    # 5. Vectorized Resampling
                    if target_samp_rate != audio_rate:
                        samples_count = int(len(audio) * target_samp_rate / audio_rate)
                        audio_resampled = np.interp(
                            np.linspace(0, len(audio) - 1, samples_count),
                            np.arange(len(audio)),
                            audio
                        )
                    else:
                        audio_resampled = audio

                    # 6. Vectorized FM Phase Modulation
                    phase = phase_offset + 2.0 * np.pi * deviation * np.cumsum(audio_resampled) * dt
                    if len(phase) > 0:
                        phase_offset = phase[-1] % (2.0 * np.pi)

                    # 7. Vectorized IQ Generation
                    i_int = np.clip(np.cos(phase) * 88.9, -128, 127).astype(np.int8)  # 88.9 = 0.7 * 127
                    q_int = np.clip(np.sin(phase) * 88.9, -128, 127).astype(np.int8)

                    # 8. Fast Interleaved Memory Write
                    c8_chunk = np.empty((2 * len(i_int),), dtype=np.int8)
                    c8_chunk[0::2] = i_int
                    c8_chunk[1::2] = q_int
                    f_out.write(c8_chunk.tobytes())
                    
                    if RICH_AVAILABLE:
                        progress.update(task, advance=frames_to_read)
                    else:
                        print(f"[~] Progress: {min(100, int((start_frame + frames_to_read) / n_frames * 100))}%", end='\r')

        return duration, required_bytes

def display_summary(output_name, txt_name, freq_mhz, target_samp_rate, duration, size_bytes):
    freq_hz = int(freq_mhz * 1000000)
    if RICH_AVAILABLE:
        summary_text = (
            f"[bold]Output File:[/bold] {output_name} ({size_bytes / 1e6:.1f} MB)\n"
            f"[bold]Metadata File:[/bold] {txt_name}\n"
            f"[bold]Duration:[/bold] {duration:.1f} seconds\n"
            f"[bold]Frequency:[/bold] {freq_mhz} MHz\n"
            f"[bold]Sample Rate:[/bold] {target_samp_rate / 1000:.0f} kHz\n\n"
            f"[yellow bold]HackRF Command:[/yellow bold]\n"
            f"hackrf_transfer -t {output_name} -f {freq_hz} -s {target_samp_rate} -a 1 -x 47\n\n"
            f"[green bold]PortaPack SD Card:[/green bold]\n"
            f"Copy '{output_name}' and '{txt_name}' to the /REPLAY or /LOOKOUT folder."
        )
        console.print(Panel(summary_text, title="[bold cyan]Conversion Complete[/bold cyan]", expand=False))
    else:
        print("\n=== CONVERSION COMPLETE ===")
        print(f"File: {output_name} ({size_bytes / 1e6:.1f} MB)")
        print(f"HackRF CMD: hackrf_transfer -t {output_name} -f {freq_hz} -s {target_samp_rate} -a 1 -x 47")
        print(f"PortaPack: Copy {output_name} and {txt_name} to /REPLAY")

def main():
    if not check_ffmpeg():
        print_msg("[red]Error: FFmpeg is not installed or not in PATH. Please install FFmpeg to continue.[/red]")
        sys.exit(1)

    print_msg("\n[bold cyan]🎙️ HackRF/PortaPack Audio-to-C8 CLI Tool[/bold cyan]\n")
    
    files = find_audio_files()
    if not files:
        print_msg("[red]No audio files (.wav, .mp3, .flac, .m4a) found in the current directory.[/red]")
        sys.exit(1)
        
    if RICH_AVAILABLE:
        table = Table(title="Available Audio Files")
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Filename", style="magenta")
        for idx, f in enumerate(files):
            table.add_row(str(idx + 1), f)
        console.print(table)
    else:
        print("Available Audio Files:")
        for idx, f in enumerate(files):
            print(f"  [{idx + 1}] {f}")

    # File Selection
    while True:
        try:
            choice = int(input("\nSelect file ID: ")) - 1
            if 0 <= choice < len(files):
                selected_file = files[choice]
                break
            print_msg("[red]Invalid selection.[/red]")
        except ValueError:
            print_msg("[red]Please enter a number.[/red]")

    # Presets
    print_msg("\n[bold]Select Processing Preset:[/bold]")
    print_msg("  [1] PortaPack FM Broadcast (500 kHz, Balanced)")
    print_msg("  [2] HackRF High Fidelity (1 MHz, Cleanest Signal)")
    print_msg("  [3] Low Storage Mode (250 kHz, Minimal Size)")
    print_msg("  [4] Custom Setup")
    
    preset = input("Enter choice [1-4] (default: 1): ").strip() or "1"
    
    if preset == "1":
        target_sample_rate, freq_mhz = 500000, 107.9
    elif preset == "2":
        target_sample_rate, freq_mhz = 1000000, 107.9
    elif preset == "3":
        target_sample_rate, freq_mhz = 250000, 107.9
    else:
        sr_input = input("Enter Sample Rate in Hz (default: 500000): ").strip()
        target_sample_rate = int(sr_input) if sr_input else 500000
        fr_input = input("Enter Center Frequency in MHz (default: 107.9): ").strip()
        freq_mhz = float(fr_input) if fr_input else 107.9

    output_name = input("Enter output filename (default: output.c8): ").strip() or "output.c8"
    if not output_name.endswith('.c8'):
        output_name += ".c8"
        
    wav_path = convert_to_wav(selected_file)
    
    try:
        duration, size_bytes = process_audio(wav_path, output_name, target_sample_rate, freq_mhz)
        txt_name = create_portapack_metadata(output_name, int(freq_mhz * 1000000), target_sample_rate)
        display_summary(output_name, txt_name, freq_mhz, target_sample_rate, duration, size_bytes)
    finally:
        if wav_path != selected_file and os.path.exists(wav_path):
            os.remove(wav_path)

if __name__ == "__main__":
    main()