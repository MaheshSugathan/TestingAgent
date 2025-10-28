FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Set environment variables
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}
ENV AWS_REGION=us-east-1

# Set the CMD to your handler
CMD [ "cli.lambda_handler" ]

