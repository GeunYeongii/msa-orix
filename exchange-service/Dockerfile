FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY server.py /app/server.py

EXPOSE 8080
CMD ["python", "/app/server.py"]
