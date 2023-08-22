---
title: whisper.api
emoji: 😶‍🌫️
colorFrom: purple
colorTo: gray
sdk: docker
app_file: Dockerfile
app_port: 7860
---

# Whisper API - Speech to Text Transcription

Description: This open source project provides a self-hostable API for speech to text transcription using a finetuned Whisper ASR model. The API allows you to easily convert audio files to text through HTTP requests. Ideal for adding speech recognition capabilities to your applications.

Key features:

- Uses a finetuned Whisper model for accurate speech recognition
- Simple HTTP API for audio file transcription
- User level access with API keys for managing usage
- Self-hostable code for your own speech transcription service
- Quantized model optimization for fast and efficient inference
- Open source implementation for customization and transparency

This repository contains code to deploy the API server along with finetuning and quantizing models. Check out the documentation for getting started!

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
