# Dataset setup

Large datasets are not bundled. Download through the upstream projects, comply with their access and licensing terms, and keep local copies outside version control. Packaged splits contain IDs/metadata, not answers. A custom `--split-dir` must provide `train.json` and `val.json` with unique `uid` entries and no overlap.

| CLI domain | Data argument | Upstream / notes |
|---|---|---|
| `officeqa` / `officeqa-retrieval` | `--csv` and `--corpus` | [Databricks OfficeQA](https://github.com/databricks/officeqa), [gated HF dataset](https://huggingface.co/datasets/databricks/officeqa). CSV `officeqa_full.csv`; parsed Treasury text corpus. Data CC-BY-SA 4.0; scorer Apache-2.0. |
| `spreadsheet` | `--data data/spreadsheet` | [SpreadsheetBench](https://github.com/RUCKBReasoning/SpreadsheetBench). Directory containing task definitions and source/reference workbooks. Install `.[spreadsheet]`. |
| `livemath` | `--data data/livemath` | [LiveMathematicianBench](https://github.com/LinyangHe/LiveMathematicianBench), monthly `qa_*_final.json`. New default is the revised `id_split-v2`; bundled historical results use v1. |
| `sealqa` | `--data data/sealqa/seal-0.parquet` | [SealQA](https://huggingface.co/datasets/vtllms/sealqa). Install `.[datasets]`. This adapter provides packaged source URLs, not the paper's live Google search backend. |
| `alfworld` | `--data` pointing at `json_2.1.1` | [ALFWorld](https://github.com/alfworld/alfworld). Install its environment separately and set `ALFWORLD_PYTHON` to that Python executable. Packaged game IDs are relative to the data root. |

For OfficeQA, `officeqa` copies cited documents under `docs/`; `officeqa-retrieval` exposes the full supplied corpus under `corpus/`, without listing gold source filenames in the prompt. Supply the same parsed corpus when comparing skill/no-skill within a mode. The helper `wikiskill.officeqa.fetch.fetch_missing` downloads missing required bulletins using the HF CLI and a pinned revision, after the CSV is available; it is not a general full-corpus downloader.

Never put the restricted gold CSV into an inference workspace. The operator-side loader may read it for scoring, while model workspaces receive only their task inputs. Freeze the dataset revision and hashes before a serious experiment; changing inputs midway requires a new campaign.

## Example: spreadsheet evolution

```bash
python -m pip install -e '.[spreadsheet]'
wikiskill init runs/sheets \
  --domain spreadsheet --model gpt-5.5 --optimizer-model gpt-5.6-sol \
  --data data/spreadsheet --iterations 4
wikiskill evolve runs/sheets
```

The source spreadsheet experiments used 278 held-out tasks after excluding two defective instances. The small validation split cannot establish generalization by itself. No formal test is launched by this example.
