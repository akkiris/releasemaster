#!/usr/bin/env python3
"""Build dist/releasemaster-skill.zip for upload to claude.ai (Settings > Capabilities > Skills)."""
import os, zipfile
SRC = os.path.join(os.path.dirname(__file__), "..", "plugins", "releasemaster", "skills", "releasemaster")
OUT = os.path.join(os.path.dirname(__file__), "..", "dist", "releasemaster-skill.zip")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(SRC):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in files:
            p = os.path.join(d, f)
            z.write(p, os.path.join("releasemaster", os.path.relpath(p, SRC)))
print("wrote", os.path.abspath(OUT))
