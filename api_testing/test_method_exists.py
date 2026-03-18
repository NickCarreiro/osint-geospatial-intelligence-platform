#!/usr/bin/env python3
"""Test script to verify the _refresh_catalog_from_spacetrak method exists."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Import the class
from app.adapters.celestrak import CelesTrakAdapter

# Check if the method exists
print("Checking if _refresh_catalog_from_spacetrack method exists...")
print()

# Check the class
print("Methods in CelesTrakAdapter class:")
methods = [m for m in dir(CelesTrakAdapter) if not m.startswith('__')]
for method in methods:
    print(f"  - {method}")

print()

# Check if the specific method exists
if hasattr(CelesTrakAdapter, '_refresh_catalog_from_spacetrak'):
    print("✓ Method _refresh_catalog_from_spacetrack EXISTS in class")
else:
    print("✗ Method _refresh_catalog_from_spacetrack DOES NOT EXIST in class")

print()

# Create an instance and check
adapter = CelesTrakAdapter()
print("Methods in adapter instance:")
instance_methods = [m for m in dir(adapter) if not m.startswith('__')]
for method in instance_methods:
    print(f"  - {method}")

print()

if hasattr(adapter, '_refresh_catalog_from_spacetrak'):
    print("✓ Method _refresh_catalog_from_spacetrack EXISTS in instance")
else:
    print("✗ Method _refresh_catalog_from_spacetrak DOES NOT EXIST in instance")