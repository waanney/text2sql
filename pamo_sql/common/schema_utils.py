import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any


def get_rich_schema_ddl(db_path: str, max_samples: int = 3) -> str:
    """
    Builds an enriched DDL schema containing column names, data types,
    and 3 representative non-null sample values for each column.
    """
    if not db_path or not Path(db_path).exists():
        return ""

    enriched_tables = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        tables = cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        for table_name, original_sql in tables:
            try:
                # Get column info: (cid, name, type, notnull, dflt_value, pk)
                columns_info = cursor.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                col_descriptions = []

                for col in columns_info:
                    col_name = col[1]
                    col_type = col[2] or "TEXT"
                    
                    # Fetch sample values
                    try:
                        sample_rows = cursor.execute(
                            f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL AND "{col_name}" != "" LIMIT {max_samples}'
                        ).fetchall()
                        samples = [str(r[0]) for r in sample_rows]
                    except Exception:
                        samples = []

                    if samples:
                        sample_str = ", ".join([f'"{s}"' if isinstance(s, str) else str(s) for s in samples])
                        col_desc = f'  `{col_name}` {col_type} /* Samples: {sample_str} */'
                    else:
                        col_desc = f'  `{col_name}` {col_type}'
                    
                    col_descriptions.append(col_desc)

                table_ddl = f'CREATE TABLE `{table_name}` (\n' + ',\n'.join(col_descriptions) + '\n);'
                enriched_tables.append(table_ddl)
            except Exception:
                if original_sql:
                    enriched_tables.append(original_sql)

        conn.close()
    except Exception as e:
        print(f"[schema_utils] Error extracting rich DDL: {e}")
        return ""

    return "\n\n".join(enriched_tables)


def extract_value_links(question: str, evidence: str, db_path: str) -> List[str]:
    """
    Scans question and evidence for string phrases and matches them against
    text column values in the SQLite database to provide exact value-linking hints.
    """
    if not db_path or not Path(db_path).exists():
        return []

    # Extract potential entity phrases (quoted text or capitalized sequences / n-grams)
    phrases = set()
    
    # Quoted text
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", f"{question} {evidence}")
    phrases.update(quoted)

    # N-grams (2-4 words) from combined text
    combined_text = f"{question} {evidence}"
    words = re.findall(r"\b[A-Za-z0-9\-\.\,\(\)]+\b", combined_text)
    
    for n in range(2, 5):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            # Filter out common stop-word heavy n-grams
            if len(ngram) > 4 and not ngram.lower().startswith(("what is", "how many", "list the", "where is", "of the")):
                phrases.add(ngram)

    hints = []
    matched_keys = set()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        tables = [r[0] for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]

        for phrase in phrases:
            clean_phrase = phrase.strip(" .,'\"")
            if not clean_phrase or len(clean_phrase) < 3:
                continue

            for table in tables:
                columns = [c[1] for c in cursor.execute(f'PRAGMA table_info("{table}")').fetchall()]
                for col in columns:
                    try:
                        # Exact or prefix match
                        match = cursor.execute(
                            f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" LIKE ? LIMIT 1',
                            (f"%{clean_phrase}%",)
                        ).fetchone()
                        
                        if match and match[0]:
                            actual_val = str(match[0])
                            key = (table, col, actual_val)
                            if key not in matched_keys:
                                matched_keys.add(key)
                                hints.append(
                                    f"Value '{clean_phrase}' matches value '{actual_val}' in table '{table}', column '{col}'"
                                )
                                if len(hints) >= 10:
                                    break
                    except Exception:
                        pass
                if len(hints) >= 10:
                    break
            if len(hints) >= 10:
                break
        conn.close()
    except Exception as e:
        print(f"[schema_utils] Error in value linking: {e}")

    return hints
