FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN apt update && apt install -y ffmpeg


RUN --mount=type=secret,id=ALGORITHM,mode=0444,required=true \
    file_contents=$(cat /run/secrets/ALGORITHM) && \
    export ALGORITHM="$file_contents"

RUN --mount=type=secret,id=SERVER_NAME,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SERVER_NAME) && \
    export SERVER_NAME="$file_contents"

RUN --mount=type=secret,id=SECRET_KEY,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SECRET_KEY) && \
    export SECRET_KEY="$file_contents"

RUN --mount=type=secret,id=SERVER_HOST,mode=0444,required=true \
    file_contents=$(cat /run/secrets/SERVER_HOST) && \
    export SERVER_HOST="$file_contents"

RUN --mount=type=secret,id=POSTGRES_DATABASE_URL,mode=0444,required=true \
    file_contents=$(cat /run/secrets/POSTGRES_DATABASE_URL) && \
    export POSTGRES_DATABASE_URL="$file_contents"


RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user . $HOME/app


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]