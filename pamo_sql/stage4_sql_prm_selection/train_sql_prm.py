"""
Train a SQL-PRM (Pairwise Reward Model) selector.

Three implementation options:
  Option 1: LLM judge (no training, use format_pairwise_input + call_llm)
  Option 2: Classification cross-encoder (DeBERTa baseline)
  Option 3: LoRA fine-tune on coder LLM (Qwen2.5-Coder / DeepSeek-Coder)

This file implements Option 2 as the default trainable baseline.
"""

import json
from pathlib import Path

from stage4_sql_prm_selection.format_pairwise_input import format_pair_for_training


def prepare_training_data(pairs_jsonl_path, output_dir):
    """
    Read pairwise JSONL, format for training, and split into train/dev.
    """
    pairs = []
    with open(pairs_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            pair = json.loads(line.strip())
            pairs.append(format_pair_for_training(pair))

    # Simple split: 90% train, 10% dev
    split_idx = int(len(pairs) * 0.9)
    train_data = pairs[:split_idx]
    dev_data = pairs[split_idx:]

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    train_path = str(Path(output_dir) / "train_pairs_formatted.jsonl")
    dev_path = str(Path(output_dir) / "dev_pairs_formatted.jsonl")

    for data, path in [(train_data, train_path), (dev_data, dev_path)]:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[prepare_training_data] Train: {len(train_data)}, Dev: {len(dev_data)}")
    return train_path, dev_path


def train_sql_prm(train_path, dev_path, model_name="microsoft/deberta-v3-base",
                  output_dir="artifacts/models/sql_prm_selector", **kwargs):
    """
    Train a 3-class classification model (A / B / tie) on pairwise data.

    Requires: transformers, datasets, torch
    """
    try:
        from datasets import load_dataset
        from transformers import (
            AutoTokenizer,
            AutoModelForSequenceClassification,
            TrainingArguments,
            Trainer
        )
    except ImportError as e:
        raise ImportError(
            "Training requires: pip install transformers datasets torch"
        ) from e

    label2id = {"A": 0, "B": 1, "tie": 2}
    id2label = {v: k for k, v in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3,
        label2id=label2id,
        id2label=id2label
    )

    dataset = load_dataset("json", data_files={
        "train": train_path,
        "validation": dev_path
    })

    def tokenize_fn(batch):
        return tokenizer(batch["text"], truncation=True, max_length=2048)

    dataset = dataset.map(lambda x: {"label": label2id[x["winner"]]})
    dataset = dataset.map(tokenize_fn, batched=True)

    args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=kwargs.get("learning_rate", 2e-5),
        per_device_train_batch_size=kwargs.get("batch_size", 8),
        per_device_eval_batch_size=kwargs.get("batch_size", 8),
        num_train_epochs=kwargs.get("epochs", 3),
        evaluation_strategy="steps",
        save_strategy="steps",
        logging_steps=50,
        save_steps=500,
        eval_steps=500,
        fp16=kwargs.get("fp16", True),
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"[train_sql_prm] Model saved to {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train SQL-PRM selector")
    parser.add_argument("--pairs", default="artifacts/stage4_pairs/train_pairs.jsonl")
    parser.add_argument("--output_dir", default="artifacts/models/sql_prm_selector")
    parser.add_argument("--model", default="microsoft/deberta-v3-base")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=8)
    args = parser.parse_args()

    train_path, dev_path = prepare_training_data(
        args.pairs, str(Path(args.output_dir) / "data")
    )
    train_sql_prm(
        train_path, dev_path,
        model_name=args.model,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
