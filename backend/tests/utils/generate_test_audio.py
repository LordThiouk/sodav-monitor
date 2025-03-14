#!/usr/bin/env python3
"""
Script pour générer des fichiers audio synthétiques pour les tests.

Ce script crée des fichiers audio synthétiques avec différentes caractéristiques
pour tester le système de détection musicale.
"""

import argparse
import logging
import os
import random
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sawtooth, Sine, Square, WhiteNoise
from radio_simulator import AUDIO_DIR

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("generate_test_audio")


def generate_tone(frequency, duration_ms=5000, sample_rate=44100, waveform="sine"):
    """
    Génère un ton simple.

    Args:
        frequency: Fréquence en Hz
        duration_ms: Durée en millisecondes
        sample_rate: Taux d'échantillonnage
        waveform: Type de forme d'onde ("sine", "square", "sawtooth", "noise")

    Returns:
        Segment audio généré
    """
    if waveform == "sine":
        generator = Sine(frequency, sample_rate=sample_rate)
    elif waveform == "square":
        generator = Square(frequency, sample_rate=sample_rate)
    elif waveform == "sawtooth":
        generator = Sawtooth(frequency, sample_rate=sample_rate)
    elif waveform == "noise":
        generator = WhiteNoise(sample_rate=sample_rate)
    else:
        raise ValueError(f"Type de forme d'onde non pris en charge: {waveform}")

    return generator.to_audio_segment(duration=duration_ms)


def generate_melody(notes, durations, sample_rate=44100, waveform="sine"):
    """
    Génère une mélodie à partir d'une séquence de notes.

    Args:
        notes: Liste des fréquences en Hz
        durations: Liste des durées en millisecondes
        sample_rate: Taux d'échantillonnage
        waveform: Type de forme d'onde

    Returns:
        Segment audio généré
    """
    if len(notes) != len(durations):
        raise ValueError("Les listes de notes et de durées doivent avoir la même longueur")

    melody = AudioSegment.silent(duration=0)

    for note, duration in zip(notes, durations):
        tone = generate_tone(note, duration, sample_rate, waveform)
        melody += tone

    return melody


def generate_rhythm(pattern, sample_rate=44100, tempo=120):
    """
    Génère un rythme à partir d'un motif.

    Args:
        pattern: Motif rythmique (liste de 0 et 1)
        sample_rate: Taux d'échantillonnage
        tempo: Tempo en BPM

    Returns:
        Segment audio généré
    """
    # Durée d'une noire en millisecondes
    beat_duration = 60000 / tempo

    # Durée d'un pas du motif (généralement une double-croche)
    step_duration = beat_duration / 4

    rhythm = AudioSegment.silent(duration=0)

    # Son de "kick" (basse fréquence)
    kick = generate_tone(60, 100, sample_rate, "sine")
    kick = kick.apply_gain(10)  # Augmenter le volume

    # Son de "snare" (bruit blanc)
    snare = generate_tone(0, 80, sample_rate, "noise")
    snare = snare.apply_gain(5)

    # Son de "hi-hat" (haute fréquence)
    hihat = generate_tone(8000, 50, sample_rate, "noise")
    hihat = hihat.apply_gain(-5)  # Réduire le volume

    # Générer le rythme
    for i, beat in enumerate(pattern):
        if beat == 1:
            # Alterner entre kick, snare et hi-hat
            if i % 16 == 0 or i % 16 == 8:
                rhythm += kick
            elif i % 16 == 4 or i % 16 == 12:
                rhythm += snare
            else:
                rhythm += hihat
        else:
            # Silence
            rhythm += AudioSegment.silent(duration=step_duration)

    return rhythm


def generate_random_melody(duration_sec=30, sample_rate=44100, waveform="sine"):
    """
    Génère une mélodie aléatoire.

    Args:
        duration_sec: Durée en secondes
        sample_rate: Taux d'échantillonnage
        waveform: Type de forme d'onde

    Returns:
        Segment audio généré
    """
    # Notes de la gamme pentatonique (fréquences en Hz)
    pentatonic_scale = [261.63, 293.66, 329.63, 392.00, 440.00]

    # Durées possibles des notes (en millisecondes)
    possible_durations = [250, 500, 750, 1000]

    # Générer des notes aléatoires
    total_duration = 0
    notes = []
    durations = []

    while total_duration < duration_sec * 1000:
        note = random.choice(pentatonic_scale)
        duration = random.choice(possible_durations)

        notes.append(note)
        durations.append(duration)

        total_duration += duration

    return generate_melody(notes, durations, sample_rate, waveform)


def generate_random_rhythm(duration_sec=30, sample_rate=44100, tempo=120):
    """
    Génère un rythme aléatoire.

    Args:
        duration_sec: Durée en secondes
        sample_rate: Taux d'échantillonnage
        tempo: Tempo en BPM

    Returns:
        Segment audio généré
    """
    # Durée d'une noire en millisecondes
    beat_duration = 60000 / tempo

    # Nombre de pas nécessaires pour atteindre la durée souhaitée
    steps_needed = int((duration_sec * 1000) / (beat_duration / 4))

    # Générer un motif rythmique aléatoire
    pattern = []
    for _ in range(steps_needed):
        # 30% de chance d'avoir un son
        if random.random() < 0.3:
            pattern.append(1)
        else:
            pattern.append(0)

    return generate_rhythm(pattern, sample_rate, tempo)


def generate_senegal_style_rhythm(duration_sec=30, sample_rate=44100):
    """
    Génère un rythme inspiré des styles musicaux sénégalais (mbalax, sabar).

    Args:
        duration_sec: Durée en secondes
        sample_rate: Taux d'échantillonnage

    Returns:
        Segment audio généré
    """
    # Motif rythmique inspiré du mbalax (16 pas par mesure)
    # 1 = son, 0 = silence
    mbalax_pattern = [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0]

    # Répéter le motif pour atteindre la durée souhaitée
    tempo = random.randint(110, 140)  # Tempo typique du mbalax
    beat_duration = 60000 / tempo
    steps_per_pattern = len(mbalax_pattern)
    pattern_duration = steps_per_pattern * (beat_duration / 4)

    repetitions = int((duration_sec * 1000) / pattern_duration) + 1
    full_pattern = mbalax_pattern * repetitions

    return generate_rhythm(full_pattern, sample_rate, tempo)


def generate_test_audio_file(output_path, duration_sec=30, style="senegal", sample_rate=44100):
    """
    Génère un fichier audio de test.

    Args:
        output_path: Chemin de sortie
        duration_sec: Durée en secondes
        style: Style musical ("senegal", "melody", "rhythm", "mixed")
        sample_rate: Taux d'échantillonnage

    Returns:
        Chemin vers le fichier généré
    """
    # Générer l'audio selon le style demandé
    if style == "senegal":
        # Combiner un rythme sénégalais avec une mélodie
        rhythm = generate_senegal_style_rhythm(duration_sec, sample_rate)
        melody = generate_random_melody(duration_sec, sample_rate)

        # Mixer les deux (70% rythme, 30% mélodie)
        audio = rhythm.overlay(melody.apply_gain(-10))

    elif style == "melody":
        audio = generate_random_melody(duration_sec, sample_rate)

    elif style == "rhythm":
        audio = generate_random_rhythm(duration_sec, sample_rate)

    elif style == "mixed":
        # Mélange de différents styles
        segments = []
        remaining_duration = duration_sec

        while remaining_duration > 0:
            segment_duration = min(remaining_duration, random.randint(5, 10))
            style_choice = random.choice(["melody", "rhythm", "senegal"])

            if style_choice == "melody":
                segment = generate_random_melody(segment_duration, sample_rate)
            elif style_choice == "rhythm":
                segment = generate_random_rhythm(segment_duration, sample_rate)
            else:
                segment = generate_senegal_style_rhythm(segment_duration, sample_rate)

            segments.append(segment)
            remaining_duration -= segment_duration

        # Concaténer tous les segments
        audio = segments[0]
        for segment in segments[1:]:
            audio += segment

    else:
        raise ValueError(f"Style non pris en charge: {style}")

    # Exporter le fichier
    audio.export(output_path, format="mp3")
    logger.info(f"Fichier audio généré: {output_path}")

    return output_path


def generate_multiple_test_files(output_dir=None, count=5, duration_range=(10, 30), styles=None):
    """
    Génère plusieurs fichiers audio de test.

    Args:
        output_dir: Répertoire de sortie (utilise le répertoire par défaut si None)
        count: Nombre de fichiers à générer
        duration_range: Plage de durées en secondes (min, max)
        styles: Liste des styles à utiliser (utilise tous les styles si None)

    Returns:
        Liste des chemins vers les fichiers générés
    """
    if output_dir is None:
        output_dir = AUDIO_DIR

    if styles is None:
        styles = ["senegal", "melody", "rhythm", "mixed"]

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Générer les fichiers
    generated_files = []
    for i in range(count):
        # Choisir un style aléatoire
        style = random.choice(styles)

        # Choisir une durée aléatoire
        duration = random.randint(duration_range[0], duration_range[1])

        # Générer un nom de fichier
        filename = f"synthetic_{style}_{i+1}_{duration}s.mp3"
        output_path = os.path.join(output_dir, filename)

        # Générer le fichier
        generate_test_audio_file(output_path, duration, style)
        generated_files.append(output_path)

    logger.info(f"{len(generated_files)} fichiers audio générés dans {output_dir}")
    return generated_files


def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Génère des fichiers audio synthétiques pour les tests"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Répertoire de sortie pour les fichiers générés",
    )
    parser.add_argument("--count", type=int, default=5, help="Nombre de fichiers à générer")
    parser.add_argument("--min-duration", type=int, default=10, help="Durée minimale en secondes")
    parser.add_argument("--max-duration", type=int, default=30, help="Durée maximale en secondes")
    parser.add_argument(
        "--styles",
        type=str,
        nargs="+",
        default=None,
        choices=["senegal", "melody", "rhythm", "mixed"],
        help="Styles musicaux à générer",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    if output_dir:
        output_dir = Path(output_dir)

    generated_files = generate_multiple_test_files(
        output_dir, args.count, (args.min_duration, args.max_duration), args.styles
    )

    if generated_files:
        logger.info("Génération terminée avec succès")
        for file_path in generated_files:
            logger.info(f"  - {file_path}")
    else:
        logger.warning("Aucun fichier n'a été généré")


if __name__ == "__main__":
    main()
