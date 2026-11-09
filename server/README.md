# Koya Booking API - Server

## Setup

1. Install prerequisites

MacOS

```bash
brew install pipenv
```

Windows

```bash
pip install pipenv
```

2. Install dependencies

```bash
pipenv install --dev
```

3. Configure environment

```bash
cp .env.template .env
```

Fill in the values in `.env`.

4. Run

```bash
make migrate
make run
```
