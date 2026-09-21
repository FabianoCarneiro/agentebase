"""Faz `import agent` funcionar rodando o pytest da raiz do projeto ou de
dentro de tests/ — sem isso, o pytest não acha o módulo `agent`, já que ele
mora na raiz e não é um pacote instalado.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
