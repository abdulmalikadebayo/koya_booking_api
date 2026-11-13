FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies exactly as pinned in Pipfile.lock (fails if it is out of date)
RUN pip install pipenv --no-cache-dir
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . /app

RUN chmod u+x /app/scripts/entrypoint.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
