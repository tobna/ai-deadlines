FROM nginx:latest

RUN apt update

# RUN apt install -y libcurl3-gnutls make wget --fix-missing

RUN apt install -y git wget --fix-missing

RUN wget https://ftp.debian.org/debian/pool/main/p/python3.11/libpython3.11-minimal_3.11.2-6+deb12u6_amd64.deb
RUN apt install -y ./libpython3.11-minimal_3.11.2-6+deb12u6_amd64.deb

RUN wget https://ftp.debian.org/debian/pool/main/p/python3.11/python3.11-minimal_3.11.2-6+deb12u6_amd64.deb
RUN apt install -y ./python3.11-minimal_3.11.2-6+deb12u6_amd64.deb

RUN wget https://ftp.debian.org/debian/pool/main/p/python3.11/libpython3.11-stdlib_3.11.2-6+deb12u6_amd64.deb
RUN apt install -y ./libpython3.11-stdlib_3.11.2-6+deb12u6_amd64.deb

RUN wget https://ftp.debian.org/debian/pool/main/p/python3.11/python3.11_3.11.2-6+deb12u6_amd64.deb
RUN apt install -y ./python3.11_3.11.2-6+deb12u6_amd64.deb

RUN ln /usr/bin/python3.11 /usr/bin/python3
RUN ln /usr/bin/python3 /usr/bin/python

RUN rm /usr/lib/python3.11/EXTERNALLY-MANAGED
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py

RUN pip install requests bs4 pytz pyyaml dateparser
