# William & Mary Farmers Market Dashboard

This repository now preserves two versions:

- `bestversionmarket.py`: the preferred full demo local app with the original dashboard layout and operational logic.
- `streamlit_app.py`: the shareable Streamlit app target, updated to preserve the core bestversionmarket dashboard experience.

## Launching the app locally

Run:

```bash
python3 bestversionmarket.py --serve --port 8501
```

Then open:

```text
http://127.0.0.1:8501
```

If you want the shareable Streamlit version locally, run:

```bash
streamlit run streamlit_app.py
```

Or visit the hosted Streamlit demo:

```text
https://marketdemo.streamlit.app/
```

## Notes

- `bestversionmarket.py` is the full demo version with the original dashboard layout and operational logic. It is a local HTTP server app, not a Streamlit Cloud entrypoint.
- `streamlit_app.py` is the Streamlit app file and should be used as the deployment target for Streamlit Cloud.
- The devcontainer is configured to start the full demo automatically on port `8501`.

## Streamlit Cloud deployment

If you deploy this repo on Streamlit Cloud, set the app file to `streamlit_app.py` and use the `main` branch. `requirements.txt` already includes `streamlit`.
