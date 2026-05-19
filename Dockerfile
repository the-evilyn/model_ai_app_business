# Image Python
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_api_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
