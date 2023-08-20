FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY .env /code

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

