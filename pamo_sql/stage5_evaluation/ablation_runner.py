import json
import copy
from pathlib import Path
import yaml


def load_ablation_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_overrides(base_config, overrides):
    """Apply dot-notation overrides to a config dict."""
    config = copy.deepcopy(base_config)
    for key, value in overrides.items():
        parts = key.split(".")
        target = config
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return config


def run_ablation(config_path, run_pipeline_fn, dataset_path, db_dir, output_dir):
    """
    Run all ablation variants defined in the config.

    Args:
        config_path: path to experiment_ablation.yaml
        run_pipeline_fn: callable(config, dataset_path, db_dir, output_path) -> results
        dataset_path: path to dataset JSON
        db_dir: path to database directory
        output_dir: directory to save ablation results
    """
    config = load_ablation_config(config_path)
    variants = config.get("ablation_variants", [])

    base_config = {
        "stages": config["stages"],
        "generation": config["generation"],
    }

    all_results = []

    for variant in variants:
        name = variant["name"]
        description = variant.get("description", "")
        overrides = variant.get("overrides", {})

        variant_config = apply_overrides(base_config, overrides)
        variant_output = str(Path(output_dir) / name)
        Path(variant_output).mkdir(parents=True, exist_ok=True)

        print(f"[ablation] Running variant: {name} — {description}")

        try:
            result = run_pipeline_fn(
                variant_config, dataset_path, db_dir, variant_output
            )
            result["variant"] = name
            result["description"] = description
            result["config_overrides"] = overrides
            all_results.append(result)
        except Exception as e:
            all_results.append({
                "variant": name,
                "description": description,
                "error": str(e),
            })
            print(f"[ablation] ERROR in {name}: {e}")

    summary_path = str(Path(output_dir) / "ablation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"[ablation] Summary saved to {summary_path}")
    return all_results
