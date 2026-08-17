# Contributing to Knowledge Research Agent

Thanks for your interest in contributing! This guide covers environment setup, workflow and code style conventions.

## Environment Setup

1. Follow the [Quick Start](README.md#-quick-start) to get the backend (Python 3.11 + conda), frontend (Node 18+) and Qdrant running.
2. No API keys are required for development — the project runs in **Mock mode** when keys are empty (see `.env.example`).
3. Download local models (~4.4GB) only when working on retrieval/ranking:

```bash
cd apps/api
python scripts/download_models.py
```

## Branch & Commit Conventions

- Branch from `main` with a descriptive name: `feat/query-router`, `fix/pdf-parser`, `docs/readme`
- Commit messages follow the existing style: `<type>: <description>`, where type is one of `feat` / `fix` / `docs` / `refactor` / `eval` / `chore`
- Keep commits focused — one logical change per commit

## Testing

### CI checks (automatic on push/PR)

| Scope | Command | Where |
|---|---|---|
| Backend syntax + imports | `python -m compileall -q app` | `apps/api` |
| Frontend lint | `npm run lint` | `apps/web` |
| Frontend type check + build | `npm run build` | `apps/web` |

### Manual smoke tests (local, require models / services)

```bash
cd apps/api
python scripts/smoke_test.py           # full pipeline smoke
python scripts/router_test.py          # query router
python scripts/kb_rag_test.py          # knowledge-base RAG
python scripts/multi_source_test.py    # multi-source retrieval
```

### Evaluation

```bash
cd apps/api
python eval/scripts/eval_dataset_gen.py 40
python eval/scripts/eval_run.py --gen 10 --save-baseline
```

## Code Style

- **Backend**: follow the existing module structure (`agents` / `rag` / `llm` / `services` / `api` / `models`); config goes to `.env.example`; no secrets in code
- **Frontend**: components go to `src/components/<group>/`, shared state to `src/features/`; run `npm run lint` before committing
- Keep the graph logic in `app/agents/` — new retrieval steps must update the evaluation suite accordingly

## Pull Requests

1. Run the CI checks above locally before pushing
2. Fill in the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
3. Update docs (README / docs/) if behavior changes

## License

By contributing you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
