FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Use a minimal requirements file for the UI to avoid installing server-only deps
COPY docker/ui/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the UI needs (keep layer small)
COPY ui/ ./ui/
COPY app/ ./app/
COPY stock_news.cleaned.json ./stock_news.cleaned.json

# Gradio default port 7860
CMD ["python", "ui/app.py"]