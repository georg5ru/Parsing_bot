import csv
from pathlib import Path
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font


EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)


def _convert_to_rows(data):
    rows = []

    for item in data:
        dt = datetime.fromtimestamp(item.published)

        er = 0
        if item.views:
            er = round(
                (item.cnt_likes + item.cnt_comments + item.cnt_shares) / item.views * 100,
                2,
            )

        rows.append({
            "Date": dt.strftime("%Y-%m-%d"),
            "URL": str(item.link),
            "Views": item.views,
            "Likes": item.cnt_likes,
            "Comments": item.cnt_comments,
            "Shares": item.cnt_shares,
            "ER": er,
            "Description": ", ".join(item.articles) if item.articles else "",
        })

    return rows


def generate_csv(data, task_id: int):
    file_path = EXPORTS_DIR / f"parsing_{task_id}.csv"
    rows = _convert_to_rows(data)

    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Date", "URL", "Views", "Likes", "Comments", "Shares", "ER", "Description"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return str(file_path)


def generate_excel(data, task_id: int):
    file_path = EXPORTS_DIR / f"parsing_{task_id}.xlsx"
    rows = _convert_to_rows(data)

    wb = Workbook()
    ws = wb.active
    ws.title = "Parsing Result"

    headers = ["Date", "URL", "Views", "Likes", "Comments", "Shares", "ER", "Description"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append(list(row.values()))

    wb.save(file_path)

    return str(file_path)