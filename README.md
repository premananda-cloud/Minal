# NIELIT Imphal Ambassador Assistant

## Run
```
uv run uvicorn app.main:app --reload
```
(run from the `rt/` directory, so `app` resolves as a package)

## Edit data
Edit the JSON files in `app/asset/`, then either restart the server
or `POST /refresh` to reload without restarting.

## Add a new skill later (e.g. web search)
Add `app/skill/web_search.py` with a zero-arg or query-arg function,
then register it in `app/skill/registry.py`'s `SKILLS` list.
Nothing else needs to change.
