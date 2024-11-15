FROM python:3.10-slim AS builder

# Copying argilla distribution files
COPY dist/*.whl /packages/
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python-dev-is-python3 libpq-dev gcc && \
    pip install --upgrade uv && \
    for wheel in /packages/*.whl; do uv pip install "uvicorn[standard]" "$wheel[extraction, llm]"; done && \
    apt-get remove -y python-dev-is-python3 libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /packages

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y libpq-dev nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Set environment variables for the container
ARG ENV=dev
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV NLTK_DATA="/home/extralit/llama_index_cache"
ENV LLAMA_INDEX_CACHE_DIR="/home/extralit/llama_index_cache"

# Create a user and a volume for argilla
SHELL ["/bin/bash", "-c"]
RUN source /opt/venv/bin/activate
RUN useradd -ms /bin/bash extralit

# Copy the entire repository into /home/argilla in the container
COPY . /home/extralit/

# Change the ownership of the /home/argilla directory to the new user
WORKDIR /home/extralit/

RUN uv pip install -e "."

# Set the working directory in the container to /home/extralit
RUN chown -R extralit:extralit /home/extralit

USER extralit
EXPOSE 5555

# Run the command to start uvicorn server
CMD if [ "$ENV" = "dev" ]; then \
    uvicorn extralit.server.app:app --host 0.0.0.0 --port 5555 --reload; \
    else \
    uvicorn extralit.server.app:app --host 0.0.0.0 --port 5555; \
    fi
