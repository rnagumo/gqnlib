FROM nvidia/cuda:10.2-cudnn7-runtime-ubuntu18.04

# Set up cudnn
ENV CUDNN_VERSION 7.6.5.32
LABEL com.nvidia.cudnn.version="${CUDNN_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcudnn7=$CUDNN_VERSION-1+cuda10.2 \
    && apt-mark hold libcudnn7 \
    && rm -rf /var/lib/apt/lists/*

# Install Python and utilities
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.7 python3.7-dev python3-pip python3-wheel python3-setuptools \
        git vim ssh wget gcc cmake build-essential libblas3 libblas-dev \
    && rm /usr/bin/python3 \
    && ln -s python3.7 /usr/bin/python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy package
WORKDIR /app
COPY bin/ bin/
COPY examples/ examples/
COPY gqnlib/ gqnlib/
COPY tests/ tests/
COPY setup.py setup.py

# Install package
RUN pip install --no-cache-dir .

# Install other requirements for examples
RUN pip install --no-cache-dir numpy==1.18.4 matplotlib==3.2.1 tqdm==4.46.0 \
        tensorflow == 2.2.0 tensorboardX==2.0
