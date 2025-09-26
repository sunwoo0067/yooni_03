# Repository Guidelines

## Project Structure & Module Organization
- `backend/app` hosts FastAPI endpoints, background tasks, and shared logic in `app/core` and `app/services`.
- Domain tests live in `backend/tests` mirroring module layout; expect fixtures under `backend/tests/conftest.py`.
- Frontend React code resides in `frontend/src` with UI in `components/`, state in `store/`, and end-to-end specs under `frontend/e2e`.
- Support assets: container configs in `docker/`, environment presets in `config/`, automation scripts in `scripts/`, and reference docs in `docs/` and `logs/`.

## Build, Test, and Development Commands
- `make dev-start` boots the docker-compose dev stack; pair with `make dev-logs` for live service output and `make dev-stop` to shut it down cleanly.
- `make test` runs linting plus the full pytest suite; scope to fast feedback via `make test-unit` or `cd backend && python -m pytest tests/unit -k name`.
- Frontend loops rely on `npm run dev` for hot reloads, `npm run build` for production bundles, and `npm run test` for Jest suites; run `cd frontend/e2e && npx playwright test` for browser coverage.

## Coding Style & Naming Conventions
- Format Python with Black (88 columns) and isort before committing; modules stay snake_case and typed public APIs.
- React/TypeScript uses 2-space indentation, PascalCase components (for example `SupplierTable.tsx`), camelCase hooks, and ESLint must pass.
- Name services descriptively; `supplier_sync_service.py` beats abbreviations, and capture complex flows with concise docstrings.

## Testing Guidelines
- Pytest markers `unit`, `integration`, and `slow` gate execution; use VCR or feature flags to avoid live API hits.
- Match coverage baselines tracked in `coverage.json`; add regression tests whenever touching `backend/app/services/` or orchestration flows.
- Store generated reports in `logs/` or `frontend/test-results` and prune anything older than a sprint.

## Commit & Pull Request Guidelines
- Follow Conventional Commits via `cz commit` (`feat:`, `fix:`, `chore:`); keep subject lines imperative and under 72 characters.
- PRs should link issues, summarize scope, list validation commands, and attach UI screenshots when frontend changes apply.
- Flag skipped tests or pending migrations in the description so reviewers can plan follow-up work.

## Security & Configuration Tips
- Start from `.env.example` or `.env.development`, keep secrets local, and never commit populated `.env` files.
- After database schema changes, run `make db-migrate` and rotate service logs into `logs/` with the 14-day retention rule.
- Review `security_reports/` and `SECURITY_GUIDELINES.md` quarterly; raise any credential exposure immediately in the security channel.
