## Paper Assistant

### Purpose

The main goal here is to just have a better way of organizing papers for readers of [Daily Papers](https://huggingface.co/papers).

### Setup

In order to run this project, you'd need to set up [Neo4j Desktop](https://neo4j.com/download/). You should then create a DBMS and a database inside it and set it as `DATABASE` in the `.env`.

You'd also need to add your [Google AI Studio](https://aistudio.google.com/) for access to [Gemini 2.0 Flash](https://aistudio.google.com/prompts/new_chat?model=gemini-2.0-flash) used in the project and set the `GEMINI_API_KEY` in the `.env`.

A few packages are being used such as [docling](https://github.com/DS4SD/docling) which should be installed via the `requirements.txt`.

The pdf for the papers processed are stored in the `papers` folder, and the corresponding markdowns are stored in the `markdown` folder. A few of these have been added for being a starting point.

### Usage

There are 2 user-facing scripts -
1. `store.py`: for processing today's papers and storing in the db.
2. `retrieve.py`: for interacting with the db to retrieve data.

In order to just get started, you should populate the `DATABASE` and `GEMINI_API_KEY` in the `.env` and then just run `store.py --existing` so that the existing papers get added to the database (instead of the current daily papers).

The data should now be available in your database. Run `retrieve.py` to explore, pass `"exit"` or `"q"` to end the loop.

### Images

Here's what the graph looks like for the existing papers,

![Graph](graph.png)

with the clusters in green, the concepts in blue and the papers in orange.
