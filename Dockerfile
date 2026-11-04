FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src src
COPY dbt dbt
COPY tests tests
CMD ["sh", "-c", "python src/main.py && dbt build --project-dir dbt --profiles-dir dbt"]
