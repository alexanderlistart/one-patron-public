"""Recompute the bound finite score. Stdout only; no new input or file writes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable import activate,emit,guard
activate()
if __name__=='__main__':
    guard()
    import engine5
    emit(engine5.kernel())
