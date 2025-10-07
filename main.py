"""Entrypoint for running the FastAPI app with Uvicorn."""

import uvicorn

def main():
    """The main function."""
    # lets you run the app with `python main.py`
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(
        "app.main:app", host="127.0.0.1", port=8000, log_level="debug", reload=True
    )

if __name__ == "__main__":
    main()
