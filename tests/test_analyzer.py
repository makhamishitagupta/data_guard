import pandas as pd
from dataguard.app_logic import analyze_dataframe

def test_detects_missing_duplicate_and_range():
    df = pd.DataFrame({
        "Student_ID": ["S1", "S1", "S3"],
        "Name": ["A", "A", None],
        "Age": [19, 19, 200],
        "Marks": [80, 80, 110],
    })
    rules = {"Age": {"min": 0, "max": 120}, "Marks": {"min": 0, "max": 100}}
    issues = analyze_dataframe(df, ["Name"], "Student_ID", rules, [], ("", ""))
    assert "Missing required value" in set(issues["Issue"])
    assert "Duplicate row" in set(issues["Issue"])
    assert "Duplicate identifier" in set(issues["Issue"])
    assert "Above maximum" in set(issues["Issue"])
