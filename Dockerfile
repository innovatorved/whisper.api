FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


RUN --mount=type=secret,id=ALGORITHM,mode=0444,required=true \
    file_contents=$(cat /run/secrets/ALGORITHM) && \
    echo "ALGORITHM: $file_contents" && \
    export ALGORITHM="$file_contents"

RUN --mount=type=secret,id=SERVER_NAME,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SERVER_NAME) && \
    echo "SERVER_NAME: $file_contents" && \
    export SERVER_NAME="$file_contents"

RUN --mount=type=secret,id=SECRET_KEY,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SECRET_KEY) && \
    echo "SECRET_KEY: $file_contents" && \
    export SECRET_KEY="$file_contents"

RUN --mount=type=secret,id=SERVER_HOST,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SERVER_HOST) && \
    echo "SERVER_HOST: $file_contents" && \
    export SERVER_HOST="$file_contents"

RUN --mount=type=secret,id=POSTGRES_DATABASE_URL,mode=0444,required=true \
    file_contents=$(cat /run/secrets/POSTGRES_DATABASE_URL) && \
    echo "POSTGRES_DATABASE_URL: $file_contents" && \
    export POSTGRES_DATABASE_URL="$file_contents"


COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]