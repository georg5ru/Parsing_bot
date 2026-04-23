import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font


EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)


def get_mock_rows(platform: str, account: str) -> list[dict]:
    return [
        {
            "Date": "2026-04-20",
            "URL": f"https://example.com/{platform.lower()}/{account}/video1",
            "Views": 12500,
            "Likes": 860,
            "Comments": 54,
            "ER": 7.31,
            "Description": "Первый тестовый ролик",
        },
        {
            "Date": "2026-04-18",
            "URL": f"https://example.com/{platform.lower()}/{account}/video2",
            "Views": 9800,
            "Likes": 650,
            "Comments": 42,
            "ER": 7.06,
            "Description": "Второй тестовый ролик",
        },
        {
            "Date": "2026-04-15",
            "URL": f"https://example.com/{platform.lower()}/{account}/video3",
            "Views": 15600,
            "Likes": 1200,
            "Comments": 77,
            "ER": 8.19,
            "Description": "Третий тестовый ролик",
        },
    ]


def generate_csv_for_task(task_id: int, platform: str, account: str) -> tuple[str, str, int, float]:
    file_path = EXPORTS_DIR / f"parsing_{task_id}.csv"
    rows = get_mock_rows(platform, account)

    with open(file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["Date", "URL", "Views", "Likes", "Comments", "ER", "Description"],
        )
        writer.writeheader()
        writer.writerows(rows)

    videos_count = len(rows)
    avg_interval_days = 2.5
    summary_text = f"{videos_count} видео, в среднем 1 видео каждые {avg_interval_days} дня"

    return str(file_path), summary_text, videos_count, avg_interval_days


def generate_excel_for_task(task_id: int, platform: str, account: str) -> tuple[str, str, int, float]:
    file_path = EXPORTS_DIR / f"parsing_{task_id}.xlsx"
    rows = get_mock_rows(platform, account)

    wb = Workbook()
    ws = wb.active
    ws.title = "Parsing Result"

    headers = ["Date", "URL", "Views", "Likes", "Comments", "ER", "Description"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append([
            row["Date"],
            row["URL"],
            row["Views"],
            row["Likes"],
            row["Comments"],
            row["ER"],
            row["Description"],
        ])

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 35

    wb.save(file_path)

    videos_count = len(rows)
    avg_interval_days = 2.5
    summary_text = f"{videos_count} видео, в среднем 1 видео каждые {avg_interval_days} дня"

    return str(file_path), summary_text, videos_count, avg_interval_days