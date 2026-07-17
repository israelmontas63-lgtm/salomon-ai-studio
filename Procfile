web: python -m gunicorn app:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 90 --graceful-timeout 20 --max-requests 120 --max-requests-jitter 20
