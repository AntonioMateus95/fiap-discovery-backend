from pathlib import Path

import yaml

ASSETS_DIR = Path(__file__).parent.parent / "assets"


def build_semantic_catalog(
    base_catalog_path: Path | None = None,
    dataset_path: Path | None = None,
) -> str:
    base_catalog_path = base_catalog_path or ASSETS_DIR / "base_semantic_catalog.yaml"
    dataset_path = dataset_path or ASSETS_DIR / "datasets" / "abertura_empresas.yaml"

    with open(base_catalog_path, encoding="utf-8") as f:
        catalog = yaml.safe_load(f)

    with open(dataset_path, encoding="utf-8") as f:
        dataset = yaml.safe_load(f)

    catalog["datasets"] = dataset
    return yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True)
