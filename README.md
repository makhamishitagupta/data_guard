# DataGuard: Automated Error Detection and Data Integrity Assessment

Beginner-friendly CBP project using Python, Pandas, and Streamlit.

## Features
- Upload CSV/XLSX datasets
- Data preview and profiling
- Missing-value checks
- Duplicate full-row and duplicate ID checks (select a column)
- Numeric min/max rules
- Email-format checks (optional by column name)
- Cross-column consistency example: start date must not be after end date (optional)
- Data quality score based on configured checks
- Interactive charts
- Download issue report and original data with optional conservative cleaning

## Setup (Windows)
1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Create and activate an environment:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   python -m pip install -r requirements.txt
   ```
5. Run:
   ```bat
   streamlit run app.py
   ```

## Demo dataset
Upload `sample_data/students_with_errors.csv`.

## Important notes
- Validation rules are examples; adapt ranges to your actual dataset.
- Outliers are not automatically errors.
- A quality score is a configurable summary, not proof that data is factually accurate.
- The app does not overwrite uploaded files. Review issues before using cleaned data.
- Report row numbers are shown as 1-based data row numbers (excluding the header).
