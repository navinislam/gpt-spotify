.PHONY: api
api:
	uvicorn spot_gpt:app --port 9000  --reload