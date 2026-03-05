# MCP Prompts and Resources - Easy Explanation

This document explains in simple words how **Prompts** and **Resources** work in this project, so you can present it to your TL.

---

## 1) Big Picture

In MCP server:

- **Prompt** = a dynamic instruction template for the LLM  
  (example: "analyze this portfolio and return structured insights")
- **Resource** = structured data exposed through a URI  
  (example: "give latest saved portfolio analysis JSON")

So, think of it like:

- Prompt tells the model **what to do**
- Resource gives the model/client **what data to read**

---

## 2) How Prompt Works (Portfolio Example)

File: `mcp_server/prompts/portfolio_prompts.py`

### Step-by-step flow

1. `register_portfolio_prompts(mcp)` is called during server setup.
2. It registers one prompt with decorator `@mcp.prompt(...)`.
3. Prompt name is `portfolio_analysis`.
4. When client calls this prompt, function `portfolio_analysis(portfolio: str)` runs.
5. It calls `_build_portfolio_analysis_prompt(portfolio)`.
6. Builder validates input:
   - trims spaces using `strip()`
   - if empty, raises `ValueError("Missing required argument: portfolio.")`
7. If valid, it returns a multi-line instruction string with required sections:
   - allocation diagnostics
   - risk findings
   - benchmark interpretation
   - action plan

### Example call

Client asks:

`get_prompt("portfolio_analysis", {"portfolio": "US Core"})`

Server returns prompt text similar to:

- "You are an institutional portfolio analyst..."
- "Analyze the portfolio named 'US Core' and provide..."

This text is then used by the LLM to generate final analysis output.

---

## 3) How Resource Works (Portfolio Snapshot Example)

File: `mcp_server/resources/portfolio_resources.py`

Two resources are registered:

1. **Static current snapshot URI**  
   `portfolio://current`
2. **Template URI by report type**  
   `portfolio://snapshot/{report_type}`

### A) `portfolio://current`

- Calls `services.portfolio.get_current_resource_snapshot()`
- If no snapshot exists -> raises:
  `ValueError("Portfolio resource not found. Run a portfolio workflow first.")`
- If snapshot exists -> returns JSON string (`application/json`)

### B) `portfolio://snapshot/{report_type}`

- Example URI: `portfolio://snapshot/analysis`
- Calls `services.portfolio.get_resource_snapshot(report_type)`
- If matching report type not found -> raises:
  `ValueError("Portfolio resource not found for the given report_type.")`
- If found -> returns JSON string (`application/json`)

---

## 4) End-to-End Example

### Scenario
User runs portfolio workflow first (analysis/benchmark/stress tools).

### Then:

1. Client reads resource:
   - `read_resource("portfolio://current")`
   - Gets latest analysis payload JSON.
2. Client asks prompt:
   - `get_prompt("portfolio_analysis", {"portfolio": "US Core"})`
   - Gets analysis instruction template.
3. LLM can use resource data + prompt instruction to produce final response.

---

## 5) Prompt vs Resource (Quick Comparison)

- **Prompt**
  - Purpose: guide model behavior
  - Output: text instruction
  - Input: arguments like `portfolio`
  - Error example: missing required argument

- **Resource**
  - Purpose: provide reusable data
  - Output: JSON content via URI
  - Input: URI (sometimes with template param)
  - Error example: resource not found / no snapshot yet

---

## 6) What Is Verified by Tests

File: `tests/test_mcp_prompts_resources.py`

Tests confirm:

- Prompt registration appears in `list_prompts()`
- Prompt retrieval works and includes expected text content
- Unknown prompt name errors correctly
- Missing prompt arguments error correctly
- Resource registration appears in `list_resources()`
- Resource read returns valid JSON with expected fields
- Resource template appears in `list_resource_templates()`
- Invalid/unknown resources raise errors
- Error messages do not leak sensitive terms like token/api_key

---

## 7) One-Line TL Pitch

"In our MCP server, prompts define **how the model should analyze**, while resources expose **latest portfolio data as JSON URIs**; together they separate instruction logic from data delivery and make the workflow clean, testable, and reusable."

