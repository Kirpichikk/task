FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG TARGET=app
ENV TARGET=$TARGET

RUN if [ "$TARGET" = "test" ]; then \
        pip install --no-cache-dir -r requirements_testing.txt; \
    fi

CMD if [ "$TARGET" = "test" ]; then \
        pytest test.py -v; \
    else \
        gunicorn -b 0.0.0.0:5000 main:app; \
    fi