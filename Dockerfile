FROM python:3.11-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy backend source
COPY backend ./backend

# environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cloud Run port
EXPOSE 8080

# start server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]