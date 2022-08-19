FROM python:3.9

ENV PATH=".:${PATH}"

WORKDIR /monitor

# install python requirements for yagna_mon.py
RUN pip install requests

# run script + monitor
COPY discord_manager.py .
COPY golem_rpc_endpoint_check.py .
COPY monitor.py .
COPY README.md .


