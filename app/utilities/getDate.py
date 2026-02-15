from datetime import date, timedelta

def getCurrentDate():
    today = date.today()
    return today

def getSundayDate() -> str:
    today = date.today()
    today_weekday = today.weekday()

    days_from_sunday = (today_weekday + 1) % 6
    latest_sunday_date = today - timedelta(days=days_from_sunday)

    return str(latest_sunday_date)

if __name__ == "__main__":
    getSundayDate()
    