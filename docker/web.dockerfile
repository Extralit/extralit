# Use an official Node.js runtime as the base image
FROM node:18

# Create a user
RUN useradd -ms /bin/bash argilla

# Set the working directory
WORKDIR /home/argilla/

# Change the ownership of the /home/appuser directory to the new user
RUN chown -R argilla:argilla /home/argilla

# Copy the frontend directory to the container
COPY frontend/ ./frontend/

# Copy the scripts/build_frontend.sh script to the container
COPY scripts/ ./scripts/

# Switch to the new user
USER argilla

# Install the project dependencies and build frontend static assets
RUN chmod +x ./scripts/build_frontend.sh && /bin/bash ./scripts/build_frontend.sh

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD /bin/bash -c "cd frontend && npm run dev"
