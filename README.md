# AI Investor Agent

This project is an AI-powered agent that performs fundamental financial analysis on stock tickers.

## Running the Script

To run the analysis directly from the command line, use the following command:

```bash
python -m app.fundamental_agent <TICKER>
```

Replace `<TICKER>` with the stock ticker you want to analyze (e.g., `AAPL`).

## Running the API

This project also provides a FastAPI server to expose the analysis functionality as an API.

To start the server, run the following command:

```bash
uvicorn app.main:app --reload --port 8001
```

The API will be available at `http://127.0.0.1:8001`.

### API Endpoints

*   **`GET /analyze/{ticker}`**: Get a fundamental analysis for a given stock ticker.
    *   **`ticker`** (string, required): The stock ticker symbol.
