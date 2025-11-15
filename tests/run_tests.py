#!/usr/bin/env python3
"""
Script pour exécuter tous les tests unitaires avec pytest.
Usage: python3 tests/run_tests.py
"""
import sys
import os
import subprocess

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    # Changer vers le répertoire tests
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Exécuter tous les tests avec pytest
    result = subprocess.run(['python3', '-m', 'pytest', '-v'], capture_output=False)
    sys.exit(result.returncode)
