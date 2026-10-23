import io
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="DataGuard | Data Integrity", page_icon="🛡️", layout="wide")

st.title("🛡️ DataGuard")
st.subheader("Automated Error Detection and Data Integrity Assessment")
st.caption("Upload a CSV or Excel file to profile data, detect quality issues, and export a report.")

from dataguard.app_logic import analyze_dataframe

def completeness_score(df):
    """Percentage of non-empty cells. It measures completeness only."""
    total = df.shape[0] * df.shape[1]
    if total == 0:
        return 100.0
    missing = int(df.isna().sum().sum())
    # Treat whitespace-only strings as missing too.
    for col in df.select_dtypes(include=["object", "string"]).columns:
        missing += int((df[col].notna() & df[col].astype(str).str.strip().eq("")).sum())
    return max(0.0, 100.0 * (total - missing) / total)

with st.sidebar:
    st.header("Validation settings")
    st.write("Rules are configurable. Start with the sample dataset.")
    st.caption("Only selected required columns are checked for missing values.")

uploaded = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])

if uploaded is None:
    st.info("No file uploaded yet.")
    st.markdown("""
    **Checks available**
    - Missing values in selected required columns
    - Duplicate complete rows
    - Duplicate identifiers
    - Numeric minimum / maximum
    - Email format
    - Start-date / end-date consistency
    """)
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
except Exception as exc:
    st.error(f"Could not read this file. Check the file format and try again. Details: {exc}")
    st.stop()

if df.empty:
    st.warning("This file has no data rows.")
    st.stop()

if len(df.columns) == 0:
    st.error("No columns were found in the uploaded file.")
    st.stop()

# Normalize column names only for selection display? Preserve source column names.
all_columns = list(df.columns)

st.markdown("### 1. Dataset preview")
m1, m2, m3 = st.columns(3)
m1.metric("Rows", f"{df.shape[0]:,}")
m2.metric("Columns", f"{df.shape[1]:,}")
m3.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
st.dataframe(df.head(100), use_container_width=True)

with st.expander("View data types and summary"):
    profile = pd.DataFrame({
        "Column": df.columns.astype(str),
        "Data type": [str(dtype) for dtype in df.dtypes],
        "Missing cells": [int(df[c].isna().sum()) for c in df.columns],
        "Unique values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    st.dataframe(profile, use_container_width=True)

st.markdown("### 2. Configure checks")
default_required = [c for c in ["Student_ID", "Name", "Age", "Marks", "Email"] if c in all_columns]
required_columns = st.multiselect(
    "Columns that must not be empty",
    options=all_columns,
    default=default_required,
    help="Select columns where missing or blank values should be reported."
)
unique_default = "Student_ID" if "Student_ID" in all_columns else ""
unique_options = ["(none)"] + all_columns
selected_unique = st.selectbox(
    "Column that should be unique",
    options=unique_options,
    index=(unique_options.index(unique_default) if unique_default else 0)
)
unique_column = "" if selected_unique == "(none)" else selected_unique

st.write("**Numeric range rules**")
numeric_candidates = [c for c in all_columns if pd.api.types.is_numeric_dtype(df[c])]
# Also allow object columns that look numeric.
for c in all_columns:
    if c not in numeric_candidates and pd.to_numeric(df[c], errors="coerce").notna().any():
        numeric_candidates.append(c)

numeric_rules = {}
if numeric_candidates:
    chosen_numeric = st.multiselect(
        "Select numeric columns to validate",
        options=numeric_candidates,
        default=[c for c in ["Age", "Marks"] if c in numeric_candidates]
    )
    cols = st.columns(2)
    for i, col in enumerate(chosen_numeric):
        with cols[i % 2]:
            st.markdown(f"**{col}**")
            low, high = st.columns(2)
            min_text = low.text_input(f"Minimum for {col}", value=("0" if col.lower() in ["age", "marks", "score", "quantity", "price"] else ""), key=f"min_{col}")
            default_max = "100" if col.lower() in ["marks", "score", "attendance"] else ("120" if col.lower() == "age" else "")
            max_text = high.text_input(f"Maximum for {col}", value=default_max, key=f"max_{col}")
            try:
                min_value = float(min_text) if min_text.strip() else None
                max_value = float(max_text) if max_text.strip() else None
                if min_value is not None and max_value is not None and min_value > max_value:
                    st.error(f"Minimum for {col} cannot exceed maximum.")
                else:
                    numeric_rules[col] = {"min": min_value, "max": max_value}
            except ValueError:
                st.error(f"Rules for {col} must be numeric. Leave a field blank if no limit is needed.")
else:
    st.caption("No numeric columns detected.")

email_candidates = [c for c in all_columns if "email" in str(c).lower()]
email_columns = st.multiselect("Columns to check for email format", all_columns, default=email_candidates)

date_candidates = [c for c in all_columns if "date" in str(c).lower()]
date_cols_options = ["(none)"] + date_candidates
start_default = "Start_Date" if "Start_Date" in all_columns else ""
end_default = "End_Date" if "End_Date" in all_columns else ""
date_pair = ("", "")
if date_candidates:
    d1, d2 = st.columns(2)
    start_choice = d1.selectbox("Start-date column", date_cols_options,
                                index=date_cols_options.index(start_default) if start_default else 0)
    end_choice = d2.selectbox("End-date column", date_cols_options,
                              index=date_cols_options.index(end_default) if end_default else 0)
    date_pair = ("" if start_choice == "(none)" else start_choice,
                 "" if end_choice == "(none)" else end_choice)

if st.button("🔎 Analyze dataset", type="primary", use_container_width=True):
    issues = analyze_dataframe(df, required_columns, unique_column, numeric_rules, email_columns, date_pair)
    st.session_state["issues"] = issues
    st.session_state["analyzed"] = True
    st.session_state["source_name"] = uploaded.name
    st.session_state["source_rows"] = len(df)

if st.session_state.get("analyzed", False):
    issues = st.session_state.get("issues", pd.DataFrame())
    st.markdown("### 3. Assessment results")
    issue_count = len(issues)
    unique_issue_rows = int(issues["Row"].nunique()) if issue_count else 0
    completeness = completeness_score(df)
    issue_free_rows = max(0, len(df) - unique_issue_rows)
    validity_proxy = 100.0 * issue_free_rows / len(df) if len(df) else 100.0

    a, b, c, d = st.columns(4)
    a.metric("Issues found", f"{issue_count:,}")
    b.metric("Rows with issues", f"{unique_issue_rows:,}")
    c.metric("Completeness", f"{completeness:.1f}%")
    d.metric("Rows with no flagged issues", f"{validity_proxy:.1f}%")

    st.caption("Completeness measures non-empty cells. 'Rows with no flagged issues' is a rule-based proxy, not proof of accuracy.")

    if issue_count:
        category_counts = issues["Issue"].value_counts().rename_axis("Issue type").reset_index(name="Count")
        fig = px.bar(category_counts, x="Issue type", y="Count", title="Detected issues by category", text="Count")
        st.plotly_chart(fig, use_container_width=True)
        severity_counts = issues["Severity"].value_counts().rename_axis("Severity").reset_index(name="Count")
        fig2 = px.pie(severity_counts, names="Severity", values="Count", title="Issue severity distribution")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(issues, use_container_width=True)
    else:
        st.success("No issues were found by the selected rules. This does not guarantee that all values are factually accurate.")

    st.download_button(
        "⬇️ Download issue report (CSV)",
        data=issues.to_csv(index=False).encode("utf-8"),
        file_name="dataguard_issue_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### 4. Optional conservative cleaning")
    st.warning("Cleaning changes the exported copy only. Review the issue report first; the uploaded file is not overwritten.")
    drop_duplicates = st.checkbox("Remove exact duplicate rows from exported copy", value=False)
    trim_spaces = st.checkbox("Trim leading/trailing spaces in text columns", value=False)
    cleaned = df.copy()
    if drop_duplicates:
        cleaned = cleaned.drop_duplicates()
    if trim_spaces:
        for col in cleaned.select_dtypes(include=["object", "string"]).columns:
            cleaned[col] = cleaned[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    st.download_button(
        "⬇️ Download processed dataset (CSV)",
        data=cleaned.to_csv(index=False).encode("utf-8"),
        file_name="dataguard_processed_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown("---")
st.caption("DataGuard CBP prototype • Rule-based validation • Inspect results before making corrections")
