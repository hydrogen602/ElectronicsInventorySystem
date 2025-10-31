FROM node:slim

WORKDIR /app

COPY ui/package.json ui/package-lock.json ui/tsconfig.json /app/

RUN npm install

COPY ui/src /app/src
COPY ui/public /app/public

ENV REACT_APP_INV_API=""
ENV REACT_APP_BASE_PATH=""

RUN npm run build

FROM python:3.12-slim
RUN apt-get update

ENV RUNNING_IN_DOCKER=true

RUN apt-get install --no-install-suggests --no-install-recommends --yes pipx
ENV PATH="/root/.local/bin:${PATH}"
RUN pipx install poetry

WORKDIR /app

COPY poetry.lock pyproject.toml README.md ./
COPY electronic_inv_sys ./electronic_inv_sys

RUN poetry install --only main

COPY --from=0 /app/build /app/

EXPOSE 8000

CMD ["poetry", "run", "fastapi", "run", "electronic_inv_sys"]
