# Wanted transport bot

Telegram bot that checks whether a vehicle is in the Ukrainian open dataset of wanted transport (`data/carswanted.json`, about 79 thousand records).

The bot answers in Ukrainian. A search is exact after cleanup: letter case, spaces, and dashes do not matter. On a plate, Latin letters that look like Ukrainian plate letters are treated as those Cyrillic letters, so `AE9157CX` matches `АЕ9157СХ`.

## Run

```bash
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

`BOT_TOKEN` is read from `.env` in the project root. Do not commit that file.

The program is five files:

- `main.py` starts the bot and loads the data once.
- `config.py` reads the token and the path to the JSON file.
- `clean.py` makes a plate, number, or brand comparable.
- `cars.py` finds a vehicle and prepares the statistics.
- `handlers.py` shows the Telegram menu and the replies.

## Demo (about two minutes)

1. Send `/start`.
2. Tap **Номерний знак** and send `ВТ8360АА`. The card is a ГАЗ 31105 from the wanted list.
3. Send a plate that is not in the file, for example `АА0000АА`. The bot says it is not wanted.
4. Tap **Назад**, then **Статистика**.
5. Open **За типом**, then **Останні викрадення**.

Other searches from the same menu: body number, chassis number, engine number, and brand plus model (`KIA SORENTO`). A brand alone, when it has many models, asks you to add the model instead of listing every record.
