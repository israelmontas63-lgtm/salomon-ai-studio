web: python -m gunicorn app:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120 --graceful-timeout 30 --max-requests 200 --max-requests-jitter 40
