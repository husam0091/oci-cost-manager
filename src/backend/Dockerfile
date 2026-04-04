FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends gosu dos2unix && rm -rf /var/lib/apt/lists/* \
    && dos2unix /app/docker-entrypoint.sh \
    && addgroup --system app && adduser --system --ingroup app --uid 10001 app \
    && mkdir -p /home/app/.oci /data /exports /tmp /app/portal-ssl \
    && chown -R app:app /app /home/app /data /exports /tmp \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
