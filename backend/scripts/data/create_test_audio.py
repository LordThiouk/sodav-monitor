"""Script to create test audio files for real data testing."""

import argparse
import os
import sys

import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from scipy.io import wavfile

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def create_sine_wave(freq=440, duration=5, sample_rate=44100):
    """Create a sine wave audio signal."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    sine = 0.5 * np.sin(2 * np.pi * freq * t)
    return sine, sample_rate


def create_test_audio_file(output_path, filename, format="mp3", duration=5, sample_rate=44100):
    """Create a test audio file with a sine wave."""
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Generate a sine wave
    freq = 440  # A4 note
    sine_wave, sr = create_sine_wave(freq, duration, sample_rate)

    # Create the full output path
    output_file = os.path.join(output_path, filename)

    # Save the audio file in the specified format
    if format.lower() == "wav":
        wavfile.write(output_file, sr, sine_wave.astype(np.float32))
        print(f"Created WAV file: {output_file}")
    elif format.lower() == "mp3":
        # First save as WAV
        temp_wav = os.path.join(output_path, "temp.wav")
        wavfile.write(temp_wav, sr, sine_wave.astype(np.float32))

        # Convert to MP3 using pydub
        audio = AudioSegment.from_wav(temp_wav)
        audio.export(output_file, format="mp3")

        # Remove temporary WAV file
        os.remove(temp_wav)
        print(f"Created MP3 file: {output_file}")
    else:
        print(f"Unsupported format: {format}")


def create_multiple_test_files():
    """Create multiple test audio files with different characteristics."""
    # Define the output directory
    output_dir = os.path.join("backend", "tests", "data", "audio")
    os.makedirs(output_dir, exist_ok=True)

    # Create a few test files with different durations and frequencies
    create_test_audio_file(output_dir, "sample1.mp3", format="mp3", duration=5)
    create_test_audio_file(output_dir, "sample2.mp3", format="mp3", duration=10)
    create_test_audio_file(output_dir, "sample3.wav", format="wav", duration=3)

    # Create a test file with a different frequency
    freq = 880  # A5 note
    sine_wave, sr = create_sine_wave(freq, 5, 44100)
    output_file = os.path.join(output_dir, "sample4.mp3")
    temp_wav = os.path.join(output_dir, "temp.wav")
    wavfile.write(temp_wav, sr, sine_wave.astype(np.float32))
    audio = AudioSegment.from_wav(temp_wav)
    audio.export(output_file, format="mp3")
    os.remove(temp_wav)
    print(f"Created MP3 file with 880Hz: {output_file}")

    # Create a simple melody (multiple frequencies)
    sample_rate = 44100
    duration = 10
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Create a simple melody with multiple notes
    melody = np.zeros_like(t)
    notes = [440, 494, 523, 587, 659, 698, 784, 880]  # A4, B4, C5, D5, E5, F5, G5, A5
    note_duration = duration / len(notes)

    for i, note in enumerate(notes):
        start_idx = int(i * note_duration * sample_rate)
        end_idx = int((i + 1) * note_duration * sample_rate)
        melody[start_idx:end_idx] = 0.5 * np.sin(2 * np.pi * note * t[start_idx:end_idx])

    # Save the melody
    output_file = os.path.join(output_dir, "melody.mp3")
    temp_wav = os.path.join(output_dir, "temp.wav")
    wavfile.write(temp_wav, sample_rate, melody.astype(np.float32))
    audio = AudioSegment.from_wav(temp_wav)
    audio.export(output_file, format="mp3")
    os.remove(temp_wav)
    print(f"Created melody MP3 file: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create test audio files for testing.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join("backend", "tests", "data", "audio"),
        help="Output directory for test audio files",
    )
    parser.add_argument(
        "--filename", type=str, default="test_audio.mp3", help="Filename for the test audio file"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="mp3",
        choices=["mp3", "wav"],
        help="Format of the test audio file",
    )
    parser.add_argument(
        "--duration", type=float, default=5.0, help="Duration of the test audio file in seconds"
    )
    parser.add_argument(
        "--multiple",
        action="store_true",
        help="Create multiple test files with different characteristics",
    )

    args = parser.parse_args()

    if args.multiple:
        create_multiple_test_files()
    else:
        create_test_audio_file(args.output_dir, args.filename, args.format, args.duration)
