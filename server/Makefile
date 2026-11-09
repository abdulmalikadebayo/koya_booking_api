export PIPENV_VERBOSITY=-1

.PHONY: run
run:
	pipenv run python src/manage.py runserver 0.0.0.0:8001

# Tests run against a local Postgres in Docker (fast); the app itself uses .env (Supabase)
.PHONY: db
db:
	docker start koya-pg || docker run -d --name koya-pg -e POSTGRES_PASSWORD=pg -e POSTGRES_DB=koya -p 5433:5432 postgres:16

.PHONY: test
test:
	PIPENV_DONT_LOAD_ENV=1 DB_HOST=localhost DB_PORT=5433 DB_USER=postgres DB_PASSWORD=pg DB_NAME=koya pipenv run pytest

.PHONY: shell
shell:
	pipenv run python src/manage.py shell

.PHONY: migrate
migrate:
	pipenv run python src/manage.py makemigrations
	pipenv run python src/manage.py migrate

.PHONY: clean
clean:
	rm -rf ./src/db.sqlite3
	find ./src -name __pycache__ -type d -prune -exec rm -rf {} +

.PHONY: collectstatic
collectstatic:
	pipenv run python src/manage.py collectstatic --no-input

.PHONY: run/gunicorn
run/gunicorn:
	PYTHONPATH=src gunicorn config.wsgi:application --bind 0.0.0.0:8000

.PHONY: docker/build
docker/build:
	docker build -f ./Dockerfile -t koya-booking-api:latest .

.PHONY: tidy
tidy:
	pipenv run autoflake --in-place --remove-all-unused-imports -r --exclude migrations ./src
	pipenv run isort --atomic ./src/
	pipenv run black ./src/ --exclude=migrations
