"""Portable IO adapter. Original mathematical modules remain byte-identical."""
import sys
from portable import MACHINE,activate,guard
from pathlib import Path
activate()
ROOT=MACHINE/'prototype_0p_v04'
PROJECT=MACHINE
V01=PROJECT/'prototype_0p'
V02=PROJECT/'prototype_0p_v02'
V03=PROJECT/'prototype_0p_v03'
V03A=PROJECT/'prototype_0p_v03a'
from canonical import load,encode,digest,write_new

def inputs():
    return (load(V02/'fixtures/genesis.json'),load(V02/'fixtures/continuations.json'),
            load(V03/'fixtures/history_inputs.json'),load(V03A/'fixtures/choices.json')['cases'])

def protected_integrity():return guard()
