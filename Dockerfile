FROM python:3.11

RUN mkdir /ring-mtr
WORKDIR /ring-mtr

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY ./* ./

ENTRYPOINT ["python", "/ring-mtr/ring-mtr.py"]
