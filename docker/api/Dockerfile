# Stage: build
FROM python:3.11-slim AS build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Use the minimal API requirements file
COPY docker/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Stage: final
FROM python:3.11-slim
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1

# copy installed packages from build stage
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# copy only runtime files
COPY app/ ./app/
COPY stock_news.cleaned.json ./stock_news.cleaned.json

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]