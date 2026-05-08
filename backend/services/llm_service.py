"""
LLM Service — loads a HuggingFace causal-LM locally and exposes
helper methods used by model_builder, forecast_engine and the chat router.

Supported models (in order of preference):
  1. Qwen/Qwen2.5-7B-Instruct  (needs ~14 GB VRAM or ~28 GB RAM)
  2. Qwen/Qwen2.5-3B-Instruct  (needs ~6 GB VRAM or ~12 GB RAM)
  3. Qwen/Qwen2.5-1.5B-Instruct (CPU-friendly fallback)

GPU users get 4-bit NF4 quantisation via bitsandbytes.
CPU users get the model loaded in float32 (slow but works).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── global singleton ──────────────────────────────────────────────────────────

_tokenizer = None
_model = None
_llm_meta: Dict[str, Any] = {
    "loaded": False,
    "model_name": None,
    "device": None,
    "quantized": False,
    "error": None,
}


# ── public status ─────────────────────────────────────────────────────────────

def get_status() -> Dict[str, Any]:
    return dict(_llm_meta)


def is_loaded() -> bool:
    return _llm_meta["loaded"]


# ── loader ────────────────────────────────────────────────────────────────────

CANDIDATE_MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
]


def load_model(model_name: Optional[str] = None, force_cpu: bool = False) -> Dict[str, Any]:
    """
    Download (first time) and load the model into memory.
    Returns the current status dict.
    """
    global _tokenizer, _model, _llm_meta

    if _llm_meta["loaded"]:
        return get_status()

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    except ImportError as e:
        _llm_meta["error"] = f"Missing dependency: {e}. Run: pip install torch transformers bitsandbytes accelerate"
        return get_status()

    candidates = [model_name] if model_name else CANDIDATE_MODELS
    device = "cpu" if force_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    use_4bit = (device == "cuda")

    for name in candidates:
        try:
            logger.info(f"Loading {name} on {device} (4-bit={use_4bit}) …")

            _tokenizer = AutoTokenizer.from_pretrained(
                name,
                trust_remote_code=True,
            )

            if use_4bit:
                bnb_cfg = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
                _model = AutoModelForCausalLM.from_pretrained(
                    name,
                    quantization_config=bnb_cfg,
                    device_map="auto",
                    trust_remote_code=True,
                )
            else:
                _model = AutoModelForCausalLM.from_pretrained(
                    name,
                    device_map="cpu",
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                )

            _llm_meta.update(
                loaded=True,
                model_name=name,
                device=device,
                quantized=use_4bit,
                error=None,
            )
            logger.info(f"LLM ready: {name} on {device}")
            return get_status()

        except Exception as e:
            logger.warning(f"Failed to load {name}: {e}")
            continue

    _llm_meta["error"] = "All candidate models failed to load. Check RAM/VRAM and network."
    return get_status()


# ── inference helper ──────────────────────────────────────────────────────────

def _generate(system_prompt: str, user_prompt: str, max_new_tokens: int = 512) -> str:
    """Low-level generation wrapper."""
    if not _llm_meta["loaded"]:
        raise RuntimeError("LLM not loaded. Call load_model() first.")

    import torch

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    text = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = _tokenizer([text], return_tensors="pt")
    if _llm_meta["device"] == "cuda":
        inputs = {k: v.cuda() for k, v in inputs.items()}

    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=_tokenizer.eos_token_id,
        )

    # strip prompt tokens
    generated = output_ids[0][inputs["input_ids"].shape[1]:]
    return _tokenizer.decode(generated, skip_special_tokens=True).strip()


# ── task-specific helpers ─────────────────────────────────────────────────────

def enhance_line_item_mapping(raw_label: str, candidate_ids: List[str], context: str = "") -> Dict[str, Any]:
    """
    Given a raw PDF label and a ranked list of candidate standard IDs,
    return {"standard_id": ..., "confidence": 0-1, "reasoning": ...}.
    Falls back to top candidate if LLM unavailable.
    """
    if not is_loaded():
        return {"standard_id": candidate_ids[0] if candidate_ids else "unknown",
                "confidence": 0.5, "reasoning": "LLM not available"}

    system = (
        "You are an expert financial analyst. "
        "Map raw financial statement line items to standardised IDs. "
        "Reply ONLY with valid JSON."
    )
    user = (
        f"Raw label: \"{raw_label}\"\n"
        f"Context: {context or 'N/A'}\n"
        f"Candidate IDs: {json.dumps(candidate_ids)}\n\n"
        "Choose the best matching standard_id from the candidates. "
        "Return JSON: {{\"standard_id\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}}"
    )
    try:
        raw = _generate(system, user, max_new_tokens=128)
        # extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.warning(f"LLM mapping failed: {e}")
    return {"standard_id": candidate_ids[0] if candidate_ids else "unknown",
            "confidence": 0.5, "reasoning": "LLM parse error"}


def generate_forecast_assumptions(
    historical: Dict[str, Dict[str, float]],  # standard_id -> period -> value
    periods_to_forecast: List[str],
    company_context: str = "",
) -> Dict[str, Any]:
    """
    Returns {"assumptions": {standard_id: {"growth_rate": float, "rationale": str}}}
    """
    if not is_loaded():
        # naive fallback: 5% growth
        return {
            "assumptions": {
                sid: {"growth_rate": 0.05, "rationale": "LLM not available; using 5% default"}
                for sid in historical
            }
        }

    summary_lines = []
    for sid, periods in list(historical.items())[:20]:  # cap to avoid huge prompt
        vals = ", ".join(f"{p}: {v:.0f}" for p, v in sorted(periods.items()))
        summary_lines.append(f"  {sid}: {vals}")

    system = (
        "You are a senior equity analyst. "
        "Analyse historical financial data and produce realistic growth-rate assumptions. "
        "Reply ONLY with valid JSON."
    )
    user = (
        f"Company context: {company_context or 'N/A'}\n"
        f"Historical data (values in reporting currency):\n" + "\n".join(summary_lines) + "\n\n"
        f"Periods to forecast: {periods_to_forecast}\n\n"
        "For each line item ID above, return a JSON object:\n"
        "{{\"assumptions\": {{\"<id>\": {{\"growth_rate\": 0.05, \"rationale\": \"...\"}}, ...}}}}"
    )
    try:
        raw = _generate(system, user, max_new_tokens=1024)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.warning(f"LLM forecast failed: {e}")
    # fallback
    return {
        "assumptions": {
            sid: {"growth_rate": 0.05, "rationale": "LLM parse error; using 5% default"}
            for sid in historical
        }
    }


def chat_about_financials(
    project_summary: str,
    conversation_history: List[Dict[str, str]],
    user_message: str,
) -> str:
    """
    General-purpose financial chat. Returns assistant reply string.
    """
    if not is_loaded():
        return (
            "The local LLM is not yet loaded. "
            "Please go to the LLM Setup page and click 'Load Model'."
        )

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-10:]  # last 10 turns
    )

    system = (
        "You are an expert financial analyst assistant. "
        "You have access to the company's financial data summary below. "
        "Answer questions clearly and concisely."
    )
    user = (
        f"COMPANY DATA SUMMARY:\n{project_summary}\n\n"
        f"CONVERSATION HISTORY:\n{history_text}\n\n"
        f"USER: {user_message}"
    )
    try:
        return _generate(system, user, max_new_tokens=512)
    except Exception as e:
        return f"Error generating response: {e}"
