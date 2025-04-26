FROM python:3.10

# not write .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Python output is sent straight to the terminal (i.e., it's unbuffered) 
ENV PYTHONUNBUFFERED 1

WORKDIR /ws_server

COPY pyproject.toml poetry.lock* /ws_server/

RUN pip install poetry

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . /ws_server

CMD ["litestar", "run", "--host", "0.0.0.0", "--port", "${WS_SERVER_PORT}"]
