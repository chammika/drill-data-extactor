# Drill data extractor

Extracts data from scanned well drilling files (PDF) and lets you check and correct it side by side with the scan. The corrected data is saved to a SQLite database for later use, such as machine learning model training.

![Drill data extractor](docs/drill-data-extractor.png)

Each file is expected to contain a Site Location Sheet, a Drill Log, pumping test reports and supporting letters. The forms are handwritten scans, so extraction uses a vision model (Claude or Gemini) and the result is meant to be reviewed.

## Installation

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs Python and the dependencies.

```
git clone https://github.com/chammika/drill-data-extactor.git
cd drill-data-extactor
uv sync
```

Set an API key for the extraction engine you want to use:

```
export ANTHROPIC_API_KEY=...   # Claude (default)
export GEMINI_API_KEY=...      # Gemini
```

## Running

```
uv run streamlit run app.py
```

The app opens in your browser. To start with Gemini selected, run `EXTRACTOR=gemini uv run streamlit run app.py`. The Gemini model can be changed with `GEMINI_MODEL=<model id>`.

## Usage

1. Put your PDF files in a folder (`samples/` by default) and enter its path in the sidebar.
2. Choose the extraction engine, then extract one file or all pending files.
3. Select a file. The scan is on the left with page navigation; the extracted data is on the right in tabs: Summary, Location sheet, Drill log, Pump tests and Other sections.
4. Correct any values, tick **Reviewed** when the record is checked, and press **Save**.

A file that has already been extracted is not extracted again, and a file whose Well No is already in the database loads the existing record.

## Data

Everything is stored in `drill_data.db` (SQLite) in the project folder:

| Table | Contents |
|---|---|
| `wells` | One row per well: summary fields, reviewed flag, the edited data and the original extraction as JSON |
| `drill_log_rows` | One row per drill log line |
| `pump_tests` | One row per pumping test |
| `other_sections` | Letters, job cards and other free text |
| `files` | Which PDF belongs to which well |

All values are stored as text, as written on the forms.
