#!/usr/bin/env python3
"""
Script pour exécuter tous les tests unitaires.
Usage: python3 tests/run_tests.py
"""
import unittest
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_tests():
    """Charge tous les tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Charger tous les modules de test
    test_modules = [
        'test_kodi_metadata_provider',
        'test_cache_provider',
        'test_imdb_provider',
        'test_zoom_applier',
    ]
    
    for module_name in test_modules:
        try:
            module = __import__(module_name)
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
        except Exception as e:
            print(f"Erreur lors du chargement de {module_name}: {e}")
    
    return suite


if __name__ == "__main__":
    # Changer vers le répertoire tests pour les imports
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Exécuter les tests
    suite = load_tests()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Retourner le code de sortie approprié
    sys.exit(0 if result.wasSuccessful() else 1)

