# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Create a user and a volume for argilla
RUN useradd -ms /bin/bash extralit

# Install any needed packages specified in requirements.txt
# Set up a virtual environment in /opt/venv
SHELL ["/bin/bash", "-c"]
RUN pip install -q uv && uv venv /opt/venv && source /opt/venv/bin/activate
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Copy the entire repository into /home/argilla in the container
COPY . /home/extralit/

# Change the ownership of the /home/argilla directory to the new user
WORKDIR /home/extralit/

RUN uv pip install -q uvicorn[standard] -e /home/extralit/argilla/argilla -e ".[extraction, llm]"

# Set the working directory in the container to /home/extralit
RUN chown -R extralit:extralit /home/extralit

USER extralit
EXPOSE 5555

# Run the command to start uVicorn server
CMD ["uvicorn", "extralit.app:app", "--host", "0.0.0.0", "--port", "5555", "--reload"]
