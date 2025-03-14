#!/usr/bin/env python3
"""
Verification script for SODAV Monitor fixes.

This script verifies that the fixes for the log manager and SciPy issues are working correctly.
"""

import importlib
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_log_manager():
    """Check if the LogManager can be imported correctly."""
    print("Checking LogManager import...")

    try:
        from backend.logs import LogManager

        log_manager = LogManager()
        logger = log_manager.get_logger("verify_fixes")
        logger.info("LogManager imported successfully")
        print("✅ LogManager import successful")
        return True
    except ImportError as e:
        print(f"❌ LogManager import failed: {e}")
        return False


def check_scipy():
    """Check if SciPy can be imported correctly."""
    print("Checking SciPy import...")

    try:
        import scipy
        import scipy.signal

        print(f"✅ SciPy import successful (version: {scipy.__version__})")
        return True
    except ImportError as e:
        print(f"❌ SciPy import failed: {e}")
        return False


def check_feature_extractor():
    """Check if the FeatureExtractor can be imported correctly."""
    print("Checking FeatureExtractor import...")

    try:
        # First check if the module exists
        if not os.path.exists(
            project_root / "backend" / "detection" / "audio_processor" / "feature_extractor.py"
        ):
            print("❌ FeatureExtractor file not found")
            return False

        # Try to import the module
        spec = importlib.util.find_spec("backend.detection.audio_processor.feature_extractor")
        if spec is None:
            print("❌ FeatureExtractor module not found")
            return False

        # Try to import the class
        try:
            from backend.detection.audio_processor.feature_extractor import FeatureExtractor

            print("✅ FeatureExtractor import successful")
            return True
        except ImportError as e:
            print(f"❌ FeatureExtractor import failed: {e}")
            return False
    except Exception as e:
        print(f"❌ Error checking FeatureExtractor: {e}")
        return False


def main():
    """Run all verification checks."""
    print("Running verification checks for SODAV Monitor fixes...\n")

    log_manager_ok = check_log_manager()
    print()

    scipy_ok = check_scipy()
    print()

    feature_extractor_ok = check_feature_extractor()
    print()

    # Summary
    print("Verification Summary:")
    print(f"LogManager: {'✅ OK' if log_manager_ok else '❌ Failed'}")
    print(f"SciPy: {'✅ OK' if scipy_ok else '❌ Failed'}")
    print(f"FeatureExtractor: {'✅ OK' if feature_extractor_ok else '❌ Failed'}")

    if log_manager_ok and scipy_ok and feature_extractor_ok:
        print("\n✅ All checks passed! The fixes appear to be working correctly.")
        return 0
    else:
        print("\n❌ Some checks failed. Please review the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
