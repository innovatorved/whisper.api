FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


RUN --mount=type=secret,id=ALGORITHM,mode=0444,required=true \
	export ALGORITHM='$(cat /run/secrets/ALGORITHM)'
RUN --mount=type=secret,id=SERVER_NAME,mode=0444,required=true \
    export SERVER_NAME='$(cat /run/secrets/SERVER_NAME)'
RUN --mount=type=secret,id=SECRET_KEY,mode=0444,required=true \
    export SECRET_KEY='$(cat /run/secrets/SECRET_KEY)'
RUN --mount=type=secret,id=SERVER_HOST,mode=0444,required=true \
    export SERVER_HOST='$(cat /run/secrets/SERVER_HOST)'
RUN --mount=type=secret,id=POSTGRES_DATABASE_URL,mode=0444,required=true \
    export POSTGRES_DATABASE_URL='$(cat /run/secrets/POSTGRES_DATABASE_URL)'


COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]