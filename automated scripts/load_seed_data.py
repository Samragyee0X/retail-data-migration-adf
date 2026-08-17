
import os
import sys
import pandas as pd
import pyodbc

def get_connection():
    server = os.environ.get("SQL_SERVER")
    database = os.environ.get("SQL_DATABASE")
    user = os.environ.get("SQL_USER")
    password = os.environ.get("SQL_PASSWORD")

    missing = [name for name, val in [
        ("SQL_SERVER", server), ("SQL_DATABASE", database),
        ("SQL_USER", user), ("SQL_PASSWORD", password)
    ] if not val]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def load_table(cursor, csv_path: str, table: str, columns: list[str]):
    df = pd.read_csv(csv_path)
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    sql = f"INSERT INTO dbo.{table} ({col_list}) VALUES ({placeholders})"

    rows = [tuple(row[c] for c in columns) for _, row in df.iterrows()]

    cursor.fast_executemany = True
    cursor.executemany(sql, rows)
    print(f"  {table}: inserted {len(rows)} rows from {csv_path}")


def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("Loading seed data...")
    try:
        load_table(cursor, "product.csv", "Product", ["prod_num", "prod_name"])
        load_table(cursor, "store.csv", "Store", ["store_num", "store_name", "store_address"])
        load_table(cursor, "customer.csv", "Customer", ["cust_num", "cust_name", "phone"])
        conn.commit()
        print("All tables loaded and committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error occurred, rolled back: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
