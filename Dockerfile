FROM python:3.10-bullseye as builder

RUN pip install poetry==1.8.3

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY . .

RUN --mount=type=cache,target=$POETRY_CACHE_DIR \
    poetry export -f requirements.txt -o requirements.txt && \
    poetry build -f wheel


FROM python:3.10-bullseye

COPY --from=builder /app/requirements.txt .
COPY --from=builder /app/dist/bidsificator-*.whl .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn && \
    pip install bidsificator-*.whl

CMD [ "gunicorn", "-w", "4", "bidsificator.api:app" ]
