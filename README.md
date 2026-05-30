# dnd genie

A local RAG chatbot for Dungeons & Dragons basic rules.

The genie uses LM Studio's OpenAI-compatible local server for both chat
completion and embeddings. OctoAI credentials are no longer required.

## Prerequisites

Install Python dependencies:

    python3 -m venv ./venv
    source ./venv/bin/activate
    python -m pip install -r requirements.txt

Install LM Studio, download a chat model and an embedding-capable model, and
start the local server. LM Studio's default HTTP server is:

    http://127.0.0.1:1234

The scripts normalize that to the OpenAI-compatible `/v1` endpoint internally,
so either of these works:

    export LMSTUDIO_BASE_URL=http://127.0.0.1:1234
    export LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1

Export the model identifiers shown by LM Studio:

    export LMSTUDIO_CHAT_MODEL=<chat-model-id>
    export LMSTUDIO_EMBEDDING_MODEL=<embedding-model-id>

`LMSTUDIO_API_KEY` defaults to `lm-studio`, which is enough for the local
server. You can also tune generation with `LMSTUDIO_MAX_TOKENS` and
`LMSTUDIO_TEMPERATURE`.

To confirm that the script can see LM Studio:

    ./scripts/dnd-beyond-basic --check-lmstudio

This checks that both configured models are loaded, that embeddings work, and
that the chat model can return a non-empty response.

If LM Studio reports "No models loaded," start the server and load both models
before running the genie:

    lms server start
    lms load "$LMSTUDIO_CHAT_MODEL" --identifier "$LMSTUDIO_CHAT_MODEL"
    lms load "$LMSTUDIO_EMBEDDING_MODEL" --identifier "$LMSTUDIO_EMBEDDING_MODEL"

You can also load models from the LM Studio Developer page. Use `lms ps` to
confirm which models are currently loaded in memory.

## Running the genie

Run:

    ./scripts/dnd-beyond-basic

Once the script loads and embeds the local data files, it will present a REPL
prompt:

    input>

Try asking it a question, for example:

    input> provide a brief random encounter table for 3 first-level characters. They are in the woods.

Once the party has handled the encounter, ask for treasure:

    input> a party of 3 first-level characters has killed 7 goblins. Provide reasonable treasure the goblins had.

## Tips

* Ask for brief responses.
* Use an embedding model in LM Studio for `LMSTUDIO_EMBEDDING_MODEL`; most chat
  models are not embedding-capable.
* Run `./scripts/dnd-beyond-basic --check-lmstudio` first if indexing fails.
* Press Enter on an empty prompt to continue; use `exit`, `quit`, or Ctrl-D to
  leave the REPL.
* A `Thinking...` line means the question was sent to the local chat model.
* The vector store is built once on startup and reused for each prompt.

## Testing

Run the automated unit and end-to-end tests with:

    python -m unittest discover -s tests

The end-to-end tests start a local mock LM Studio server, run the real
`scripts/dnd-beyond-basic` entry point, and use a tiny temporary D&D rules page
so the suite does not require real LM Studio models.

## Go CLI

The experimental `dndx` Go CLI lives in `cli/`. It can configure local model
endpoints such as LM Studio and Ollama, configure chat and embedding model
names, and chat with the configured local model. See `cli/README.md` for build,
usage, and test commands.

## Easter egg

You can load a URL into the current FAISS index:

    input> load(https://www.dndbeyond.com/sources/basic-rules/spells)
