container_name = waypoint-gateway
compose_file = compose.yml

.PHONY: up down start stop test_ci_workflow add_migration run_migrations revert_migrations show_current_db_head show_db_heads

up start:
	docker compose -f $(compose_file) up -d --build

down stop:
	docker compose -f $(compose_file) down

show_current_db_head:
	docker exec $(container_name) python -m alembic current

show_db_heads:
	docker exec $(container_name) python -m alembic heads

test_ci_workflow:
	@command -v act > /dev/null 2>&1 || (echo "Error: 'act' is not installed or not in PATH. See https://github.com/nektos/act" && exit 1)
	@if [ -z "$(GH_TOKEN)" ]; then \
		echo "Error: Please provide a github token. Usage: make test_ci_workflow GH_TOKEN=<your-github-pat>"; \
		exit 1; \
	fi
	@if [ -z "$(TEST_PYPI_TOKEN)" ]; then \
		echo "Error: Please provide a test pypi token. Usage: make test_ci_workflow TEST_PYPI_TOKEN=<your-test-pypi-token>"; \
		exit 1; \
	fi
	@echo "Running CI workflow..."
	act workflow_dispatch --input version=0.2.0 --secret GH_TOKEN=$(GH_TOKEN) --secret TEST_PYPI_TOKEN=$(TEST_PYPI_TOKEN) --artifact-server-path /tmp/act-artifacts

add_migration:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: Please provide a message. Usage: make add_migration MSG='your message'"; \
		exit 1; \
	fi
	@if [ -z "$(AUTO)" ] || [ "$(AUTO)" = "1" ]; then \
		docker exec $(container_name) python -m alembic revision --autogenerate -m "$(MSG)"; \
	else \
		docker exec $(container_name) python -m alembic revision -m "$(MSG)"; \
	fi

run_migrations:
	docker exec $(container_name) python -m alembic upgrade head

revert_migrations:
	docker exec $(container_name) python -m alembic downgrade -1
