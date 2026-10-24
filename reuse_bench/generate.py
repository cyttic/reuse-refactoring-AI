"""GPU stage: generate refactorings for every task x condition x instruction with an open model.

    python -m reuse_bench.generate --tasks data/tasks/*.jsonl --model Qwen/Qwen2.5-Coder-7B-Instruct \
        --out results/<run>/generations.jsonl

Resumable: prompts already present in --out are skipped.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from pathlib import Path

from .index import RepoIndex
from .prompting import CONDITIONS, INSTRUCTIONS, TaskContext, build_prompt, load_tasks


class VLLMBackend:
    def __init__(self, args):
        from vllm import LLM, SamplingParams
        self.llm = LLM(model=args.model, max_model_len=args.max_model_len, seed=args.seed,
                       gpu_memory_utilization=args.gpu_memory_utilization,
                       quantization=args.quantization, trust_remote_code=True)
        self.params = SamplingParams(temperature=args.temperature, max_tokens=args.max_tokens, seed=args.seed)

    def generate(self, conversations: list[list[dict]]) -> list[str]:
        outputs = self.llm.chat(conversations, self.params, use_tqdm=True)
        return [o.outputs[0].text for o in outputs]


class HFBackend:
    """Fallback when vLLM cannot be installed; much slower (one prompt at a time)."""

    def __init__(self, args):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        print(f"loading {args.model} (downloads on first use) ...")
        self.tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
        # sdpa avoids materialising the full attention matrix for long prompts
        self.model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto", device_map="auto",
                                                          attn_implementation="sdpa", trust_remote_code=True)
        offloaded = {d for d in getattr(self.model, "hf_device_map", {}).values() if d in ("cpu", "disk")}
        if offloaded:
            print(f"WARNING: part of the model is on {offloaded}, generation will be very slow. "
                  "Free GPU memory (nvidia-smi) or use a smaller/quantized model.")
        print(f"model loaded on {self.model.device}")
        self.args = args

    def generate(self, conversations: list[list[dict]]) -> list[str]:
        texts = []
        for i, messages in enumerate(conversations, 1):
            t0 = time.time()
            # return_dict=True gives the same type on old and new transformers versions
            inputs = self.tok.apply_chat_template(messages, add_generation_prompt=True, return_dict=True,
                                                  return_tensors="pt").to(self.model.device)
            n_in = inputs["input_ids"].shape[1]
            sample = self.args.temperature > 0
            try:
                with self.torch.no_grad():
                    out = self.model.generate(**inputs, max_new_tokens=self.args.max_tokens, do_sample=sample,
                                              temperature=self.args.temperature if sample else None,
                                              pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
            except self.torch.OutOfMemoryError:
                # Very long prompts do not fit for models without grouped-query attention; record and go on.
                del inputs
                self.torch.cuda.empty_cache()
                texts.append(None)
                print(f"    prompt {i}/{len(conversations)}: {n_in} tokens in, OUT OF GPU MEMORY (skipped)")
                continue
            texts.append(self.tok.decode(out[0, n_in:], skip_special_tokens=True))
            print(f"    prompt {i}/{len(conversations)}: {n_in} tokens in, "
                  f"{out.shape[1] - n_in} out, {time.time() - t0:.0f}s")
            del out, inputs
            self.torch.cuda.empty_cache()
        return texts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", type=Path, nargs="+", required=True)
    parser.add_argument("--repos-dir", type=Path, default=Path("data/repos"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--instructions", default=",".join(INSTRUCTIONS))
    parser.add_argument("--k", type=int, default=5, help="retrieved snippets for bm25")
    parser.add_argument("--limit", type=int, help="only the first N tasks (for smoke tests)")
    parser.add_argument("--backend", choices=["vllm", "hf"], default="vllm")
    parser.add_argument("--max-model-len", type=int, default=16384)
    parser.add_argument("--max-file-chars", type=int, default=30000)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--quantization", default=None, help="e.g. awq; usually auto-detected")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--no-system-prompt", action="store_true", help="for chat templates without a system role")
    parser.add_argument("--chunk", type=int, default=64, help="prompts per batch written to disk")
    parser.add_argument("--dry-run", action="store_true", help="build prompts only, no model")
    args = parser.parse_args(argv)

    tasks = load_tasks(args.tasks)[: args.limit]
    conditions, instructions = args.conditions.split(","), args.instructions.split(",")
    done = set()
    if args.out.exists():
        done = {(r["task_id"], r["condition"], r["instruction"])
                for r in map(json.loads, args.out.read_text().splitlines())}

    indexes: dict[str, RepoIndex] = {}
    jobs = []
    for task in tasks:
        repo_root = args.repos_dir / task["repo"]
        if task["repo"] not in indexes:
            indexes[task["repo"]] = RepoIndex.build(repo_root)
        ctx = TaskContext(task, repo_root, indexes[task["repo"]])
        for condition in conditions:
            for instruction in instructions:
                if (task["id"], condition, instruction) in done:
                    continue
                messages, meta = build_prompt(ctx, condition, instruction, args.k, args.max_file_chars,
                                              system_prompt=not args.no_system_prompt)
                jobs.append(({"task_id": task["id"], "condition": condition, "instruction": instruction,
                              "model": args.model, **meta,
                              "prompt_sha256": hashlib.sha256(json.dumps(messages).encode()).hexdigest()},
                             messages))
    print(f"{len(tasks)} tasks, {len(jobs)} prompts to generate ({len(done)} already done)")
    if args.dry_run or not jobs:
        if jobs:
            print(jobs[0][1][-1]["content"][:3000])
        return

    backend = VLLMBackend(args) if args.backend == "vllm" else HFBackend(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(jobs), args.chunk):
        chunk = jobs[start: start + args.chunk]
        t0 = time.time()
        texts = backend.generate([messages for _, messages in chunk])
        seconds = round((time.time() - t0) / len(chunk), 2)
        with args.out.open("a", encoding="utf-8") as fh:
            for (record, _), text in zip(chunk, texts):
                error = {"error": "out of GPU memory"} if text is None else {}
                fh.write(json.dumps({**record, "output": text or "", **error, "seconds_per_prompt": seconds}) + "\n")
        # Full prompts are large; keep them compressed next to the generations (appending gzip members is valid).
        with gzip.open(args.out.with_name("prompts.jsonl.gz"), "at", encoding="utf-8") as fh:
            for record, messages in chunk:
                fh.write(json.dumps({"prompt_sha256": record["prompt_sha256"], "messages": messages}) + "\n")
        print(f"  {start + len(chunk)}/{len(jobs)} prompts ({time.time() - t0:.0f}s for this chunk)")


if __name__ == "__main__":
    main()
