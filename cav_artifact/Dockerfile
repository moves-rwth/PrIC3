FROM ubuntu:bionic

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Setup timezone for texlive-latex-extra
RUN ln -snf /usr/share/zoneinfo/Etc/UTC /etc/localtime \
    && echo "Etc/UTC" > /etc/timezone

WORKDIR /root/artifact
COPY . .
RUN bash scripts/install.bash

WORKDIR /root/
COPY cav_artifact/README.md .

CMD bash -c 'cd /root && source artifact/env_python/bin/activate && exec bash'
