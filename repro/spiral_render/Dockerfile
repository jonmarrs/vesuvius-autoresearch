# A volume-cartographer image that can actually complete a spiral ink render.
#
# The published runtime image (:edge and :main are one digest,
# sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4, built
# 2026-05-13) cannot: its vc_tifxyz2obj predates --keep, so render_ink.py's
# documented --flatten-keep 6.25 is rejected, and the only value it accepts
# (100) leaves flatboi SLIM-diverging (3 windings at 10 iters ran over 1h13m
# without finishing). It also lacks vc_obj_uv_lift entirely. Reported upstream
# as ScrollPrize/villa#1660.
#
# So: build the two missing/stale tools from pinned source, and graft them onto
# the published runtime image. Only vc_tifxyz2obj needs the heavy toolchain, and
# only as a single CMake target, which skips nearly all of VC3D and takes a few
# minutes rather than the hour a full build costs.

ARG VILLA_SHA=5479453a

# ---------------------------------------------------------------- build stage
FROM ghcr.io/scrollprize/villa/volume-cartographer:builder-ubuntu-24.04 AS vcbuild
ARG VILLA_SHA
# Sparse checkout: villa is large and only volume-cartographer is needed.
RUN git clone --filter=blob:none --sparse https://github.com/ScrollPrize/villa.git /src \
 && cd /src && git sparse-checkout set volume-cartographer && git checkout ${VILLA_SHA}
# UI/tracer, flatboi, python bindings and tests are all off: the runtime image
# already ships flatboi, and none of the rest is on the render path.
RUN cmake -S /src/volume-cartographer -B /build -DCMAKE_BUILD_TYPE=Release \
      -DVC_BUILD_APPS=ON -DVC_BUILD_UI_TRACER=OFF -DVC_BUILD_FLATBOI=OFF \
      -DVC_BUILD_PYTHON=OFF -DVC_TESTING=OFF \
 && cmake --build /build --target vc_tifxyz2obj -j"$(nproc)"
RUN mkdir -p /out/bin /out/lib \
 && cp /build/bin/vc_tifxyz2obj /out/bin/ \
 && find /build -name '*.so*' -type f -not -path '*/_deps/*' -exec cp {} /out/lib/ \;

# -------------------------------------------------------------- runtime image
FROM ghcr.io/scrollprize/villa/volume-cartographer:edge

# The stale vc_tifxyz2obj is shadowed rather than deleted: /usr/local/bin
# precedes the original on PATH, so `command -v` resolves to the new one.
COPY --from=vcbuild /out/lib/ /usr/local/lib/vc/
COPY --from=vcbuild /out/bin/vc_tifxyz2obj /usr/local/bin/vc_tifxyz2obj
RUN echo /usr/local/lib/vc > /etc/ld.so.conf.d/vc-local.conf && ldconfig

# CPU-only torch: tifxyz.py imports it for mesh tensor ops and the render path
# does no learning. The CUDA build would add several GB for nothing.
RUN python3 -m pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu torch \
 && python3 -m pip install --no-cache-dir einops scipy Pillow tifffile zarr

# vc_obj_uv_lift is 381 lines and, unlike the rest of VC3D, needs only
# header-only libigl + Eigen + OpenMP, so it builds here in seconds.
RUN git clone --depth 1 --branch v2.5.0 https://github.com/libigl/libigl.git /opt/libigl \
 && rm -rf /opt/libigl/.git
COPY vc_obj_uv_lift.cpp /tmp/vc_obj_uv_lift.cpp
RUN g++ -O2 -std=c++17 -fopenmp -I/opt/libigl/include -I/usr/include/eigen3 \
        /tmp/vc_obj_uv_lift.cpp -o /usr/local/bin/vc_obj_uv_lift \
 && rm /tmp/vc_obj_uv_lift.cpp

# Fail at build time rather than halfway through a render.
RUN python3 -c "import torch, einops, scipy.ndimage, PIL, tifffile; print('render deps ok')" \
 && for b in vc_render_tifxyz vc_tifxyz_trim vc_tifxyz2obj vc_obj2tifxyz vc_obj_uv_lift flatboi; do \
      command -v $b >/dev/null || { echo "MISSING $b"; exit 1; }; done \
 && vc_tifxyz2obj 2>&1 | grep -q -- '--keep' \
 || { echo 'FATAL: vc_tifxyz2obj still does not accept --keep'; exit 1; }
RUN echo "all six binaries present and vc_tifxyz2obj accepts --keep"
