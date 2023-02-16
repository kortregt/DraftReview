FROM python:3.9

ADD *.py ./

RUN pip install requests discord.py python-dotenv

CMD ["python", "./start_bot.py"]
