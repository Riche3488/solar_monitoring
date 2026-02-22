from datetime import datetime

import pytz
from dotenv import load_dotenv

load_dotenv()

from get_data import get_generation_time
from telegram import send_message


def main():
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)

    data = get_generation_time()

    message = (
        f"[태양광 발전 현황] {now.strftime('%Y-%m-%d %H:%M')} KST\n"
        f"{'─' * 24}\n"
        f"발전소1 발전 시간: {data['발전소1']}\n"
        f"발전소2 발전 시간: {data['발전소2']}"
    )

    result = send_message(message)
    print(message)
    print("텔레그램 전송 결과:", result)


if __name__ == "__main__":
    main()
