#!/usr/bin/env python3
"""
Script para poblar la base de datos con datos de ejemplo.

Uso:
    python scripts/seed_data.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.seed import seed_all


if __name__ == "__main__":
    seed_all()
