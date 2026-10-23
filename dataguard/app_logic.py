import re
import pandas as pd

def add_issue(issues, row_index, column, value, issue_type, severity, recommendation):
    issues.append({
        "Row": int(row_index) + 1,
        "Column": str(column),
        "Value": "" if pd.isna(value) else str(value),
        "Issue": issue_type,
        "Severity": severity,
        "Recommended Action": recommendation,
    })

def analyze_dataframe(df, required_columns=None, unique_column="", numeric_rules=None,
                      email_columns=None, date_pair=("", "")):
    required_columns = required_columns or []
    numeric_rules = numeric_rules or {}
    email_columns = email_columns or []
    issues = []

    for col in required_columns:
        if col not in df.columns:
            add_issue(issues, 0, col, "", "Required column missing", "High",
                      "Add the required column or update the selected rule.")
        else:
            mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
            for idx in df.index[mask]:
                add_issue(issues, idx, col, df.at[idx, col], "Missing required value", "High",
                          "Verify the source and supply the correct value.")

    for idx in df.index[df.duplicated(keep=False)]:
        add_issue(issues, idx, "(entire row)", "", "Duplicate row", "Medium",
                  "Compare with the original source before removing a record.")

    if unique_column and unique_column in df.columns:
        nonempty = df[unique_column].notna() & df[unique_column].astype(str).str.strip().ne("")
        for idx in df.index[df[unique_column].duplicated(keep=False) & nonempty]:
            add_issue(issues, idx, unique_column, df.at[idx, unique_column],
                      "Duplicate identifier", "High", "Verify whether the identifier should be unique.")

    for col, rule in numeric_rules.items():
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        nonempty = df[col].notna() & df[col].astype(str).str.strip().ne("")
        for idx in df.index[nonempty & numeric.isna()]:
            add_issue(issues, idx, col, df.at[idx, col], "Invalid numeric value", "High",
                      "Check the expected numeric format and original source.")
        if rule.get("min") is not None:
            for idx in df.index[(numeric < rule["min"]).fillna(False)]:
                add_issue(issues, idx, col, df.at[idx, col], "Below minimum", "High",
                          f"Expected a value >= {rule['min']}.")
        if rule.get("max") is not None:
            for idx in df.index[(numeric > rule["max"]).fillna(False)]:
                add_issue(issues, idx, col, df.at[idx, col], "Above maximum", "High",
                          f"Expected a value <= {rule['max']}.")

    for col in email_columns:
        if col not in df.columns:
            continue
        for idx, value in df[col].items():
            if pd.isna(value) or str(value).strip() == "":
                continue
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(value).strip()):
                add_issue(issues, idx, col, value, "Invalid email format", "Medium",
                          "Check format; this does not verify that the mailbox exists.")

    start_col, end_col = date_pair
    if start_col and end_col and start_col in df.columns and end_col in df.columns:
        starts = pd.to_datetime(df[start_col], errors="coerce")
        ends = pd.to_datetime(df[end_col], errors="coerce")
        mask = starts.notna() & ends.notna() & (starts > ends)
        for idx in df.index[mask]:
            add_issue(issues, idx, f"{start_col} / {end_col}",
                      f"{df.at[idx, start_col]} / {df.at[idx, end_col]}",
                      "Date consistency error", "High",
                      "Verify that start date is not later than end date.")

    return pd.DataFrame(issues, columns=[
        "Row", "Column", "Value", "Issue", "Severity", "Recommended Action"
    ])
