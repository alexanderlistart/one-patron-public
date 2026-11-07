import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
V01=PROJECT/'prototype_0p'
V02=PROJECT/'prototype_0p_v02'
V03=PROJECT/'prototype_0p_v03'
for path in (V03,V02,V01): sys.path.insert(0,str(path))
from canonical import load,encode,digest,write_new
