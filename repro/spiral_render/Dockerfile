# render_ink.py needs a Python stack the published volume-cartographer image does
# not carry, and that image is the only practical source of the native VC binaries
# (building the full VC3D pulls Ceres, OpenCV, CGAL and Qt).
#
# Base image: :edge and :main are the SAME digest
# (sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4, built
# 2026-05-13). Both ship vc_render_tifxyz, vc_tifxyz_trim, vc_tifxyz2obj,
# vc_obj2tifxyz and flatboi, and BOTH lack vc_obj_uv_lift, which render_ink.py
# invokes whenever --flatten-keep < 100 (the default is 6.25). Its source is in
# current main, so the images predate it. We build it here.
FROM ghcr.io/scrollprize/villa/volume-cartographer:edge

# CPU-only torch: tifxyz.py imports it for mesh tensor ops and the render path does
# no learning. The CUDA build would add several GB for nothing.
RUN python3 -m pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu torch \
 && python3 -m pip install --no-cache-dir einops scipy Pillow tifffile zarr

# vc_obj_uv_lift is 381 lines and, unlike the rest of VC3D, depends only on
# header-only libigl + Eigen + OpenMP. Eigen is already in the image; libigl is
# not, so fetch just the headers. Without this binary the only way to render is
# --flatten-keep 100, which leaves SLIM flattening a full-resolution mesh: 200k
# vertices took over 13 minutes single-threaded, against ~1/16 the points at the
# documented default.
RUN git clone --depth 1 --branch v2.5.0 https://github.com/libigl/libigl.git /opt/libigl \
 && rm -rf /opt/libigl/.git
COPY vc_obj_uv_lift.cpp /tmp/vc_obj_uv_lift.cpp
RUN g++ -O2 -std=c++17 -fopenmp \
        -I/opt/libigl/include -I/usr/include/eigen3 \
        /tmp/vc_obj_uv_lift.cpp -o /usr/local/bin/vc_obj_uv_lift \
 && rm /tmp/vc_obj_uv_lift.cpp

# Fail at build time rather than halfway through a render.
RUN python3 -c "import torch, einops, scipy.ndimage, PIL, tifffile; print('render deps ok')" \
 && for b in vc_render_tifxyz vc_tifxyz_trim vc_tifxyz2obj vc_obj2tifxyz vc_obj_uv_lift flatboi; do \
      command -v $b >/dev/null || { echo "MISSING $b"; exit 1; }; done \
 && vc_obj_uv_lift 2>&1 | head -2 \
 && echo "native binaries ok"
