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

# VRMアドオン(エクスポートに必須。ビルド時にネットワークが要る)。
# 新品プロファイルはリポジトリ索引が未同期で install が
# 「Package not found / sync required!」になる — sync を必ず先行させる
# --online-mode: 新品プロファイルは「オンラインアクセス」既定OFFで
# repo_sync_all が RuntimeError になる(Blender 4.2+の仕様)
RUN /opt/blender/blender --background --online-mode --command extension sync \
    && (/opt/blender/blender --background --online-mode --command extension install vrm --enable \
        || /opt/blender/blender --background --online-mode --command extension install vrm)
# 有効化をユーザープリファレンスに永続化し、実際にimportできることを検証
# (bpy.ops の hasattr は遅延スタブで偽陽性 — module import が本物の証拠)
RUN /opt/blender/blender --background --python-expr "import bpy, addon_utils; addon_utils.enable('bl_ext.blender_org.vrm', default_set=True, persistent=True); bpy.ops.wm.save_userpref(); import bl_ext.blender_org.vrm; print('VRM_ADDON_OK')" \
    | grep VRM_ADDON_OK

WORKDIR /app
COPY src ./src
COPY schemas ./schemas
COPY tools ./tools
COPY viewer/assets/vrm/default.vrm ./viewer/assets/vrm/default.vrm
COPY cloud/forge ./cloud/forge

ENV PYTHONUNBUFFERED=1 \
    FORGE_WORK_DIR=/tmp/forge

CMD ["python", "cloud/forge/forge_server.py"]
