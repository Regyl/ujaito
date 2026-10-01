import os
import csv
import shutil
import sqlite3
from pathlib import Path

def get_chrome_login_data_path():
    home = Path.home()

    paths = [
        # Windows
        home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Login Data",
        # macOS
        home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Login Data",
        # Linux
        home / ".config" / "google-chrome" / "Default" / "Login Data",
    ]

    for p in paths:
        if p.exists():
            return p

    raise FileNotFoundError("File Login Data not found")

def export_chrome_logins_to_csv(output_file="chrome_passwords_full.csv"):
    db_path = get_chrome_login_data_path()

    # Chrome блокирует файл, поэтому делаем копию
    tmp_db = "login_data_copy.db"
    shutil.copyfile(db_path, tmp_db)

    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()

    # Получаем список всех столбцов
    column_names = ['origin_url', 'username_element', 'username_value', 'date_created', 'blacklisted_by_user', 'times_used', 'id', 'date_last_used', 'date_password_modified']

    # Читаем всю таблицу
    cursor.execute("SELECT origin_url, username_element, username_value, date_created, blacklisted_by_user, times_used, id, date_last_used, date_password_modified FROM logins")
    rows = cursor.fetchall()

    conn.close()
    os.remove(tmp_db)

    # Экспорт в CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)

    return output_file


if __name__ == "__main__":
    path = export_chrome_logins_to_csv()
    print(f"Готово! Данные сохранены в: {path}")
