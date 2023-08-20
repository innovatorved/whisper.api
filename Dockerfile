FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ENV ALGORITHM=$(cat /run/secrets/ALGORITHM)
ENV SERVER_NAME=$(cat /run/secrets/SERVER_NAME)
ENV SECRET_KEY=$(cat /run/secrets/SECRET_KEY)
ENV SERVER_HOST=$(cat /run/secrets/SERVER_HOST)
ENV POSTGRES_SERVER=$(cat /run/secrets/POSTGRES_SERVER)
ENV POSTGRES_USER=$(cat /run/secrets/POSTGRES_USER)
ENV POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
ENV POSTGRES_DB=$(cat /run/secrets/POSTGRES_DB)
ENV POSTGRES_DATABASE_URL=$(cat /run/secrets/POSTGRES_DATABASE_URL)

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]