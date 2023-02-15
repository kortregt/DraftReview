FROM python:3

ADD *.py .

RUN pip install requests discord.py==1.7.2 python-dotenv

CMD ["python", "./start_bot.py"]
