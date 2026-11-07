"""Portable IO adapter ONLY. No formation, Q/L/M, sigma or choice mathematics."""
from pathlib import Path
from portable import MACHINE,activate,guard
activate()
ROOT=MACHINE/'prototype_0p_v05'
PROJECT=MACHINE
OLD=[PROJECT/n for n in ('prototype_0p_v04','prototype_0p_v03a','prototype_0p_v03','prototype_0p_v02','prototype_0p')]
from canonical import load,encode,digest,write_new

def integrity():return guard()
def plans():return load(ROOT/'fixtures/layout.json')['cases']
def static_choices(_prepared):return load(ROOT/'fixtures/choices.json')['cases']
