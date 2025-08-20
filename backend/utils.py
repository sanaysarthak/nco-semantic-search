# utils.py
import pandas as pd
import re

def parse_csv_file(file_stream):
    try:
        df = pd.read_csv(file_stream)
    except Exception:
        file_stream.seek(0)
        df = pd.read_csv(file_stream, engine='python')
    return df

def normalize_text(s: str) -> str:
    if s is None:
        return ''
    s = str(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def dataframe_to_records(df):
    return df.where(pd.notnull(df), None).to_dict(orient='records')
