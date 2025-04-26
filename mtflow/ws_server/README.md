# ws_server

## Run WS Server
```bash
# preferred
litestar run --port 8002 --reload --debug --web-concurrency 1
or
uvicorn app:app --port 8002 --reload
or
python app.py
```

## API Doc:
```http://127.0.0.1:8002/schema```