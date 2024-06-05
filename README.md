
# dnd genie

## Prerequisites

Create and export into your environment the following API keys:

* `OCTOAI_API_TOKEN` via https://octoai.cloud
* `OPENAI_API_KEY` via https://platform.openai.com/api-keys

You need `python3` and `venv`.

    python3 -m venv ./venv
    source ./venv/bin/activate
    python -m pip install -q langchain-openai langchain langchain-text-splitters lxml octoai-sdk langchain-community faiss-cpu tiktoken

## Starting things up

You'll need two sacrificial terminals.

In the first, run

    ./standalone_embed.sh start

Once that starts up, in the second one, run

    python3 -m http.server 8000

## Running the genie

In a third terminal, run:

    ./scripts/dnd-beyond-basic

Once the script loads all the data files, it'll present you with a REPL prompt:

    input>

Try asking it a question, eg:

    input> provide a brief random encounter table for 3 first-level characters. They are in the woods.

Once you've decided your murderhobos have vanquished the wolves (or whatever), ask for treasure!

    input> a party of 3 first-level characters has killed 7 goblins. Provide reasonable treasure the goblins had.

# Tips

* Ask for brief responses.

# Easter-egg

You can load any random URL in:

    input> load(https://www.dndbeyond.com/sources/basic-rules/spells)
