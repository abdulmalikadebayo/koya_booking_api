FROM python:3.13-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies
RUN pip install pipenv --no-cache-dir
COPY Pipfile Pipfile.lock* ./
RUN pipenv install --system --skip-lock

COPY . /app

RUN chmod u+x /app/scripts/entrypoint.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
