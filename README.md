# calldesnac

A minimal, standalone SNAC-to-audio decoder designed to work with LLM-generated speech tokens (specifically for models like Orpheus-TTS).

## Features

- **Streaming Support:** Decodes tokens as they arrive from the LLM API.
- **Frame Orchestration:** Automatically handles the 7-token frame structure used by SNAC.
- **Token Synchronization:** Robustly handles token skips or repeats to maintain audio alignment.
- **Dockerized:** Includes a `Dockerfile` for easy, environment-isolated deployment.
- **Podman Wrapper:** A helper script (`tool/podman-run.sh`) that simplifies running the container and mounting output directories.

## Installation

### Local (Python)

Ensure you have Python 3.10+ and the required dependencies:

```bash
pip install torch snac requests numpy
```

### Docker / Podman

Build the image:

```bash
podman build -t calldesnac .
```

## Usage

### Basic Usage

```bash
python calldesnac.py --prompt "Hello, this is a test of the SNAC decoder." --output output.wav
```

### Using the Podman Wrapper

The wrapper automatically handles volume mounting for the `--output` file:

```bash
./tool/podman-run.sh calldesnac --prompt "Deep in the digital dreamscape, a sprite named Paprika is hard at work." --output paprika.wav
```

### Arguments

- `--openai-api-url`: OpenAI-compatible API base URL (defaults to `http://127.0.0.1:11434/v1`).
- `--model`: Model name for the API (defaults to `orpheus-tts`).
- `--voice`: Voice name prefix (defaults to `tara`).
- `--output`: Output WAV file (defaults to stdout).
- `--snac-model`: SNAC model on Hugging Face (defaults to `hubertsiuzdak/snac_24khz`).
- `--quiet`: Minimize log output.
- `--debug`: Print token debugging information to stderr.
