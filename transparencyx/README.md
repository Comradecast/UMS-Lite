# TransparencyX

A Python civic-data project that consolidates U.S. congressional financial disclosure information into a normalized, searchable dataset.

## What This Project Is
- **Normalization:** Standardizing highly fragmented public disclosure formats.
- **Estimation Bands:** Representing financial ranges accurately without claiming precision.
- **Audit-Friendly:** Preserving original source text to trace back to raw disclosure reports.

## What This Project Is NOT
- **Exact Net Worth:** Financial disclosures are inherently ranges. TransparencyX does not claim to know exact wealth.
- **Inference Engine:** This project does not invent data, infer missing values, or guess unknown bounds.
- **Political Opinion Tool:** This is purely a factual representation of publicly available financial disclosures.

## Note on Sources
Official source priority comes first. House and Senate sources are separate, inconsistent, and will be handled accordingly in upcoming phases.

## Installation and Usage
Currently in Phase 0 (Scaffold & Range Parsing).

To install for development:
```bash
pip install -e .[dev]
```

To use the CLI:
```bash
transparencyx --version
transparencyx sources
transparencyx parse-range "$1,001 - $15,000"
```
