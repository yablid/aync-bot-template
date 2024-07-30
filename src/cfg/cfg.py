"""load cfg"""

import yaml
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
print(ROOT_DIR)

def load_yaml(path_from_root: str) -> dict:

    fp = ROOT_DIR / path_from_root

    with open(fp, 'r') as f:
        cfg = yaml.safe_load(f)
        return cfg


CFG = load_yaml('cfg/cfg.yaml')

if __name__ == '__main__':
    print(CFG)