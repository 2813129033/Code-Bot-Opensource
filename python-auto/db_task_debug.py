import pymysql

# 与 python-auto/db_connector.py 保持一致
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "cursorbot",
    "charset": "utf8mb4",
    "autocommit": True,
}

PENDING_FILTER = ("pending", "user_change", "review_change", "pending_modify")


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            print("[db] using:", cur.fetchone()[0])

            cur.execute("SELECT COUNT(1) FROM user_task")
            print("[user_task] total:", cur.fetchone()[0])

            cur.execute(
                """
                SELECT task_status, COUNT(1) AS cnt
                FROM user_task
                GROUP BY task_status
                ORDER BY cnt DESC
                """
            )
            rows = cur.fetchall()
            print("[user_task] by status:")
            for status, cnt in rows:
                print(f"  - {status}: {cnt}")

            placeholders = ",".join(["%s"] * len(PENDING_FILTER))
            cur.execute(
                f"""
                SELECT COUNT(1)
                FROM user_task
                WHERE task_status IN ({placeholders})
                """,
                PENDING_FILTER,
            )
            print("[user_task] pending filter count:", cur.fetchone()[0], "filter=", PENDING_FILTER)

            cur.execute(
                """
                SELECT id, task_id, user_id, task_status, create_time
                FROM user_task
                ORDER BY create_time DESC
                LIMIT 10
                """
            )
            print("[user_task] latest 10:")
            for r in cur.fetchall():
                print("  ", r)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

