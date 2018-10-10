FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
WORKDIR /app
ADD . /app/

RUN pip3 install -U pip && \
    pip3 install -U -r requirements.txt

# Workaround: for reasons I don't understand, this package is not found
#             unless it's installed (again) after requirements.txt
# RUN pip3 install -U -e "git+https://github.com/limdauto/drf_openapi.git#egg=drf_openapi"
# RUN pip3 install -U -e "git+https://github.com/maykinmedia/drf_openapi.git@105-proxy-label-cannot-be-decoded#egg=drf_openapi"
