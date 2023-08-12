FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY ./app /app/app

COPY ./requirements.txt /app

RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]