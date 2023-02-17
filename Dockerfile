FROM python:3.9

ADD *.py ./

RUN pip install requests py-cord python-dotenv

CMD ["python", "./start_bot.py"]
