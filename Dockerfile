FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    GENACADEMY_COACH_DATA_DIR=/data \
    GENACADEMY_COACH_TRACE_DIR=/data/traces \
    GENACADEMY_COACH_REVIEW_QUEUE_PATH=/data/review_queue.jsonl \
    GENACADEMY_DATA_DIR=/data \
    GENACADEMY_EMBED_MODEL=all-MiniLM-L6-v2 \
    GENACADEMY_EMBED_DIM=384 \
    HF_HOME=/workspace/Week3-TheAgenticLeap/genacademy-coach/.cache/huggingface

WORKDIR /workspace/Week3-TheAgenticLeap/genacademy-coach

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user

ARG GENACADEMY_RAG_GIT_URL=https://github.com/manjunath84/genacademy-rag.git
ARG GENACADEMY_RAG_REF=517faffbfdf37f8972f5bf3076e21eb2ab0ba7b4
RUN mkdir -p /workspace/Week2-RAG_ContextEngineering \
    && git clone --filter=blob:none --no-checkout "${GENACADEMY_RAG_GIT_URL}" \
        /workspace/Week2-RAG_ContextEngineering/genacademy-rag \
    && cd /workspace/Week2-RAG_ContextEngineering/genacademy-rag \
    && git fetch --depth 1 origin "${GENACADEMY_RAG_REF}" \
    && git checkout --detach FETCH_HEAD

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

RUN mkdir -p /workspace/Week3-TheAgenticLeap/genacademy-coach/.cache/huggingface /data/traces \
    && chown -R user:user /workspace/Week3-TheAgenticLeap/genacademy-coach/.cache /data
USER user

EXPOSE 7860

CMD ["bash", "scripts/start_hf_space.sh"]
