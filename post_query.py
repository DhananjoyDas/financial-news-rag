"""Example script to query the FastAPI server."""
import requests

r = requests.post("http://localhost:8000/chat",
                  json={"question": "What’s up with AAPL in China?"})
print(r.status_code, r.json())