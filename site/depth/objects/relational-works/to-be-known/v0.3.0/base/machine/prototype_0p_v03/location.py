import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
V01=PROJECT/'prototype_0p'
V02=PROJECT/'prototype_0p_v02'
sys.path.insert(0,str(V02))
sys.path.insert(0,str(V01))
from canonical import load, encode, digest, write_new
