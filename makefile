container_name = waypoint-ahandler
compose_file = compose.yml

.PHONY: up down start stop add_migration run_migrations revert_migrations show_current_db_head show_db_heads

up start:
	docker compose -f $(compose_file) up -d --build

down stop:
	docker compose -f $(compose_file) down

show_current_db_head:
	docker exec $(container_name) python -m alembic current

show_db_heads:
	docker exec $(container_name) python -m alembic heads

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
