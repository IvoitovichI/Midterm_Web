FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --no-create-home appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appgroup app.py ./
COPY --chown=appuser:appgroup database ./database
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)"
CMD ["sh", "-c", "python app.py --init-db && exec gunicorn --bind 0.0.0.0:8080 --workers 2 --access-logfile - --error-logfile - app:app"]
