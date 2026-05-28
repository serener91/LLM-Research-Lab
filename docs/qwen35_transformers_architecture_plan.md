# Implementing a hypothetical **Qwen3.5** architecture in Hugging Face `transformers`

This guide is a practical, end-to-end blueprint for adding a **new model architecture** (e.g., Qwen3.5, different from Qwen3) to the `transformers` codebase so you can prototype, run inference, train, and publish.

> Scope: This follows the current `transformers` model-integration pattern used for modern decoder-only LLMs. The exact file names in upstream can shift slightly across versions, but the workflow and responsibilities remain the same.

---

## 0) Mental model of what you are adding

A new Transformers architecture usually consists of:

1. **Config class** (`PretrainedConfig`)  
   - Stores architecture hyperparameters and serialization defaults.
2. **PyTorch model class(es)** (`PreTrainedModel`)  
   - Core transformer blocks and task heads (CausalLM first).
3. **Tokenizer / processor mapping**  
   - Usually reuse existing tokenizer if vocabulary format is unchanged.
4. **AutoClass registration**  
   - Enables `AutoConfig`, `AutoModel`, `AutoModelForCausalLM`.
5. **Conversion script** (optional but common)  
   - Converts original checkpoints into HF format.
6. **Tests**  
   - Config tests, shape tests, cache/generation tests, save/load tests.
7. **Docs + model card snippets**  
   - User-facing docs and examples.

For Qwen3.5, start from Qwen3 implementation and create a **parallel model family** (`qwen3_5`) to avoid destabilizing existing Qwen3 users.

---

## 1) Create architecture contract first (before coding)

Write a one-page architecture contract that freezes these decisions:

- Hidden size, heads, KV heads (GQA/MQA), layers.
- Positional encoding variant (RoPE base/scaling or alternative).
- Attention mechanism differences (e.g., grouped attention, sliding-window, hybrid local/global).
- MLP block type (SwiGLU, MoE, gated linear variants).
- Normalization and residual ordering.
- Cache layout and generation behavior.
- Special tokens and vocab assumptions.
- Backward-compat constraints with Qwen3 tokenizer/checkpoints.

This document will prevent repeated refactors when wiring config ↔ model ↔ tests.

---

## 2) Files to add/modify in `transformers`

Below is the **practical file map** to implement a new architecture.

## A. New model package directory

Add a new package under:

- `src/transformers/models/qwen3_5/`

Create:

1. `src/transformers/models/qwen3_5/__init__.py`
2. `src/transformers/models/qwen3_5/configuration_qwen3_5.py`
3. `src/transformers/models/qwen3_5/modeling_qwen3_5.py`
4. `src/transformers/models/qwen3_5/tokenization_qwen3_5.py` *(only if tokenizer differs)*
5. `src/transformers/models/qwen3_5/tokenization_qwen3_5_fast.py` *(only if fast tokenizer differs)*
6. `src/transformers/models/qwen3_5/convert_qwen3_5_weights_to_hf.py` *(recommended)*

## B. Core registry and auto-mapping integration

Update global mappings:

1. `src/transformers/models/auto/configuration_auto.py`
   - Add `"qwen3_5" -> Qwen3_5Config`.
2. `src/transformers/models/auto/modeling_auto.py`
   - Add `Qwen3_5Config -> Qwen3_5Model` and `Qwen3_5ForCausalLM` mappings.
3. `src/transformers/__init__.py`
   - Export config/model/tokenizer symbols.

Depending on current repo structure, you may also need to touch lazy-import map files used to expose modules safely.

## C. Tests

Add:

1. `tests/models/qwen3_5/test_modeling_qwen3_5.py`
2. `tests/models/qwen3_5/test_configuration_qwen3_5.py`
3. `tests/models/qwen3_5/test_tokenization_qwen3_5.py` *(if tokenizer changes)*

If generation/cache edge cases are novel, add targeted tests in existing generation test suites too.

## D. Docs

Add:

1. `docs/source/en/model_doc/qwen3_5.md`

Update:

1. `docs/source/en/_toctree.yml` (or current nav file) to include Qwen3.5 docs.

---

## 3) Step-by-step implementation plan

## Step 1 — Bootstrap from Qwen3 code

- Copy Qwen3 config/model files to new Qwen3.5 files.
- Rename classes consistently:
  - `Qwen3Config` -> `Qwen3_5Config`
  - `Qwen3Model` -> `Qwen3_5Model`
  - `Qwen3ForCausalLM` -> `Qwen3_5ForCausalLM`
- Set `model_type = "qwen3_5"` in config.

Why: This gives immediate parity baseline; then you incrementally introduce architectural deltas.

## Step 2 — Implement config deltas

In `configuration_qwen3_5.py`:

- Define new/changed hyperparameters with defaults.
- Keep kwargs-compatible constructor for forward compatibility.
- Add validation guards for incompatible combinations (e.g., head dims, rope scaling options).
- Preserve serialization stability (`to_dict`, `from_pretrained` paths).

Tip: Any field that controls tensor shape should be explicitly tested.

## Step 3 — Implement core block deltas

In `modeling_qwen3_5.py`, modify building blocks in this order:

1. Attention projection shapes (`q_proj`, `k_proj`, `v_proj`, `o_proj`).
2. Attention computation path (causal mask, sliding windows, flash/sdpa support).
3. Positional embedding application (RoPE or new mechanism).
4. MLP module and activation/gating.
5. Residual + norm placement.
6. KV cache behavior (`past_key_values` structure).

Then wire:

- Base model output (`Qwen3_5Model`)
- LM head model (`Qwen3_5ForCausalLM`)

Maintain `forward` signatures compatible with Transformers conventions.

## Step 4 — Generation compatibility

Ensure `prepare_inputs_for_generation` and cache updates support:

- Prefill + decode loops.
- `use_cache=True` fast path.
- Variable sequence lengths and attention masks.

Run generation smoke tests with tiny config.

## Step 5 — AutoClass wiring

Update auto mappings so this works:

```python
from transformers import AutoModelForCausalLM, AutoConfig
cfg = AutoConfig.for_model("qwen3_5")
model = AutoModelForCausalLM.from_config(cfg)
```

If this fails, registration/export is incomplete.

## Step 6 — Tokenizer decision

If Qwen3.5 uses same tokenizer/vocab format as Qwen3:

- Reuse existing tokenizer classes (recommended).
- Document compatibility in model docs.

If tokenizer changed:

- Add new tokenizer classes and tests.
- Ensure added tokens and special token defaults serialize correctly.

## Step 7 — Checkpoint conversion script

In `convert_qwen3_5_weights_to_hf.py`:

- Load original checkpoint tensors.
- Map keys from source format -> HF expected keys.
- Handle permutes/transposes for QKV or fused projections.
- Save `config.json`, model weights, tokenizer assets.

Add CLI examples in file docstring.

## Step 8 — Tests (minimum passing bar)

Required tests:

1. **Configuration tests**
   - Roundtrip config save/load.
   - Field validation.
2. **Model shape tests**
   - Forward pass logits shape.
3. **CausalLM tests**
   - Loss path with labels.
4. **Generation tests**
   - Greedy decode with cache.
5. **Save/load parity tests**
   - Outputs before/after `save_pretrained` + `from_pretrained`.
6. **Device/dtype smoke tests**
   - fp32 baseline; bf16/fp16 if infra supports.

Optional but valuable:

- Gradient checkpointing.
- Flash attention path.
- Static cache support.

## Step 9 — Documentation and examples

In model docs page:

- Describe architecture differences from Qwen3 succinctly.
- Provide `from_pretrained` examples.
- Note tokenizer compatibility.
- Mention known limitations (e.g., unsupported attention backend).

## Step 10 — Local validation checklist

Run at minimum:

- `python -m pytest tests/models/qwen3_5/test_configuration_qwen3_5.py -q`
- `python -m pytest tests/models/qwen3_5/test_modeling_qwen3_5.py -q`
- `python -m pytest tests/models/qwen3_5 -q`
- `make fixup` (or project equivalent lint/format)

For full confidence before PR, run broader generation and integration tests.

---

## 4) Suggested development phases

Phase 1 (Day 1): config + minimal model forward pass.  
Phase 2 (Day 2): causal LM head + generation cache + basic tests.  
Phase 3 (Day 3): conversion script + docs + polishing + extended tests.

---

## 5) Common pitfalls (and how to avoid)

1. **Mismatched head dimensions**  
   - Add explicit assertions early in config and attention init.
2. **Cache tensor shape bugs**  
   - Test single-token decode after long prefill.
3. **AutoClass not discoverable**  
   - Verify both mapping files and exported symbols.
4. **Tokenizer mismatch**  
   - Validate BOS/EOS/PAD and chat template behavior.
5. **Silent dtype instability**  
   - Compare logits for fp32 vs bf16 on tiny fixtures.

---

## 6) “Done” criteria

Consider your Qwen3.5 integration complete when all are true:

- `AutoConfig.for_model("qwen3_5")` works.
- `AutoModelForCausalLM.from_config(...)` works.
- Model can generate with `use_cache=True`.
- Save/load roundtrip is numerically stable.
- Conversion script produces loadable checkpoints.
- New model docs are discoverable in docs nav.
- Tests for new model package pass in CI.

---

## 7) Minimal starter task list you can execute now

1. Create `qwen3_5` model package and skeleton files.  
2. Copy Qwen3 config/model baseline into new files.  
3. Rename classes + set `model_type="qwen3_5"`.  
4. Wire auto mappings + exports.  
5. Add baseline tests copied from Qwen3 tests.  
6. Confirm baseline tests pass before introducing architectural changes.  
7. Introduce one architecture delta at a time, with tests after each delta.

This incremental pattern is the fastest way to reach a stable upstream-quality integration.
