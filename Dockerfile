FROM python:3.9

ENV PATH=".:${PATH}"

WORKDIR /monitor

# install python requirements for yagna_mon.py
RUN pip install requests aiohttp jinja2 aiohttp-jinja2 batch-rpc-provider dataclasses-json

# run script + monitor
COPY *.py ./
COPY templates ./
COPY README.md .


