"""finance-advisor — deterministic CLI for an AI financial advisor.

The CLI owns every numeric operation: imports, dedup, categorization, queries,
aggregations. The AI layer reads the CLI's JSON output and narrates it.
The AI never does arithmetic on financial data.
"""

__version__ = "0.1.0"
