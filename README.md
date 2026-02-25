# Local Stock Analyst MCP (Python)

MCP server for stock intelligence workflows with:

- Domain-split tool registry (`market`, `stocks`, `technical`, `fundamental`, `options`, `risk`, `news`, `screener`, `portfolio`)
- Multi-provider adapters with fallback routing
- In-memory TTL caching and per-provider rate-limit guards
- `stdio` and Render-compatible HTTP transport modes

## MCP Prompts and Resources

The server now exposes MCP prompts/resources in addition to tools.

- Prompt: `portfolio_analysis`
  - Arguments: required `portfolio` (string)
  - Purpose: builds a structured institutional-grade portfolio analysis instruction
- Resource: `portfolio://current`
  - MIME type: `application/json`
  - Purpose: returns the latest successful portfolio workflow snapshot payload
  - Note: run a portfolio workflow first (for example `analyze_portfolio_excel`) to populate it

### Prompt examples

- List prompts (`prompts/list`) now includes `portfolio_analysis`.
- Get prompt (`prompts/get`) request example:

```json
{
  "name": "portfolio_analysis",
  "arguments": {
    "portfolio": "US Core"
  }
}
```

- Example behavior:
  - Unknown prompt name -> invalid-params style error (`Unknown prompt: ...`)
  - Missing required argument -> invalid-params style error (`Missing required arguments: ...`)

### Resource examples

- List resources (`resources/list`) now includes `portfolio://current`.
- List resource templates (`resources/templates/list`) now includes `portfolio://snapshot/{report_type}`.
- Read resource (`resources/read`) request example:

```json
{
  "uri": "portfolio://current"
}
```

- Example successful response content is JSON with:
  - `uri`, `report_type`, `source_file_path`, `payload`
- Error behavior:
  - Invalid URI / unknown resource -> not found style error
  - No snapshot yet -> safe not-found message without sensitive token/key leakage
  - Resource not found maps to JSON-RPC code `-32002`

### Capability and subscription behavior

- `prompts` capability advertises `listChanged: true`.
- `resources` capability advertises:
  - `subscribe: true`
  - `listChanged: true`
- Resource subscriptions are supported via `resources/subscribe` and `resources/unsubscribe`.
- Subscribed clients receive `notifications/resources/updated` when `portfolio://current` is refreshed by portfolio workflows.

## Provider Support

- Finnhub
- Alpha Vantage
- Yahoo Finance
- Financial Modeling Prep (FMP)
- TwelveData
- MarketStack
- Web quote fallback search
- FRED
- News API
- SEC EDGAR

## Tool Catalog (Phase 1 MVP)

- **Market**
  - `get_market_status`, `get_market_indices`, `get_vix`, `get_market_movers`, `get_sector_performance`, `get_market_breadth`
- **Stocks**
  - `get_stock_price`, `get_quote`, `get_company_profile`, `get_candles`, `get_stock_news`, `get_dividends`, `get_splits`, `get_earnings_calendar`
- **Technical**
  - `get_rsi`, `get_macd`, `get_sma`, `get_ema`, `get_support_resistance_levels`, `detect_chart_patterns`
- **Fundamental**
  - `get_key_financials`, `get_financial_statements`, `get_fundamental_ratings`, `get_price_targets`, `get_ownership_signals`, `get_sec_filings`
- **Options**
  - `get_options_chain`, `get_options_iv`, `get_options_greeks`, `get_unusual_options_activity`, `get_max_pain`
- **Risk**
  - `get_beta`, `get_sharpe_sortino`, `get_max_drawdown`, `get_var`, `get_correlation`, `get_rebalance_plan`, `get_markowitz_allocation`, `get_dividend_projection`, `get_tax_estimate`
- **News**
  - `get_company_news`, `get_market_news`
- **Screener**
  - `run_screener`
- **Portfolio**
  - `validate_portfolio_excel`, `analyze_portfolio_excel`, `portfolio_benchmark_report`, `portfolio_stress_test`

## Portfolio Excel Format

The portfolio module expects these exact columns in `.xlsx`/`.xls`:

- `Symbol`
- `Bucket` (`Core|Growth|Defensive|Income|Speculative`)
- `Quantity` (positive integer)
- `Entry_Price` (numeric)
- `Target_Weight` (decimal like `0.15`)

Validation rules:

- Required columns must exist
- No null values in required columns
- All symbols must be valid US ticker format
- `Target_Weight` sum must equal `1.0 +/- 0.01`

Example file path input:

- `C:/Users/LENOVO/Downloads/Sample_US_Portfolio_MCP_Format.xlsx`

## Environment Variables

Required (at least one external provider recommended):

- `FINNHUB_API_KEY`
- `ALPHAVANTAGE_API_KEY`
- `FMP_API_KEY`
- `TWELVEDATA_API_KEY`
- `MARKETSTACK_API_KEY`
- `FRED_API_KEY`
- `NEWS_API_KEY`

Optional:

- `YAHOO_FINANCE_ENABLED=true|false` (default `true`)
- `SEC_USER_AGENT` (default `local-stock-analyst/1.0 (support@example.com)`)
- `REQUEST_TIMEOUT_SECONDS` (default `15`)
- `CACHE_TTL_SECONDS` (default `60`)
- `PROVIDER_MIN_INTERVAL_SECONDS` (default `0.2`)
- `TRANSPORT_MODE=auto|stdio|http`
- `HTTP_TRANSPORT=sse|streamable`
- `HOST` / `PORT`
- `MCP_PATH` / `HEALTH_PATH`
- `CLAUDE_API_KEY` (or `ANTHROPIC_API_KEY`) for AI portfolio executive summaries
- `CLAUDE_MODEL` (or `ANTHROPIC_MODEL`), default `claude-sonnet-4-5-20250929`
- `PORTFOLIO_ENABLE_AI_SUMMARY=true|false` (default `true`)

## Stock Tool JSON Responses

All tools in the `stocks` domain now return strict JSON strings:

- Success example:

```json
{"source":"Alpha Vantage","data":{"symbol":"AAPL","price":210.5,"change":1.2,"percent_change":0.57,"high":211.0,"low":208.2,"open":209.4,"previous_close":209.3,"timestamp":1700000000,"source":"alphavantage"}}
```

- Failure example (shared for all stock-domain tools when fallback is exhausted):

```json
{"error":"All stock data providers are currently unavailable. Please try again later."}
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

### Stdio Mode

```powershell
$env:TRANSPORT_MODE="stdio"
python -m mcp_server
```

### HTTP Mode

```powershell
$env:TRANSPORT_MODE="http"
$env:HOST="0.0.0.0"
$env:PORT="8000"
python -m mcp_server
```

Health endpoint defaults to `/health`.

## Tests

```bash
python -m pytest -q
```

Protocol coverage now includes prompt/resource list/get/read success and error paths in `tests/test_mcp_prompts_resources.py`.

## Canonical Runtime Package

Use `mcp_server/` as the only supported runtime package and entrypoint:

- Run with `python -m mcp_server`
- Deploy using `mcp_server` module paths

`Resources/` is legacy/reference and is not maintained for new MCP prompt/resource capabilities.


