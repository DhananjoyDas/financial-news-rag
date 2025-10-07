```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What’s new with Apple this quarter?"}' | jq
```


```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What’s new with Apple this quarter?"}'
``` 

```python
import requests
r = requests.post("http://localhost:8000/chat",
                  json={"question": "What’s up with AAPL in China?"})
print(r.status_code, r.json())
```
