# 蒸着執行録 鍛造工場 — Blenderヘッドレス入り Cloud Run コンテナ。
# ビルドコンテキストはリポジトリルート(cloud/forge/cloudbuild.yaml 参照)。
FROM python:3.11-slim

# Blender headless の実行に要る共有ライブラリ + mesa(ソフトウェアGL。
# EEVEE レンダが立てばVRMサムネイルも付く。立たなくても --render-views soft で完走)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl xz-utils ca-certificates \
    libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 \
    libgl1 libegl1 libgles2 libglu1-mesa libgl1-mesa-dri \
    libxkbcommon0 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*

ARG BLENDER_URL=https://download.blender.org/release/Blender5.1/blender-5.1.1-linux-x64.tar.xz
RUN curl -fsSL "$BLENDER_URL" | tar -xJ -C /opt \
    && ln -s /opt/blender-*-linux-x64 /opt/blender
ENV HENSHIN_BLENDER_EXE=/opt/blender/blender

# VRMアドオン(エクスポートに必須。ビルド時にネットワークが要る)
RUN /opt/blender/blender --background --command extension install vrm \
    || /opt/blender/blender --command extension install vrm
RUN /opt/blender/blender --background --command extension list 2>/dev/null | grep -i vrm

WORKDIR /app
COPY src ./src
COPY schemas ./schemas
COPY tools ./tools
COPY viewer/assets/vrm/default.vrm ./viewer/assets/vrm/default.vrm
COPY cloud/forge ./cloud/forge

ENV PYTHONUNBUFFERED=1 \
    FORGE_WORK_DIR=/tmp/forge

CMD ["python", "cloud/forge/forge_server.py"]
