# dndx CLI

`dndx` is a small Go command line companion for DnDGenie. It stores local model
endpoint settings, configures chat/embedding model names, and can chat with a
local model server.

## Build

From this directory:

    go build -o dndx .

Then run:

    ./dndx help

## Configuration

Configuration is written to your user config directory:

    ~/.config/dndx/config.json

Set `DNDX_CONFIG` to use a different file, which is useful for tests and
automation.

## Commands

Configure LM Studio:

    ./dndx /connect lmstudio --url http://127.0.0.1:1234

The LM Studio endpoint is normalized to the OpenAI-compatible `/v1` endpoint, so
the saved value becomes:

    http://127.0.0.1:1234/v1

Configure Ollama:

    ./dndx /connect ollama --url http://127.0.0.1:11434

If `--url` is omitted, `dndx` uses these defaults:

    lmstudio -> http://127.0.0.1:1234/v1
    ollama   -> http://127.0.0.1:11434

Configure models:

    ./dndx models --chat glm-5.0 --embedding text-embedding-nomic-embed-text-v1.5

Show current model and endpoint settings:

    ./dndx models
    ./dndx status

Ask a one-off question:

    ./dndx chat provide a brief random encounter table for 3 first-level characters. They are in the woods.

## Interactive Mode

Run with no arguments:

    ./dndx

Then type plain text at the `_` prompt to chat:

    dndx _ provide a brief random encounter table for 3 first-level characters. They are in the woods.

Slash commands are handled locally:

    dndx _ /connect lmstudio --url http://127.0.0.1:1234
    dndx _ models --chat glm-5.0 --embedding text-embedding-nomic-embed-text-v1.5
    dndx _ status
    dndx _ /quit

LM Studio uses its OpenAI-compatible `/v1/chat/completions` endpoint. Ollama
uses its native `/api/chat` endpoint.

## Tests

Run:

    go test ./...

The tests use only the Go standard library and write config files to temporary
directories.
