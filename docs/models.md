# Models

The Whisper API uses model files (`.bin`) that take the `ggml-` format compatible with `whisper.cpp`.

## Model Directory

All `.bin` files should be located in the `models/` directory in the project root.

### Example File Path:
```text
./models/ggml-model-whisper-tiny.en-q5_1.bin
```

## Adding New Models

You can download official `ggml-` models from the [whisper.cpp Hugging Face repository](https://huggingface.co/ggerganov/whisper.cpp/tree/main).

### Loading a New Model:
1.  Download the `.bin` file.
2.  Move it to the `models/` folder.
3.  Restart the API server.
4.  Verify availability via: `GET /v1/models`.

### Supported Quantization Formats:
- **f32** (Full precision, slowest)
- **f16** (Half precision)
- **q4_0 / q4_1** (4-bit quantization, fastest)
- **q5_0 / q5_1** (5-bit quantization, recommended)
- **q8_0** (8-bit quantization)

*Note: For optimal performance and memory usage, `q5_1` is generally recommended for production CPU workloads.*
