FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN mkdir -p /app/data

ENV DATABASE_PATH=/app/data/drafts.db
ENV LOG_DIR=/app/logs

CMD ["python", "./start_bot.py"]