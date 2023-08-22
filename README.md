---
title: whisper.api
emoji: 😶‍🌫️
colorFrom: purple
colorTo: gray
sdk: docker
app_file: Dockerfile
app_port: 7860
---

# whisper.api

This project provides an API with user level access support to transcribe speech to text using a finetuned and processed Whisper ASR model.

## Installation

To install the necessary dependencies, run the following command:

```bash
# Install ffmpeg for Audio Processing
sudo apt install ffmpeg

# Install Python Package
pip install -r requirements.txt
```

# Running the Project
To run the project, use the following command:

```bash
uvicorn app.main:app --reload
```

## Get Your token
To get your token, use the following command:

```bash
curl -X 'POST' \
  'https://innovatorved-whisper-api.hf.space/api/v1/users/get_token' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "example@domain.com",
  "password": "password"
}'
```

## Example to Transcribe a File
To upload a file and transcribe it, use the following command:
Note: The token is a dummy token and will not work. Please use the token provided by the admin.

Here are the available models:
- tiny.en
- tiny.en.q5
- base.en.q5

```bash

# Modify the token and audioFilePath
curl -X 'POST' \
  'http://localhost:8000/api/v1/transcribe/?model=tiny.en.q5' \
  -H 'accept: application/json' \
  -H 'Authentication: e9b7658aa93342c492fa64153849c68b8md9uBmaqCwKq4VcgkuBD0G54FmsE8JT' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@audioFilePath.wav;type=audio/wav'
```

## License

[MIT](https://choosealicense.com/licenses/mit/)


## Reference & Credits

- [https://github.com/openai/whisper](https://github.com/openai/whisper)
- [https://openai.com/blog/whisper/](https://openai.com/blog/whisper/)
- [https://github.com/ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp)

  
## Authors

- [Ved Gupta](https://www.github.com/innovatorved)

  
## 🚀 About Me
I'm a Developer i will feel the code then write.

  
## Support

For support, email vedgupta@protonmail.com
