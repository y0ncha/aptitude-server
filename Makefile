UV ?= UV_CACHE_DIR=.uv-cache uv
DOCKER_IMAGE ?= y0ncha/aptitude-server
DOCKER_TAG ?= latest
DOCKER_IMAGE_REF := $(DOCKER_IMAGE):$(DOCKER_TAG)
DOCKER_PLATFORMS ?= linux/amd64,linux/arm64

.PHONY: run debug test lint format typecheck migrate-up migrate-down db-up db-down docker-migrate observability-up observability-down docker-smoke docker-build docker-push docker-build-push

run:
	@printf "\033[1;36m==>\033[0m \033[1mStarting FastAPI dev server\033[0m\n"
	@printf "\033[0;36m    API:\033[0m  http://127.0.0.1:8000\n"
	@printf "\033[0;36m   Docs:\033[0m  http://127.0.0.1:8000/docs\n"
	@printf "\033[0;36m   Stop:\033[0m  Ctrl+C\n\n"
	@UVICORN_RELOAD=true $(UV) run python -m app.main

debug:
	@printf "\033[1;36m==>\033[0m \033[1mStarting FastAPI dev server in debug mode\033[0m\n"
	@printf "\033[0;36m    API:\033[0m  http://127.0.0.1:8000\n"
	@printf "\033[0;36m   Docs:\033[0m  http://127.0.0.1:8000/docs\n"
	@printf "\033[0;36m  Level:\033[0m  DEBUG\n"
	@printf "\033[0;36m   Stop:\033[0m  Ctrl+C\n\n"
	@LOG_LEVEL=DEBUG UVICORN_RELOAD=false $(UV) run python -m app.main

test:
	$(UV) run --extra dev pytest

lint:
	$(UV) run --extra dev ruff check .

format:
	$(UV) run --extra dev ruff format .

typecheck:
	$(UV) run --extra dev mypy app

migrate-up:
	$(UV) run alembic upgrade head

migrate-down:
	$(UV) run alembic downgrade -1

db-up:
	docker compose up -d db

db-down:
	docker compose down -v

docker-migrate:
	docker compose --profile observability run --rm migrate

observability-up:
	docker compose --profile observability up -d db
	docker compose --profile observability run --rm migrate
	docker compose --profile observability up -d server prometheus grafana

observability-down:
	docker compose --profile observability down -v

docker-smoke:
	docker compose --profile observability up -d db
	docker compose --profile observability run --rm migrate
	docker compose --profile observability up -d server
	@for attempt in $$(seq 1 30); do \
		if curl --silent --fail http://127.0.0.1:8000/healthz >/dev/null 2>&1; then \
			break; \
		fi; \
		sleep 1; \
	done
	curl --fail http://127.0.0.1:8000/healthz
	curl --fail http://127.0.0.1:8000/readyz
	curl --fail http://127.0.0.1:8000/metrics
	docker compose --profile observability down -v

docker-build:
	docker buildx build --load -t $(DOCKER_IMAGE_REF) .

docker-push:
	docker buildx build --platform $(DOCKER_PLATFORMS) --push -t $(DOCKER_IMAGE_REF) .

docker-build-push: docker-push
