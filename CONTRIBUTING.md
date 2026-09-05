# Contributing

Keep changes small and measurable. Add a synthetic scorer fixture before running models on a new task, preserve failed attempts, and separate validation selection from held-out claims. Never commit credentials, restricted answer keys, local run directories or private source materials.

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m wikiskill demo /tmp/wikiskill-contribution-demo
python -m wikiskill results
```

For packaging changes, also build a wheel and install it in a new environment from outside the checkout. Examples and docs must work without a hidden source repository. Model-backed experiments need explicit model, data revision, execution settings and a bounded budget.
