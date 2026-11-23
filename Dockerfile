#
# Copyright (c) 2024 IB Systems GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# ---- builder stage: build the venv ----
FROM python:3.12.16-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install -r requirements.txt

# ---- runtime stage: slim image with the venv copied in ----
FROM python:3.12.16-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq bash curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root runtime user
RUN useradd -m -u 10001 appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY . .

# App writes device.json / onboard-token.json under ./data and devices-secret.yaml
# under ./resources at runtime, so the app dir must be writable by the runtime user.
RUN chown -R appuser:appuser /app

USER appuser

CMD ["kopf", "run", "main.py"]
