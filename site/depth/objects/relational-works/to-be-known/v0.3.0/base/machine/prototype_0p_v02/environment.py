"""Locate immutable v0.1 dependencies; no computation shared with the new verifier."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
LEGACY = PROJECT / 'prototype_0p'
sys.path.insert(0, str(LEGACY))
from canonical import load, encode, digest, write_new
