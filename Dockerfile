FROM python:3.9

WORKDIR /app

# Upgrade pip and clear cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip cache purge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app .

CMD ["python", "app.py"]
