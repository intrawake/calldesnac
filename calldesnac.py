import argparse
import requests
import json
import torch
import numpy as np
import wave
import sys
import io
from snac import SNAC


def parse_raw_id(token_string):
    token_string = token_string.strip()
    prefix = "<custom_token_"
    last_token_start = token_string.rfind(prefix)
    if last_token_start == -1:
        return None
    last_token = token_string[last_token_start:]
    if last_token.startswith(prefix) and last_token.endswith(">"):
        try:
            # Extract raw ID (e.g. 10 for <custom_token_10>)
            # Relative to the base offset of 10
            return int(last_token[len(prefix) : -1]) - 10
        except ValueError:
            return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Call LLM for SNAC tokens and decode to audio")
    parser.add_argument(
        "--openai-api-url", default="http://127.0.0.1:11436/v1", help="OpenAI-compatible API base URL"
    )
    parser.add_argument("--model", default="orpheus-tts", help="Model name for API")
    parser.add_argument("--prompt", help="Text to synthesize (defaults to stdin)")
    parser.add_argument("--voice", default="tara", help="Voice name prefix")
    parser.add_argument("--output", help="Output WAV file (defaults to stdout)")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--repetition-penalty", type=float, default=1.1)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--snac-model", default="hubertsiuzdak/snac_24khz", help="SNAC model on HF")
    parser.add_argument("--quiet", action="store_true", help="Minimize log output")
    parser.add_argument("--debug", action="store_true", help="Print token debugging to stderr")

    args = parser.parse_args()

    api_url = args.openai_api_url.rstrip("/")
    if api_url.endswith("/v1"):
        api_url = api_url + "/completions"

    prompt = args.prompt
    if prompt is None or prompt == "-":
        prompt = sys.stdin.read().strip()

    if not prompt:
        print("Error: No prompt provided", file=sys.stderr)
        sys.exit(1)

    is_stdout = args.output is None or args.output == "-"
    log_file = sys.stderr

    # Format prompt
    formatted_prompt = f"<|audio|>{args.voice}: {prompt}<|eot_id|>"

    payload = {
        "model": args.model,
        "prompt": formatted_prompt,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "repeat_penalty": args.repetition_penalty,
        "stream": True,
    }

    if not args.quiet:
        print(f"Calling API: {api_url} with model {args.model}", file=log_file)

    response = requests.post(api_url, json=payload, stream=True)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}", file=log_file)
        sys.exit(1)

    raw_ids = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    text = data["choices"][0].get("text", "")
                    if text:
                        for chunk in text.split(">"):
                            if not chunk:
                                continue
                            raw_id = parse_raw_id(chunk + ">")
                            if raw_id is not None:
                                raw_ids.append(raw_id)
                except Exception as e:
                    if not args.quiet:
                        print(f"JSON error: {e}", file=log_file)

    if not raw_ids:
        if not args.quiet:
            print("No tokens generated.", file=log_file)
        sys.exit(1)

    # SNAC Codebook buckets
    c0, c1, c2 = [], [], []

    # Orchestrate frames (7 tokens each)
    current_frame = [0] * 7
    last_p = -1
    frame_count = 0

    for v in raw_ids:
        p = v // 4096
        val = v % 4096

        if p < 0 or p > 6:
            if args.debug:
                print(f"Warning: Ignored out-of-range token {v}", file=log_file)
            continue

        # If we see a position we have already filled or skipped back to,
        # it means a new frame has started.
        if p <= last_p:
            c0.append(current_frame[0])
            c1.extend([current_frame[1], current_frame[4]])
            c2.extend([current_frame[2], current_frame[3], current_frame[5], current_frame[6]])
            current_frame = [0] * 7
            frame_count += 1

        current_frame[p] = val
        last_p = p

    # Ship final frame
    if any(x != 0 for x in current_frame):
        c0.append(current_frame[0])
        c1.extend([current_frame[1], current_frame[4]])
        c2.extend([current_frame[2], current_frame[3], current_frame[5], current_frame[6]])
        frame_count += 1

    if not args.quiet:
        print(f"Decoded {len(raw_ids)} tokens into {frame_count} frames.", file=log_file)

    # Force logs to stderr for the heavy loading phase
    old_stdout = sys.stdout
    if is_stdout:
        sys.stdout = sys.stderr

    try:
        model = SNAC.from_pretrained(args.snac_model).eval()

        codes = [
            torch.tensor(c0).unsqueeze(0).to(torch.long),
            torch.tensor(c1).unsqueeze(0).to(torch.long),
            torch.tensor(c2).unsqueeze(0).to(torch.long),
        ]

        with torch.inference_mode():
            audio_hat = model.decode(codes)

        audio_np = audio_hat.squeeze().cpu().numpy()
        audio_int16 = (audio_np * 32767).astype(np.int16)

        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, "wb") as f_wav:
                f_wav.setnchannels(1)
                f_wav.setsampwidth(2)
                f_wav.setframerate(24000)
                f_wav.writeframes(audio_int16.tobytes())
            wav_bytes = wav_buffer.getvalue()
    finally:
        sys.stdout = old_stdout

    if is_stdout:
        sys.stdout.buffer.write(wav_bytes)
        sys.stdout.buffer.flush()
    else:
        with open(args.output, "wb") as f_out:
            f_out.write(wav_bytes)
        if not args.quiet:
            print(f"Saved to {args.output}", file=log_file)


if __name__ == "__main__":
    main()
