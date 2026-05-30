# Sprint Log: 2026-03-22_sprint_000 (Pre-Shift Consolidation)
- **Consolidated**: All legacy individual logs from this session.

# Experiment Log: 2026-03-22_001
- **Tweak**: heads_64
- **Status**: REVERTED
- **Timestamp**: 20:58:35

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rn self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 1: heads_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 231, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_002
- **Tweak**: batch_size_10
- **Status**: REVERTED
- **Timestamp**: 20:58:48

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 10
- **patch_size**: 64

## Run Output (Tail)
```
ine 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 2: batch_size_10 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6307, in multi_head_attention_forward
    q, k, v = _in_projection_packed(query, key, value, in_proj_weight, in_proj_bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 5699, in _in_projection_packed
    proj = linear(q, w, b)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 480.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 62.00 MiB is free. Including non-PyTorch memory, this process has 23.44 GiB memory in use. Of the allocated memory 22.81 GiB is allocated by PyTorch, and 183.00 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_003
- **Tweak**: wd_0.005
- **Status**: REVERTED
- **Timestamp**: 20:59:00

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rn self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 3: wd_0.005 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_004
- **Tweak**: base_feat_512
- **Status**: REVERTED
- **Timestamp**: 20:59:13

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 4: base_feat_512 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 384.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 48.00 MiB is free. Including non-PyTorch memory, this process has 23.45 GiB memory in use. Of the allocated memory 22.71 GiB is allocated by PyTorch, and 309.33 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_005
- **Tweak**: dropout_0.1
- **Status**: REVERTED
- **Timestamp**: 20:59:25

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
elf._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 5: dropout_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 188.00 MiB is free. Including non-PyTorch memory, this process has 23.31 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 195.61 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_006
- **Tweak**: patch_size_48
- **Status**: REVERTED
- **Timestamp**: 20:59:36

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 48

## Run Output (Tail)
```
s)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 7: patch_size_48 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Step 0000 | Loss: 2.367441 | dt: 1554ms | Remaining: 298s
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 134, in train
    total_loss.backward()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/_tensor.py", line 625, in backward
    torch.autograd.backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/__init__.py", line 354, in backward
    _engine_run_backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/graph.py", line 841, in _engine_run_backward
    return Variable._execution_engine.run_backward(  # Calls into the C++ engine to run the backward pass
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1.69 GiB. GPU 0 has a total capacity of 23.52 GiB of which 514.00 MiB is free. Including non-PyTorch memory, this process has 22.99 GiB memory in use. Of the allocated memory 20.92 GiB is allocated by PyTorch, and 1.62 GiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_007
- **Tweak**: lr_5e-4
- **Status**: REVERTED
- **Timestamp**: 20:59:49

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
s/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 8: lr_5e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_008
- **Tweak**: blocks_18
- **Status**: REVERTED
- **Timestamp**: 21:00:03

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 9: blocks_18 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_009
- **Tweak**: dropout_0.1
- **Status**: REVERTED
- **Timestamp**: 21:00:14

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
lf._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 11: dropout_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 188.00 MiB is free. Including non-PyTorch memory, this process has 23.31 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 195.61 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_010
- **Tweak**: batch_size_10
- **Status**: REVERTED
- **Timestamp**: 21:00:24

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 10
- **patch_size**: 64

## Run Output (Tail)
```
ne 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 12: batch_size_10 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6307, in multi_head_attention_forward
    q, k, v = _in_projection_packed(query, key, value, in_proj_weight, in_proj_bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 5699, in _in_projection_packed
    proj = linear(q, w, b)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 480.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 62.00 MiB is free. Including non-PyTorch memory, this process has 23.44 GiB memory in use. Of the allocated memory 22.81 GiB is allocated by PyTorch, and 183.00 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_011
- **Tweak**: wd_0.0
- **Status**: REVERTED
- **Timestamp**: 21:00:37

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
urn self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 13: wd_0.0 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_012
- **Tweak**: heads_32
- **Status**: REVERTED
- **Timestamp**: 21:00:47

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 14: heads_32 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_013
- **Tweak**: base_feat_256
- **Status**: REVERTED
- **Timestamp**: 21:00:57

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
5, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 15: base_feat_256 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6450, in multi_head_attention_forward
    attn_output_weights = torch.bmm(q_scaled, k.transpose(-2, -1))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 768.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 614.00 MiB is free. Including non-PyTorch memory, this process has 22.90 GiB memory in use. Of the allocated memory 21.91 GiB is allocated by PyTorch, and 554.26 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_014
- **Tweak**: blocks_18
- **Status**: REVERTED
- **Timestamp**: 21:01:08

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
odule.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 16: blocks_18 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_015
- **Tweak**: patch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:06:22

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 32

## Run Output (Tail)
```
: 206ms | Remaining: 114s
Step 0600 | Loss: 0.077211 | dt: 206ms | Remaining: 112s
Step 0605 | Loss: 0.070051 | dt: 206ms | Remaining: 111s
Step 0610 | Loss: 0.088597 | dt: 206ms | Remaining: 109s
Step 0615 | Loss: 0.901145 | dt: 206ms | Remaining: 108s
Step 0620 | Loss: 0.824557 | dt: 208ms | Remaining: 106s
Step 0625 | Loss: 0.528332 | dt: 208ms | Remaining: 105s
Step 0630 | Loss: 0.352952 | dt: 207ms | Remaining: 104s
Step 0635 | Loss: 0.241402 | dt: 210ms | Remaining: 103s
Step 0640 | Loss: 0.189907 | dt: 495ms | Remaining: 102s
Step 0645 | Loss: 0.152084 | dt: 206ms | Remaining: 101s
Step 0650 | Loss: 0.153525 | dt: 1652ms | Remaining: 98s
Step 0655 | Loss: 0.202038 | dt: 211ms | Remaining: 97s
Step 0660 | Loss: 0.192156 | dt: 204ms | Remaining: 96s
Step 0665 | Loss: 0.185486 | dt: 207ms | Remaining: 89s
Step 0670 | Loss: 0.653626 | dt: 210ms | Remaining: 88s
Step 0675 | Loss: 0.451838 | dt: 208ms | Remaining: 87s
Step 0680 | Loss: 0.326459 | dt: 206ms | Remaining: 86s
Step 0685 | Loss: 0.239380 | dt: 206ms | Remaining: 84s
Step 0690 | Loss: 0.186063 | dt: 208ms | Remaining: 83s
Step 0695 | Loss: 0.156999 | dt: 206ms | Remaining: 80s
Step 0700 | Loss: 0.145438 | dt: 208ms | Remaining: 79s
Step 0705 | Loss: 0.204050 | dt: 208ms | Remaining: 76s
Step 0710 | Loss: 0.193753 | dt: 206ms | Remaining: 75s
Step 0715 | Loss: 0.182565 | dt: 215ms | Remaining: 73s
Step 0720 | Loss: 0.160667 | dt: 206ms | Remaining: 72s
Step 0725 | Loss: 0.144599 | dt: 497ms | Remaining: 70s
Step 0730 | Loss: 0.120609 | dt: 207ms | Remaining: 69s
Step 0735 | Loss: 0.107900 | dt: 229ms | Remaining: 68s
Step 0740 | Loss: 0.097393 | dt: 206ms | Remaining: 67s
Step 0745 | Loss: 0.092315 | dt: 209ms | Remaining: 66s
Step 0750 | Loss: 0.116594 | dt: 207ms | Remaining: 63s
Step 0755 | Loss: 0.144450 | dt: 207ms | Remaining: 62s
Step 0760 | Loss: 0.130295 | dt: 205ms | Remaining: 61s
Step 0765 | Loss: 0.108216 | dt: 207ms | Remaining: 60s
Step 0770 | Loss: 0.101692 | dt: 207ms | Remaining: 58s
Step 0775 | Loss: 0.093584 | dt: 206ms | Remaining: 57s
Step 0780 | Loss: 0.167442 | dt: 204ms | Remaining: 56s
Step 0785 | Loss: 0.358791 | dt: 211ms | Remaining: 55s
Step 0790 | Loss: 0.293934 | dt: 211ms | Remaining: 52s
Step 0795 | Loss: 0.278617 | dt: 206ms | Remaining: 51s
Step 0800 | Loss: 0.276986 | dt: 1578ms | Remaining: 49s
Step 0805 | Loss: 0.232129 | dt: 206ms | Remaining: 47s
Step 0810 | Loss: 0.202018 | dt: 1410ms | Remaining: 45s
Step 0815 | Loss: 0.178102 | dt: 205ms | Remaining: 44s
Step 0820 | Loss: 0.153170 | dt: 207ms | Remaining: 43s
Step 0825 | Loss: 0.145352 | dt: 208ms | Remaining: 41s
Step 0830 | Loss: 0.144365 | dt: 205ms | Remaining: 40s
Step 0835 | Loss: 0.159436 | dt: 206ms | Remaining: 37s
Step 0840 | Loss: 0.144409 | dt: 211ms | Remaining: 36s
Step 0845 | Loss: 0.132454 | dt: 212ms | Remaining: 29s
Step 0850 | Loss: 0.124417 | dt: 214ms | Remaining: 28s
Step 0855 | Loss: 0.120535 | dt: 205ms | Remaining: 24s
Step 0860 | Loss: 0.119603 | dt: 208ms | Remaining: 23s
Step 0865 | Loss: 0.118680 | dt: 212ms | Remaining: 21s
Step 0870 | Loss: 0.111338 | dt: 205ms | Remaining: 20s
Step 0875 | Loss: 0.109002 | dt: 224ms | Remaining: 17s
Step 0880 | Loss: 0.106567 | dt: 346ms | Remaining: 16s
Step 0885 | Loss: 0.102910 | dt: 1585ms | Remaining: 13s
Step 0890 | Loss: 0.102373 | dt: 229ms | Remaining: 12s
Step 0895 | Loss: 0.099545 | dt: 205ms | Remaining: 11s
Step 0900 | Loss: 0.105571 | dt: 226ms | Remaining: 9s
Step 0905 | Loss: 0.102600 | dt: 283ms | Remaining: 7s
Step 0910 | Loss: 0.099315 | dt: 227ms | Remaining: 6s
Step 0915 | Loss: 0.092684 | dt: 227ms | Remaining: 5s
Step 0920 | Loss: 0.099306 | dt: 227ms | Remaining: 2s
Step 0925 | Loss: 0.116760 | dt: 225ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.019913
train_loss:       0.116972
training_seconds: 302.3
total_seconds:    304.0
peak_vram_mb:     10263.5
num_steps:        929
num_params_M:     2.262
throughput_Mvps:  0.60
Updated progress.png

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Experiment Log: 2026-03-22_016
- **Tweak**: lr_1e-4
- **Status**: REVERTED
- **Timestamp**: 21:06:33

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
f.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 18: lr_1e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 98.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.20 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 142.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_017
- **Tweak**: lr_5e-5
- **Status**: REVERTED
- **Timestamp**: 21:06:44

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
f.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 19: lr_5e-5 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 98.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.20 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 142.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_018
- **Tweak**: heads_32
- **Status**: REVERTED
- **Timestamp**: 21:06:58

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ll_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 21: heads_32 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 76.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.22 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 161.71 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_019
- **Tweak**: blocks_18
- **Status**: REVERTED
- **Timestamp**: 21:07:09

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 22: blocks_18 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 78.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_020
- **Tweak**: batch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:07:24

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 32
- **patch_size**: 64

## Run Output (Tail)
```
d_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 23: batch_size_32 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 128.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 118.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.18 GiB memory in use. Of the allocated memory 11.66 GiB is allocated by PyTorch, and 76.87 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_021
- **Tweak**: patch_size_64
- **Status**: REVERTED
- **Timestamp**: 21:07:36

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 24: patch_size_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 78.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_022
- **Tweak**: dropout_0.1
- **Status**: REVERTED
- **Timestamp**: 21:07:48

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ror: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 25: dropout_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 102.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.19 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 138.73 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_023
- **Tweak**: base_feat_256
- **Status**: REVERTED
- **Timestamp**: 21:08:02

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
  return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 26: base_feat_256 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 178.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.12 GiB memory in use. Of the allocated memory 11.58 GiB is allocated by PyTorch, and 97.26 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_024
- **Tweak**: wd_0.1
- **Status**: REVERTED
- **Timestamp**: 21:08:18

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
lf.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 27: wd_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 78.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_025
- **Tweak**: wd_0.1
- **Status**: REVERTED
- **Timestamp**: 21:08:31

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
lf.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 28: wd_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 98.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.20 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 142.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_026
- **Tweak**: blocks_14
- **Status**: REVERTED
- **Timestamp**: 21:08:44

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 29: blocks_14 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 112.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.18 GiB memory in use. Of the allocated memory 11.60 GiB is allocated by PyTorch, and 130.63 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_027
- **Tweak**: base_feat_128
- **Status**: REVERTED
- **Timestamp**: 21:08:58

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
l_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 30: base_feat_128 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6450, in multi_head_attention_forward
    attn_output_weights = torch.bmm(q_scaled, k.transpose(-2, -1))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 768.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 666.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 11.64 GiB memory in use. Of the allocated memory 10.93 GiB is allocated by PyTorch, and 269.94 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_028
- **Tweak**: lr_1e-4
- **Status**: REVERTED
- **Timestamp**: 21:09:13

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
f.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 31: lr_1e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 78.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_029
- **Tweak**: heads_4
- **Status**: REVERTED
- **Timestamp**: 21:09:28

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 32: heads_4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 48.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.24 GiB memory in use. Of the allocated memory 11.65 GiB is allocated by PyTorch, and 144.71 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_030
- **Tweak**: batch_size_16
- **Status**: REVERTED
- **Timestamp**: 21:09:44

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 16
- **patch_size**: 64

## Run Output (Tail)
```
l
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 34: batch_size_16 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 256.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 216.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.08 GiB memory in use. Of the allocated memory 11.47 GiB is allocated by PyTorch, and 160.92 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_031
- **Tweak**: dropout_0.3
- **Status**: REVERTED
- **Timestamp**: 21:10:00

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rror: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 35: dropout_0.3 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 82.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 155.73 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_032
- **Tweak**: patch_size_64
- **Status**: REVERTED
- **Timestamp**: 21:10:16

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 36: patch_size_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 78.69 MiB is free. Process 2213105 has 11.20 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_033
- **Tweak**: wd_0.005
- **Status**: REVERTED
- **Timestamp**: 21:10:27

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 37: wd_0.005 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 64.69 MiB is free. Process 2213105 has 11.21 GiB memory in use. Including non-PyTorch memory, this process has 12.21 GiB memory in use. Of the allocated memory 11.61 GiB is allocated by PyTorch, and 159.72 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_034
- **Tweak**: heads_64
- **Status**: REVERTED
- **Timestamp**: 21:10:42

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 38: heads_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_035
- **Tweak**: batch_size_16
- **Status**: REVERTED
- **Timestamp**: 21:10:52

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 16
- **patch_size**: 64

## Run Output (Tail)
```
e.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 39: batch_size_16 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 256.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 140.00 MiB is free. Including non-PyTorch memory, this process has 23.36 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 190.80 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_036
- **Tweak**: lr_1e-4
- **Status**: REVERTED
- **Timestamp**: 21:11:05

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rn self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 40: lr_1e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_037
- **Tweak**: base_feat_64
- **Status**: REVERTED
- **Timestamp**: 21:11:18

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
lf._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 41: base_feat_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_038
- **Tweak**: dropout_0.15
- **Status**: REVERTED
- **Timestamp**: 21:11:29

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
f._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 42: dropout_0.15 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 188.00 MiB is free. Including non-PyTorch memory, this process has 23.31 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 195.61 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_039
- **Tweak**: blocks_14
- **Status**: REVERTED
- **Timestamp**: 21:11:41

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
y", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 43: blocks_14 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6450, in multi_head_attention_forward
    attn_output_weights = torch.bmm(q_scaled, k.transpose(-2, -1))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 3.00 GiB. GPU 0 has a total capacity of 23.52 GiB of which 32.00 MiB is free. Including non-PyTorch memory, this process has 23.46 GiB memory in use. Of the allocated memory 22.49 GiB is allocated by PyTorch, and 542.53 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_040
- **Tweak**: patch_size_48
- **Status**: REVERTED
- **Timestamp**: 21:11:52

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 48

## Run Output (Tail)
```
)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 45: patch_size_48 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Step 0000 | Loss: 1.405457 | dt: 1542ms | Remaining: 298s
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 134, in train
    total_loss.backward()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/_tensor.py", line 625, in backward
    torch.autograd.backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/__init__.py", line 354, in backward
    _engine_run_backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/graph.py", line 841, in _engine_run_backward
    return Variable._execution_engine.run_backward(  # Calls into the C++ engine to run the backward pass
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1.69 GiB. GPU 0 has a total capacity of 23.52 GiB of which 514.00 MiB is free. Including non-PyTorch memory, this process has 22.99 GiB memory in use. Of the allocated memory 20.92 GiB is allocated by PyTorch, and 1.62 GiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Experiment Log: 2026-03-22_041
- **Tweak**: patch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:17:04

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 32

## Run Output (Tail)
```
9383 | dt: 207ms | Remaining: 104s
Step 0650 | Loss: 0.279770 | dt: 1496ms | Remaining: 102s
Step 0655 | Loss: 0.316147 | dt: 204ms | Remaining: 101s
Step 0660 | Loss: 0.494790 | dt: 209ms | Remaining: 100s
Step 0665 | Loss: 0.658995 | dt: 209ms | Remaining: 97s
Step 0670 | Loss: 0.630252 | dt: 203ms | Remaining: 96s
Step 0675 | Loss: 0.438493 | dt: 204ms | Remaining: 95s
Step 0680 | Loss: 0.302028 | dt: 204ms | Remaining: 94s
Step 0685 | Loss: 0.215551 | dt: 209ms | Remaining: 93s
Step 0690 | Loss: 0.159114 | dt: 203ms | Remaining: 92s
Step 0695 | Loss: 0.120986 | dt: 205ms | Remaining: 90s
Step 0700 | Loss: 0.102677 | dt: 204ms | Remaining: 89s
Step 0705 | Loss: 0.220854 | dt: 205ms | Remaining: 86s
Step 0710 | Loss: 0.274266 | dt: 203ms | Remaining: 85s
Step 0715 | Loss: 0.246109 | dt: 203ms | Remaining: 84s
Step 0720 | Loss: 0.168912 | dt: 206ms | Remaining: 83s
Step 0725 | Loss: 0.122597 | dt: 1353ms | Remaining: 81s
Step 0730 | Loss: 0.119020 | dt: 205ms | Remaining: 80s
Step 0735 | Loss: 0.107400 | dt: 204ms | Remaining: 79s
Step 0740 | Loss: 0.100813 | dt: 203ms | Remaining: 77s
Step 0745 | Loss: 0.108380 | dt: 205ms | Remaining: 75s
Step 0750 | Loss: 0.101761 | dt: 207ms | Remaining: 73s
Step 0755 | Loss: 0.091585 | dt: 204ms | Remaining: 72s
Step 0760 | Loss: 0.080302 | dt: 203ms | Remaining: 71s
Step 0765 | Loss: 0.070533 | dt: 206ms | Remaining: 70s
Step 0770 | Loss: 0.064806 | dt: 205ms | Remaining: 69s
Step 0775 | Loss: 0.059904 | dt: 204ms | Remaining: 68s
Step 0780 | Loss: 0.055122 | dt: 205ms | Remaining: 65s
Step 0785 | Loss: 0.052666 | dt: 203ms | Remaining: 64s
Step 0790 | Loss: 0.049512 | dt: 207ms | Remaining: 62s
Step 0795 | Loss: 0.051113 | dt: 205ms | Remaining: 61s
Step 0800 | Loss: 0.059979 | dt: 1978ms | Remaining: 59s
Step 0805 | Loss: 0.094161 | dt: 205ms | Remaining: 58s
Step 0810 | Loss: 0.091606 | dt: 1387ms | Remaining: 55s
Step 0815 | Loss: 0.082710 | dt: 203ms | Remaining: 54s
Step 0820 | Loss: 0.078724 | dt: 204ms | Remaining: 53s
Step 0825 | Loss: 0.074403 | dt: 208ms | Remaining: 51s
Step 0830 | Loss: 0.072516 | dt: 203ms | Remaining: 50s
Step 0835 | Loss: 0.072773 | dt: 204ms | Remaining: 44s
Step 0840 | Loss: 0.083336 | dt: 207ms | Remaining: 42s
Step 0845 | Loss: 0.095505 | dt: 203ms | Remaining: 38s
Step 0850 | Loss: 0.098669 | dt: 220ms | Remaining: 37s
Step 0855 | Loss: 0.092186 | dt: 206ms | Remaining: 36s
Step 0860 | Loss: 0.079004 | dt: 206ms | Remaining: 35s
Step 0865 | Loss: 0.089707 | dt: 213ms | Remaining: 32s
Step 0870 | Loss: 0.094818 | dt: 219ms | Remaining: 31s
Step 0875 | Loss: 0.094188 | dt: 203ms | Remaining: 29s
Step 0880 | Loss: 0.081171 | dt: 204ms | Remaining: 28s
Step 0885 | Loss: 0.069020 | dt: 499ms | Remaining: 27s
Step 0890 | Loss: 0.063907 | dt: 203ms | Remaining: 26s
Step 0895 | Loss: 0.061628 | dt: 207ms | Remaining: 25s
Step 0900 | Loss: 0.077751 | dt: 203ms | Remaining: 22s
Step 0905 | Loss: 0.090983 | dt: 204ms | Remaining: 21s
Step 0910 | Loss: 0.141843 | dt: 211ms | Remaining: 18s
Step 0915 | Loss: 0.145582 | dt: 205ms | Remaining: 17s
Step 0920 | Loss: 0.124853 | dt: 210ms | Remaining: 16s
Step 0925 | Loss: 0.115189 | dt: 203ms | Remaining: 15s
Step 0930 | Loss: 0.630613 | dt: 204ms | Remaining: 12s
Step 0935 | Loss: 0.444831 | dt: 203ms | Remaining: 11s
Step 0940 | Loss: 0.340948 | dt: 203ms | Remaining: 8s
Step 0945 | Loss: 0.283368 | dt: 204ms | Remaining: 7s
Step 0950 | Loss: 0.212698 | dt: 206ms | Remaining: 6s
Step 0955 | Loss: 0.150134 | dt: 204ms | Remaining: 5s
Step 0960 | Loss: 0.110568 | dt: 516ms | Remaining: 3s
Step 0965 | Loss: 0.085104 | dt: 205ms | Remaining: 2s
Step 0970 | Loss: 0.070078 | dt: 516ms | Remaining: 1s
Step 0975 | Loss: 0.062132 | dt: 204ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.018463
train_loss:       0.062132
training_seconds: 300.1
total_seconds:    301.9
peak_vram_mb:     10263.5
num_steps:        976
num_params_M:     2.262
throughput_Mvps:  0.64
Updated progress.png

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Experiment Log: 2026-03-22_042
- **Tweak**: blocks_16
- **Status**: REVERTED
- **Timestamp**: 21:17:16

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- CYCLE 47: blocks_16 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 192.00 MiB is free. Including non-PyTorch memory, this process has 23.31 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 192.56 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_043
- **Tweak**: base_feat_512
- **Status**: REVERTED
- **Timestamp**: 21:20:45

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
ss: 0.014092 | dt: 434ms | Remaining: 148s
Step 0295 | Loss: 0.082230 | dt: 436ms | Remaining: 146s
Step 0300 | Loss: 0.074930 | dt: 447ms | Remaining: 141s
Step 0305 | Loss: 0.072098 | dt: 439ms | Remaining: 139s
Step 0310 | Loss: 0.058539 | dt: 439ms | Remaining: 137s
Step 0315 | Loss: 0.044737 | dt: 437ms | Remaining: 135s
Step 0320 | Loss: 0.033645 | dt: 2679ms | Remaining: 130s
Step 0325 | Loss: 0.026421 | dt: 446ms | Remaining: 128s
Step 0330 | Loss: 0.021441 | dt: 437ms | Remaining: 126s
Step 0335 | Loss: 0.018757 | dt: 452ms | Remaining: 124s
Step 0340 | Loss: 0.015510 | dt: 447ms | Remaining: 121s
Step 0345 | Loss: 0.017051 | dt: 459ms | Remaining: 116s
Step 0350 | Loss: 0.017570 | dt: 440ms | Remaining: 114s
Step 0355 | Loss: 0.020333 | dt: 439ms | Remaining: 111s
Step 0360 | Loss: 0.020246 | dt: 434ms | Remaining: 109s
Step 0365 | Loss: 0.017170 | dt: 447ms | Remaining: 106s
Step 0370 | Loss: 0.013334 | dt: 435ms | Remaining: 104s
Step 0375 | Loss: 0.011184 | dt: 448ms | Remaining: 102s


--- NIGHT SHIFT CYCLE 1: base_feat_512 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 63, in forward
    feat_half = self._extract_features(x_half)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6307, in multi_head_attention_forward
    q, k, v = _in_projection_packed(query, key, value, in_proj_weight, in_proj_bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 5706, in _in_projection_packed
    .contiguous()
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 576.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 342.00 MiB is free. Including non-PyTorch memory, this process has 23.16 GiB memory in use. Of the allocated memory 22.15 GiB is allocated by PyTorch, and 580.88 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_044
- **Tweak**: heads_4
- **Status**: REVERTED
- **Timestamp**: 21:20:58

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 2: heads_4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 134.00 MiB is free. Including non-PyTorch memory, this process has 23.37 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 201.59 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_045
- **Tweak**: dropout_0.4
- **Status**: REVERTED
- **Timestamp**: 21:21:10

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 3: dropout_0.4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 188.00 MiB is free. Including non-PyTorch memory, this process has 23.31 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 195.61 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_046
- **Tweak**: blocks_8
- **Status**: REVERTED
- **Timestamp**: 21:21:20

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
y", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 4: blocks_8 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 125, in train
    _, feat_teacher, _, _, _, _ = model(x_aug, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6450, in multi_head_attention_forward
    attn_output_weights = torch.bmm(q_scaled, k.transpose(-2, -1))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 3.00 GiB. GPU 0 has a total capacity of 23.52 GiB of which 2.50 GiB is free. Including non-PyTorch memory, this process has 21.00 GiB memory in use. Of the allocated memory 18.18 GiB is allocated by PyTorch, and 2.37 GiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_047
- **Tweak**: lr_5e-5
- **Status**: REVERTED
- **Timestamp**: 21:21:37

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
, line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 5: lr_5e-5 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_048
- **Tweak**: batch_size_16
- **Status**: REVERTED
- **Timestamp**: 21:21:50

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 16
- **patch_size**: 64

## Run Output (Tail)
```
 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 6: batch_size_16 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 256.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 140.00 MiB is free. Including non-PyTorch memory, this process has 23.36 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 194.80 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_049
- **Tweak**: wd_0.005
- **Status**: REVERTED
- **Timestamp**: 21:22:03

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
v_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 8: wd_0.005 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_050
- **Tweak**: patch_size_64
- **Status**: REVERTED
- **Timestamp**: 21:22:14

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 9: patch_size_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_051
- **Tweak**: heads_4
- **Status**: REVERTED
- **Timestamp**: 21:22:26

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
les/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 10: heads_4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 134.00 MiB is free. Including non-PyTorch memory, this process has 23.37 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 201.59 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_052
- **Tweak**: base_feat_128
- **Status**: REVERTED
- **Timestamp**: 21:22:39

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
urn F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 11: base_feat_128 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 384.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 6.00 MiB is free. Including non-PyTorch memory, this process has 23.49 GiB memory in use. Of the allocated memory 22.84 GiB is allocated by PyTorch, and 207.84 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_053
- **Tweak**: wd_0.0
- **Status**: REVERTED
- **Timestamp**: 21:22:50

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
nv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 12: wd_0.0 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_054
- **Tweak**: lr_5e-4
- **Status**: REVERTED
- **Timestamp**: 21:23:00

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
 line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 13: lr_5e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_055
- **Tweak**: patch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:23:13

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 32

## Run Output (Tail)
```
.120065 | dt: 205ms | Remaining: 100s
Step 0615 | Loss: 0.114908 | dt: 209ms | Remaining: 99s
Step 0620 | Loss: 0.220104 | dt: 205ms | Remaining: 96s
Step 0625 | Loss: 0.252066 | dt: 204ms | Remaining: 95s
Step 0630 | Loss: 0.257011 | dt: 204ms | Remaining: 93s
Step 0635 | Loss: 0.216027 | dt: 203ms | Remaining: 92s
Step 0640 | Loss: 0.187289 | dt: 502ms | Remaining: 91s
Step 0645 | Loss: 0.145481 | dt: 203ms | Remaining: 90s
Step 0650 | Loss: 0.118334 | dt: 527ms | Remaining: 88s
Step 0655 | Loss: 0.100770 | dt: 212ms | Remaining: 87s
Step 0660 | Loss: 0.089811 | dt: 204ms | Remaining: 86s
Step 0665 | Loss: 0.086761 | dt: 203ms | Remaining: 85s
Step 0670 | Loss: 0.077014 | dt: 205ms | Remaining: 84s
Step 0675 | Loss: 0.071757 | dt: 203ms | Remaining: 83s
Step 0680 | Loss: 0.071616 | dt: 205ms | Remaining: 82s
Step 0685 | Loss: 0.186253 | dt: 204ms | Remaining: 79s
Step 0690 | Loss: 0.347632 | dt: 207ms | Remaining: 78s
Step 0695 | Loss: 1.325266 | dt: 204ms | Remaining: 76s
Step 0700 | Loss: 0.989172 | dt: 203ms | Remaining: 75s
Step 0705 | Loss: 0.737423 | dt: 206ms | Remaining: 72s
Step 0710 | Loss: 0.553436 | dt: 205ms | Remaining: 71s
Step 0715 | Loss: 0.418552 | dt: 204ms | Remaining: 70s
Step 0720 | Loss: 0.309682 | dt: 205ms | Remaining: 68s
Step 0725 | Loss: 0.256524 | dt: 1772ms | Remaining: 66s
Step 0730 | Loss: 0.506288 | dt: 204ms | Remaining: 65s
Step 0735 | Loss: 0.510028 | dt: 204ms | Remaining: 64s
Step 0740 | Loss: 0.372309 | dt: 206ms | Remaining: 63s
Step 0745 | Loss: 0.277632 | dt: 208ms | Remaining: 61s
Step 0750 | Loss: 0.440393 | dt: 204ms | Remaining: 59s
Step 0755 | Loss: 0.459036 | dt: 207ms | Remaining: 58s
Step 0760 | Loss: 0.369755 | dt: 204ms | Remaining: 56s
Step 0765 | Loss: 0.308107 | dt: 204ms | Remaining: 55s
Step 0770 | Loss: 0.258628 | dt: 203ms | Remaining: 52s
Step 0775 | Loss: 0.217462 | dt: 204ms | Remaining: 51s
Step 0780 | Loss: 0.183413 | dt: 206ms | Remaining: 50s
Step 0785 | Loss: 0.146912 | dt: 203ms | Remaining: 49s
Step 0790 | Loss: 0.135507 | dt: 203ms | Remaining: 46s
Step 0795 | Loss: 0.149685 | dt: 204ms | Remaining: 45s
Step 0800 | Loss: 0.158562 | dt: 5862ms | Remaining: 39s
Step 0805 | Loss: 0.163073 | dt: 206ms | Remaining: 38s
Step 0810 | Loss: 0.174810 | dt: 845ms | Remaining: 36s
Step 0815 | Loss: 0.144673 | dt: 204ms | Remaining: 35s
Step 0820 | Loss: 0.141276 | dt: 204ms | Remaining: 34s
Step 0825 | Loss: 0.153031 | dt: 204ms | Remaining: 31s
Step 0830 | Loss: 0.150813 | dt: 205ms | Remaining: 30s
Step 0835 | Loss: 0.131147 | dt: 203ms | Remaining: 29s
Step 0840 | Loss: 0.126992 | dt: 204ms | Remaining: 28s
Step 0845 | Loss: 0.123795 | dt: 206ms | Remaining: 26s
Step 0850 | Loss: 0.131717 | dt: 203ms | Remaining: 25s
Step 0855 | Loss: 0.141514 | dt: 203ms | Remaining: 23s
Step 0860 | Loss: 0.135142 | dt: 208ms | Remaining: 22s
Step 0865 | Loss: 0.123560 | dt: 203ms | Remaining: 21s
Step 0870 | Loss: 0.121079 | dt: 203ms | Remaining: 20s
Step 0875 | Loss: 0.144063 | dt: 207ms | Remaining: 18s
Step 0880 | Loss: 0.222722 | dt: 203ms | Remaining: 17s
Step 0885 | Loss: 0.200219 | dt: 1019ms | Remaining: 15s
Step 0890 | Loss: 0.183481 | dt: 207ms | Remaining: 14s
Step 0895 | Loss: 0.172262 | dt: 203ms | Remaining: 13s
Step 0900 | Loss: 0.145360 | dt: 206ms | Remaining: 11s
Step 0905 | Loss: 0.119860 | dt: 207ms | Remaining: 10s
Step 0910 | Loss: 0.106489 | dt: 204ms | Remaining: 8s
Step 0915 | Loss: 0.093147 | dt: 205ms | Remaining: 7s
Step 0920 | Loss: 0.103859 | dt: 206ms | Remaining: 5s
Step 0925 | Loss: 0.109759 | dt: 203ms | Remaining: 4s
Step 0930 | Loss: 0.101917 | dt: 203ms | Remaining: 3s
Step 0935 | Loss: 0.089864 | dt: 206ms | Remaining: 1s
Step 0940 | Loss: 0.085370 | dt: 204ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.016385
train_loss:       0.085370
training_seconds: 300.1
total_seconds:    301.9
peak_vram_mb:     10263.5
num_steps:        941
num_params_M:     2.262
throughput_Mvps:  0.62
Updated progress.png

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_056
- **Tweak**: dropout_0.0
- **Status**: REVERTED
- **Timestamp**: 21:28:24

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
e 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 16: dropout_0.0 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_057
- **Tweak**: batch_size_12
- **Status**: REVERTED
- **Timestamp**: 21:28:37

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
ard(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 17: batch_size_12 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_058
- **Tweak**: blocks_24
- **Status**: REVERTED
- **Timestamp**: 21:28:50

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
s/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 18: blocks_24 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.73 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_059
- **Tweak**: base_feat_64
- **Status**: REVERTED
- **Timestamp**: 21:29:03

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 19: base_feat_64 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_060
- **Tweak**: blocks_10
- **Status**: REVERTED
- **Timestamp**: 21:29:16

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
rch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 20: blocks_10 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6451, in multi_head_attention_forward
    attn_output_weights = softmax(attn_output_weights, dim=-1)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2133, in softmax
    ret = input.softmax(dim)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 3.00 GiB. GPU 0 has a total capacity of 23.52 GiB of which 2.67 GiB is free. Including non-PyTorch memory, this process has 20.83 GiB memory in use. Of the allocated memory 19.86 GiB is allocated by PyTorch, and 527.50 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_061
- **Tweak**: heads_12
- **Status**: REVERTED
- **Timestamp**: 21:29:27

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
croll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 21: heads_12 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 66, in train
    model = InkDetectorOptimized(v_config, base_feat=64, num_blocks=18).to(device)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 31, in __init__
    self.attn = nn.MultiheadAttention(base_feat, num_heads=12, batch_first=True, dropout=0.0)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1188, in __init__
    assert self.head_dim * num_heads == self.embed_dim, (
AssertionError: embed_dim must be divisible by num_heads

```

---

# Night Shift Log: 2026-03-22_062
- **Tweak**: patch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:29:35

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 32

## Run Output (Tail)
```
 | dt: 205ms | Remaining: 107s
Step 0600 | Loss: 0.236320 | dt: 207ms | Remaining: 105s
Step 0605 | Loss: 0.211508 | dt: 207ms | Remaining: 104s
Step 0610 | Loss: 0.202564 | dt: 204ms | Remaining: 102s
Step 0615 | Loss: 0.196373 | dt: 205ms | Remaining: 101s
Step 0620 | Loss: 0.170958 | dt: 203ms | Remaining: 100s
Step 0625 | Loss: 0.164919 | dt: 204ms | Remaining: 99s
Step 0630 | Loss: 0.150118 | dt: 205ms | Remaining: 97s
Step 0635 | Loss: 0.141812 | dt: 203ms | Remaining: 96s
Step 0640 | Loss: 0.320011 | dt: 1803ms | Remaining: 94s
Step 0645 | Loss: 0.444268 | dt: 204ms | Remaining: 93s
Step 0650 | Loss: 0.377616 | dt: 5466ms | Remaining: 86s
Step 0655 | Loss: 0.346050 | dt: 203ms | Remaining: 85s
Step 0660 | Loss: 0.290866 | dt: 203ms | Remaining: 84s
Step 0665 | Loss: 0.223541 | dt: 203ms | Remaining: 83s
Step 0670 | Loss: 0.190413 | dt: 206ms | Remaining: 82s
Step 0675 | Loss: 0.188366 | dt: 203ms | Remaining: 79s
Step 0680 | Loss: 0.189859 | dt: 203ms | Remaining: 78s
Step 0685 | Loss: 0.194775 | dt: 204ms | Remaining: 75s
Step 0690 | Loss: 0.198584 | dt: 204ms | Remaining: 74s
Step 0695 | Loss: 0.171820 | dt: 203ms | Remaining: 73s
Step 0700 | Loss: 0.147957 | dt: 203ms | Remaining: 72s
Step 0705 | Loss: 0.140934 | dt: 205ms | Remaining: 69s
Step 0710 | Loss: 0.149915 | dt: 203ms | Remaining: 68s
Step 0715 | Loss: 0.151397 | dt: 203ms | Remaining: 66s
Step 0720 | Loss: 0.146508 | dt: 204ms | Remaining: 65s
Step 0725 | Loss: 0.151586 | dt: 1663ms | Remaining: 63s
Step 0730 | Loss: 0.137408 | dt: 206ms | Remaining: 62s
Step 0735 | Loss: 0.129579 | dt: 204ms | Remaining: 61s
Step 0740 | Loss: 0.121294 | dt: 206ms | Remaining: 59s
Step 0745 | Loss: 0.118248 | dt: 204ms | Remaining: 58s
Step 0750 | Loss: 0.121552 | dt: 203ms | Remaining: 52s
Step 0755 | Loss: 0.126494 | dt: 204ms | Remaining: 51s
Step 0760 | Loss: 0.125263 | dt: 205ms | Remaining: 49s
Step 0765 | Loss: 0.115119 | dt: 203ms | Remaining: 48s
Step 0770 | Loss: 0.115999 | dt: 206ms | Remaining: 47s
Step 0775 | Loss: 0.113111 | dt: 208ms | Remaining: 46s
Step 0780 | Loss: 0.115468 | dt: 204ms | Remaining: 42s
Step 0785 | Loss: 0.121483 | dt: 208ms | Remaining: 41s
Step 0790 | Loss: 0.122050 | dt: 204ms | Remaining: 40s
Step 0795 | Loss: 0.114469 | dt: 203ms | Remaining: 39s
Step 0800 | Loss: 0.111115 | dt: 528ms | Remaining: 37s
Step 0805 | Loss: 0.113110 | dt: 204ms | Remaining: 36s
Step 0810 | Loss: 0.114903 | dt: 1458ms | Remaining: 34s
Step 0815 | Loss: 0.137426 | dt: 204ms | Remaining: 33s
Step 0820 | Loss: 0.150580 | dt: 212ms | Remaining: 32s
Step 0825 | Loss: 0.138100 | dt: 204ms | Remaining: 31s
Step 0830 | Loss: 0.126416 | dt: 206ms | Remaining: 30s
Step 0835 | Loss: 0.118740 | dt: 203ms | Remaining: 28s
Step 0840 | Loss: 0.114890 | dt: 209ms | Remaining: 27s
Step 0845 | Loss: 0.137705 | dt: 205ms | Remaining: 24s
Step 0850 | Loss: 0.162977 | dt: 204ms | Remaining: 23s
Step 0855 | Loss: 0.171421 | dt: 204ms | Remaining: 21s
Step 0860 | Loss: 0.161109 | dt: 204ms | Remaining: 20s
Step 0865 | Loss: 0.169540 | dt: 204ms | Remaining: 17s
Step 0870 | Loss: 0.172916 | dt: 203ms | Remaining: 16s
Step 0875 | Loss: 0.167964 | dt: 203ms | Remaining: 14s
Step 0880 | Loss: 0.195261 | dt: 204ms | Remaining: 13s
Step 0885 | Loss: 0.182790 | dt: 1416ms | Remaining: 11s
Step 0890 | Loss: 0.194962 | dt: 203ms | Remaining: 10s
Step 0895 | Loss: 0.216994 | dt: 203ms | Remaining: 9s
Step 0900 | Loss: 0.179937 | dt: 204ms | Remaining: 7s
Step 0905 | Loss: 0.155666 | dt: 204ms | Remaining: 6s
Step 0910 | Loss: 0.136942 | dt: 205ms | Remaining: 5s
Step 0915 | Loss: 0.127397 | dt: 203ms | Remaining: 4s
Step 0920 | Loss: 0.178413 | dt: 207ms | Remaining: 1s
Step 0925 | Loss: 0.238286 | dt: 205ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.051902
train_loss:       0.239454
training_seconds: 300.1
total_seconds:    301.8
peak_vram_mb:     10263.5
num_steps:        927
num_params_M:     2.262
throughput_Mvps:  0.61
Updated progress.png

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_063
- **Tweak**: lr_1e-4
- **Status**: REVERTED
- **Timestamp**: 21:34:45

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
v_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 23: lr_1e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_064
- **Tweak**: wd_0.05
- **Status**: REVERTED
- **Timestamp**: 21:34:58

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
v_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 24: wd_0.05 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_065
- **Tweak**: batch_size_16
- **Status**: REVERTED
- **Timestamp**: 21:35:09

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 16
- **patch_size**: 64

## Run Output (Tail)
```
1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 26: batch_size_16 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 256.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 140.00 MiB is free. Including non-PyTorch memory, this process has 23.36 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 194.80 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_066
- **Tweak**: dropout_0.1
- **Status**: REVERTED
- **Timestamp**: 21:35:19

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
turn F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 27: dropout_0.1 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 16.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 178.61 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_067
- **Tweak**: wd_0.0
- **Status**: REVERTED
- **Timestamp**: 21:35:30

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
, line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 28: wd_0.0 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_068
- **Tweak**: lr_3e-4
- **Status**: REVERTED
- **Timestamp**: 21:35:41

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
v_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 29: lr_3e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_069
- **Tweak**: base_feat_128
- **Status**: REVERTED
- **Timestamp**: 21:35:51

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
urn F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 30: base_feat_128 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 124, in forward
    return self._apply_instance_norm(input)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/instancenorm.py", line 47, in _apply_instance_norm
    return F.instance_norm(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 2867, in instance_norm
    return torch.instance_norm(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 384.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 6.00 MiB is free. Including non-PyTorch memory, this process has 23.49 GiB memory in use. Of the allocated memory 22.84 GiB is allocated by PyTorch, and 207.84 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_070
- **Tweak**: dropout_0.0
- **Status**: REVERTED
- **Timestamp**: 21:36:02

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
e 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 31: dropout_0.0 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_071
- **Tweak**: batch_size_10
- **Status**: REVERTED
- **Timestamp**: 21:36:15

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 10
- **patch_size**: 64

## Run Output (Tail)
```
_call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 32: batch_size_10 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 95, in _extract_features
    x_attn, _ = self.attn(x_attn, x_attn, x_attn)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/activation.py", line 1488, in forward
    attn_output, attn_output_weights = F.multi_head_attention_forward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 6307, in multi_head_attention_forward
    q, k, v = _in_projection_packed(query, key, value, in_proj_weight, in_proj_bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/functional.py", line 5699, in _in_projection_packed
    proj = linear(q, w, b)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 480.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 62.00 MiB is free. Including non-PyTorch memory, this process has 23.44 GiB memory in use. Of the allocated memory 22.81 GiB is allocated by PyTorch, and 183.00 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_072
- **Tweak**: heads_4
- **Status**: REVERTED
- **Timestamp**: 21:36:27

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
les/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 33: heads_4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 134.00 MiB is free. Including non-PyTorch memory, this process has 23.37 GiB memory in use. Of the allocated memory 22.72 GiB is allocated by PyTorch, and 201.59 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_073
- **Tweak**: blocks_20
- **Status**: REVERTED
- **Timestamp**: 21:36:40

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
les/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 34: blocks_20 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 113, in forward
    return F.gelu(x + res)
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 6.00 MiB is free. Including non-PyTorch memory, this process has 23.49 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 187.64 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_074
- **Tweak**: patch_size_48
- **Status**: REVERTED
- **Timestamp**: 21:36:50

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 48

## Run Output (Tail)
```
ome/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 35: patch_size_48 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Step 0000 | Loss: 1.997043 | dt: 1527ms | Remaining: 298s
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 134, in train
    total_loss.backward()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/_tensor.py", line 625, in backward
    torch.autograd.backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/__init__.py", line 354, in backward
    _engine_run_backward(
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/autograd/graph.py", line 841, in _engine_run_backward
    return Variable._execution_engine.run_backward(  # Calls into the C++ engine to run the backward pass
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1.69 GiB. GPU 0 has a total capacity of 23.52 GiB of which 514.00 MiB is free. Including non-PyTorch memory, this process has 22.99 GiB memory in use. Of the allocated memory 20.92 GiB is allocated by PyTorch, and 1.62 GiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_075
- **Tweak**: lr_1e-4
- **Status**: REVERTED
- **Timestamp**: 21:37:01

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 12
- **patch_size**: 64

## Run Output (Tail)
```
 line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 112, in forward
    x = self.norm2(self.conv2(x))
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 717, in forward
    return self._conv_forward(input, self.weight, self.bias)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/conv.py", line 712, in _conv_forward
    return F.conv3d(
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 12.00 MiB is free. Including non-PyTorch memory, this process has 23.48 GiB memory in use. Of the allocated memory 22.86 GiB is allocated by PyTorch, and 182.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


--- NIGHT SHIFT CYCLE 37: lr_1e-4 ---
Initializing Vesuvius Autoresearch Training on s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/...
Initialized VesuviusS3Dataset from s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/: (20820, 6700, 9100) dtype("uint8")
Starting Scroll Foundation Loop (Budget: 300s)...
Traceback (most recent call last):
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 230, in <module>
    train()
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/train.py", line 122, in train
    out_ink, feat_student, _, _, _, _ = model(x_orig, return_fiber=True)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 65, in forward
    feat_orig = self._extract_features(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 88, in _extract_features
    x = block(x)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1775, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/.venv/lib/python3.10/site-packages/torch/nn/modules/module.py", line 1786, in _call_impl
    return forward_call(*args, **kwargs)
  File "/home/jon/openclaw-workspace/Neo-VM/projects/bountyhunter/vesuvius_model.py", line 111, in forward
    x = F.gelu(self.norm1(self.conv1(x)))
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 192.00 MiB. GPU 0 has a total capacity of 23.52 GiB of which 184.00 MiB is free. Including non-PyTorch memory, this process has 23.32 GiB memory in use. Of the allocated memory 22.67 GiB is allocated by PyTorch, and 199.60 MiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)

```

---

# Night Shift Log: 2026-03-22_076
- **Tweak**: batch_size_6
- **Status**: SUCCESS
- **Timestamp**: 21:37:14

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
173s
Step 0235 | Loss: 0.018025 | dt: 446ms | Remaining: 168s
Step 0240 | Loss: 0.023879 | dt: 435ms | Remaining: 166s
Step 0245 | Loss: 0.025498 | dt: 434ms | Remaining: 164s
Step 0250 | Loss: 0.025822 | dt: 434ms | Remaining: 161s
Step 0255 | Loss: 0.024410 | dt: 434ms | Remaining: 159s
Step 0260 | Loss: 0.021837 | dt: 435ms | Remaining: 155s
Step 0265 | Loss: 0.018323 | dt: 433ms | Remaining: 153s
Step 0270 | Loss: 0.017390 | dt: 434ms | Remaining: 150s
Step 0275 | Loss: 0.015325 | dt: 433ms | Remaining: 148s
Step 0280 | Loss: 0.018675 | dt: 446ms | Remaining: 144s
Step 0285 | Loss: 0.020992 | dt: 435ms | Remaining: 142s
Step 0290 | Loss: 0.020987 | dt: 433ms | Remaining: 140s
Step 0295 | Loss: 0.019746 | dt: 433ms | Remaining: 137s
Step 0300 | Loss: 0.023500 | dt: 434ms | Remaining: 132s
Step 0305 | Loss: 0.027920 | dt: 433ms | Remaining: 130s
Step 0310 | Loss: 0.032128 | dt: 434ms | Remaining: 128s
Step 0315 | Loss: 0.033067 | dt: 434ms | Remaining: 126s
Step 0320 | Loss: 0.035419 | dt: 3311ms | Remaining: 121s
Step 0325 | Loss: 0.031814 | dt: 433ms | Remaining: 119s
Step 0330 | Loss: 0.026288 | dt: 434ms | Remaining: 116s
Step 0335 | Loss: 0.024922 | dt: 434ms | Remaining: 114s
Step 0340 | Loss: 0.022730 | dt: 433ms | Remaining: 112s
Step 0345 | Loss: 0.019039 | dt: 434ms | Remaining: 109s
Step 0350 | Loss: 0.016137 | dt: 433ms | Remaining: 107s
Step 0355 | Loss: 0.014635 | dt: 433ms | Remaining: 105s
Step 0360 | Loss: 0.013188 | dt: 433ms | Remaining: 103s
Step 0365 | Loss: 0.014988 | dt: 434ms | Remaining: 98s
Step 0370 | Loss: 0.016510 | dt: 436ms | Remaining: 96s
Step 0375 | Loss: 0.018164 | dt: 435ms | Remaining: 94s
Step 0380 | Loss: 0.017744 | dt: 433ms | Remaining: 92s
Step 0385 | Loss: 0.016122 | dt: 438ms | Remaining: 89s
Step 0390 | Loss: 0.013260 | dt: 447ms | Remaining: 87s
Step 0395 | Loss: 0.011380 | dt: 434ms | Remaining: 84s
Step 0400 | Loss: 0.010394 | dt: 433ms | Remaining: 82s
Step 0405 | Loss: 0.009289 | dt: 1639ms | Remaining: 79s
Step 0410 | Loss: 0.008466 | dt: 446ms | Remaining: 77s
Step 0415 | Loss: 0.007689 | dt: 433ms | Remaining: 75s
Step 0420 | Loss: 0.007275 | dt: 447ms | Remaining: 72s
Step 0425 | Loss: 0.007071 | dt: 435ms | Remaining: 70s
Step 0430 | Loss: 0.011993 | dt: 435ms | Remaining: 65s
Step 0435 | Loss: 0.015858 | dt: 434ms | Remaining: 62s
Step 0440 | Loss: 0.017169 | dt: 434ms | Remaining: 60s
Step 0445 | Loss: 0.017812 | dt: 434ms | Remaining: 58s
Step 0450 | Loss: 0.017200 | dt: 434ms | Remaining: 53s
Step 0455 | Loss: 0.020130 | dt: 445ms | Remaining: 51s
Step 0460 | Loss: 0.027638 | dt: 446ms | Remaining: 48s
Step 0465 | Loss: 0.044704 | dt: 447ms | Remaining: 46s
Step 0470 | Loss: 0.043950 | dt: 446ms | Remaining: 43s
Step 0475 | Loss: 0.034702 | dt: 437ms | Remaining: 41s
Step 0480 | Loss: 0.029262 | dt: 435ms | Remaining: 39s
Step 0485 | Loss: 0.027966 | dt: 433ms | Remaining: 37s
Step 0490 | Loss: 0.029914 | dt: 1022ms | Remaining: 34s
Step 0495 | Loss: 0.029448 | dt: 434ms | Remaining: 32s
Step 0500 | Loss: 0.027408 | dt: 434ms | Remaining: 30s
Step 0505 | Loss: 0.024732 | dt: 436ms | Remaining: 28s
Step 0510 | Loss: 0.022047 | dt: 443ms | Remaining: 25s
Step 0515 | Loss: 0.020273 | dt: 434ms | Remaining: 23s
Step 0520 | Loss: 0.018428 | dt: 436ms | Remaining: 20s
Step 0525 | Loss: 0.016127 | dt: 433ms | Remaining: 18s
Step 0530 | Loss: 0.015092 | dt: 434ms | Remaining: 16s
Step 0535 | Loss: 0.030183 | dt: 434ms | Remaining: 11s
Step 0540 | Loss: 0.039559 | dt: 436ms | Remaining: 9s
Step 0545 | Loss: 0.037249 | dt: 434ms | Remaining: 7s
Step 0550 | Loss: 0.033874 | dt: 434ms | Remaining: 5s
Step 0555 | Loss: 0.028215 | dt: 434ms | Remaining: 2s
Step 0560 | Loss: 0.022508 | dt: 434ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.003849 [NEW BEST]
train_loss:       0.022508
training_seconds: 300.1
total_seconds:    301.7
peak_vram_mb:     20486.3
num_steps:        561
num_params_M:     2.262
throughput_Mvps:  0.73
Updated progress.png

[RESULT] Improvement detected! Recommended: Keep changes.

```

---

# Night Shift Log: 2026-03-22_077
- **Tweak**: base_feat_64
- **Status**: SUCCESS
- **Timestamp**: 21:42:26

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```

Step 0235 | Loss: 0.016348 | dt: 434ms | Remaining: 172s
Step 0240 | Loss: 0.015574 | dt: 434ms | Remaining: 170s
Step 0245 | Loss: 0.015087 | dt: 436ms | Remaining: 168s
Step 0250 | Loss: 0.014852 | dt: 437ms | Remaining: 166s
Step 0255 | Loss: 0.014480 | dt: 434ms | Remaining: 163s
Step 0260 | Loss: 0.014006 | dt: 434ms | Remaining: 161s
Step 0265 | Loss: 0.013699 | dt: 450ms | Remaining: 158s
Step 0270 | Loss: 0.012854 | dt: 434ms | Remaining: 156s
Step 0275 | Loss: 0.012374 | dt: 435ms | Remaining: 154s
Step 0280 | Loss: 0.040620 | dt: 437ms | Remaining: 149s
Step 0285 | Loss: 0.064457 | dt: 437ms | Remaining: 147s
Step 0290 | Loss: 0.097439 | dt: 434ms | Remaining: 145s
Step 0295 | Loss: 0.096410 | dt: 444ms | Remaining: 143s
Step 0300 | Loss: 0.080417 | dt: 433ms | Remaining: 138s
Step 0305 | Loss: 0.065787 | dt: 434ms | Remaining: 136s
Step 0310 | Loss: 0.054327 | dt: 448ms | Remaining: 133s
Step 0315 | Loss: 0.048459 | dt: 443ms | Remaining: 131s
Step 0320 | Loss: 0.041052 | dt: 1145ms | Remaining: 128s
Step 0325 | Loss: 0.030652 | dt: 435ms | Remaining: 126s
Step 0330 | Loss: 0.024883 | dt: 434ms | Remaining: 124s
Step 0335 | Loss: 0.020382 | dt: 433ms | Remaining: 122s
Step 0340 | Loss: 0.018233 | dt: 434ms | Remaining: 120s
Step 0345 | Loss: 0.015937 | dt: 434ms | Remaining: 117s
Step 0350 | Loss: 0.013661 | dt: 435ms | Remaining: 115s
Step 0355 | Loss: 0.012813 | dt: 435ms | Remaining: 112s
Step 0360 | Loss: 0.012879 | dt: 433ms | Remaining: 110s
Step 0365 | Loss: 0.018584 | dt: 434ms | Remaining: 105s
Step 0370 | Loss: 0.023020 | dt: 433ms | Remaining: 103s
Step 0375 | Loss: 0.024013 | dt: 436ms | Remaining: 101s
Step 0380 | Loss: 0.023636 | dt: 435ms | Remaining: 99s
Step 0385 | Loss: 0.020593 | dt: 435ms | Remaining: 96s
Step 0390 | Loss: 0.016851 | dt: 434ms | Remaining: 94s
Step 0395 | Loss: 0.013875 | dt: 433ms | Remaining: 92s
Step 0400 | Loss: 0.013099 | dt: 434ms | Remaining: 89s
Step 0405 | Loss: 0.011687 | dt: 1074ms | Remaining: 86s
Step 0410 | Loss: 0.011123 | dt: 435ms | Remaining: 84s
Step 0415 | Loss: 0.010214 | dt: 438ms | Remaining: 82s
Step 0420 | Loss: 0.009874 | dt: 449ms | Remaining: 80s
Step 0425 | Loss: 0.008828 | dt: 434ms | Remaining: 78s
Step 0430 | Loss: 0.017442 | dt: 433ms | Remaining: 71s
Step 0435 | Loss: 0.022443 | dt: 433ms | Remaining: 69s
Step 0440 | Loss: 0.024727 | dt: 435ms | Remaining: 67s
Step 0445 | Loss: 0.023275 | dt: 434ms | Remaining: 65s
Step 0450 | Loss: 0.021675 | dt: 436ms | Remaining: 59s
Step 0455 | Loss: 0.022289 | dt: 447ms | Remaining: 57s
Step 0460 | Loss: 0.022751 | dt: 434ms | Remaining: 55s
Step 0465 | Loss: 0.021730 | dt: 434ms | Remaining: 53s
Step 0470 | Loss: 0.021329 | dt: 445ms | Remaining: 48s
Step 0475 | Loss: 0.020048 | dt: 447ms | Remaining: 46s
Step 0480 | Loss: 0.020052 | dt: 435ms | Remaining: 44s
Step 0485 | Loss: 0.021987 | dt: 434ms | Remaining: 41s
Step 0490 | Loss: 0.021176 | dt: 1701ms | Remaining: 38s
Step 0495 | Loss: 0.016193 | dt: 435ms | Remaining: 36s
Step 0500 | Loss: 0.013363 | dt: 434ms | Remaining: 34s
Step 0505 | Loss: 0.011066 | dt: 434ms | Remaining: 31s
Step 0510 | Loss: 0.010122 | dt: 442ms | Remaining: 29s
Step 0515 | Loss: 0.017273 | dt: 435ms | Remaining: 23s
Step 0520 | Loss: 0.021273 | dt: 435ms | Remaining: 21s
Step 0525 | Loss: 0.021943 | dt: 435ms | Remaining: 19s
Step 0530 | Loss: 0.019863 | dt: 446ms | Remaining: 17s
Step 0535 | Loss: 0.020608 | dt: 451ms | Remaining: 12s
Step 0540 | Loss: 0.023477 | dt: 447ms | Remaining: 10s
Step 0545 | Loss: 0.025669 | dt: 434ms | Remaining: 8s
Step 0550 | Loss: 0.021741 | dt: 433ms | Remaining: 6s
Step 0555 | Loss: 0.019652 | dt: 433ms | Remaining: 3s
Step 0560 | Loss: 0.014732 | dt: 434ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.001896 [NEW BEST]
train_loss:       0.012907
training_seconds: 300.4
total_seconds:    302.1
peak_vram_mb:     20486.3
num_steps:        563
num_params_M:     2.262
throughput_Mvps:  0.74
Updated progress.png

[RESULT] Improvement detected! Recommended: Keep changes.

```

---

# Night Shift Log: 2026-03-22_078
- **Tweak**: patch_size_32
- **Status**: REVERTED
- **Timestamp**: 21:47:38

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 32

## Run Output (Tail)
```
ining: 61s
Step 1500 | Loss: 1.051058 | dt: 100ms | Remaining: 61s
Step 1505 | Loss: 0.802970 | dt: 102ms | Remaining: 60s
Step 1510 | Loss: 0.606826 | dt: 101ms | Remaining: 60s
Step 1515 | Loss: 0.492188 | dt: 98ms | Remaining: 59s
Step 1520 | Loss: 0.335661 | dt: 98ms | Remaining: 58s
Step 1525 | Loss: 0.247344 | dt: 102ms | Remaining: 58s
Step 1530 | Loss: 0.178948 | dt: 100ms | Remaining: 57s
Step 1535 | Loss: 0.140179 | dt: 98ms | Remaining: 57s
Step 1540 | Loss: 0.246801 | dt: 101ms | Remaining: 55s
Step 1545 | Loss: 0.232457 | dt: 100ms | Remaining: 54s
Step 1550 | Loss: 0.250333 | dt: 99ms | Remaining: 54s
Step 1555 | Loss: 0.257908 | dt: 99ms | Remaining: 53s
Step 1560 | Loss: 0.322398 | dt: 101ms | Remaining: 51s
Step 1565 | Loss: 0.284930 | dt: 99ms | Remaining: 51s
Step 1570 | Loss: 0.250432 | dt: 98ms | Remaining: 50s
Step 1575 | Loss: 0.259246 | dt: 98ms | Remaining: 50s
Step 1580 | Loss: 0.270129 | dt: 101ms | Remaining: 49s
Step 1585 | Loss: 0.222077 | dt: 99ms | Remaining: 48s
Step 1590 | Loss: 0.183289 | dt: 106ms | Remaining: 48s
Step 1595 | Loss: 0.155435 | dt: 100ms | Remaining: 47s
Step 1600 | Loss: 0.132941 | dt: 393ms | Remaining: 46s
Step 1605 | Loss: 0.117152 | dt: 102ms | Remaining: 46s
Step 1610 | Loss: 0.106633 | dt: 100ms | Remaining: 45s
Step 1615 | Loss: 0.096845 | dt: 98ms | Remaining: 45s
Step 1620 | Loss: 0.100141 | dt: 100ms | Remaining: 44s
Step 1625 | Loss: 0.099754 | dt: 101ms | Remaining: 42s
Step 1630 | Loss: 0.105559 | dt: 98ms | Remaining: 41s
Step 1635 | Loss: 0.126071 | dt: 98ms | Remaining: 41s
Step 1640 | Loss: 0.108047 | dt: 99ms | Remaining: 40s
Step 1645 | Loss: 0.094344 | dt: 98ms | Remaining: 39s
Step 1650 | Loss: 0.101541 | dt: 98ms | Remaining: 39s
Step 1655 | Loss: 0.097785 | dt: 101ms | Remaining: 38s
Step 1660 | Loss: 0.094756 | dt: 98ms | Remaining: 38s
Step 1665 | Loss: 0.153355 | dt: 105ms | Remaining: 36s
Step 1670 | Loss: 0.320793 | dt: 99ms | Remaining: 35s
Step 1675 | Loss: 0.299185 | dt: 100ms | Remaining: 35s
Step 1680 | Loss: 0.234401 | dt: 101ms | Remaining: 34s
Step 1685 | Loss: 0.232555 | dt: 1340ms | Remaining: 33s
Step 1690 | Loss: 0.273442 | dt: 102ms | Remaining: 32s
Step 1695 | Loss: 0.261721 | dt: 100ms | Remaining: 32s
Step 1700 | Loss: 0.248708 | dt: 98ms | Remaining: 31s
Step 1705 | Loss: 0.199456 | dt: 99ms | Remaining: 31s
Step 1710 | Loss: 0.169255 | dt: 100ms | Remaining: 29s
Step 1715 | Loss: 0.153144 | dt: 98ms | Remaining: 28s
Step 1720 | Loss: 0.132501 | dt: 98ms | Remaining: 28s
Step 1725 | Loss: 0.121016 | dt: 98ms | Remaining: 27s
Step 1730 | Loss: 0.119921 | dt: 101ms | Remaining: 22s
Step 1735 | Loss: 0.121593 | dt: 98ms | Remaining: 22s
Step 1740 | Loss: 0.112761 | dt: 100ms | Remaining: 21s
Step 1745 | Loss: 0.121939 | dt: 98ms | Remaining: 21s
Step 1750 | Loss: 0.124707 | dt: 101ms | Remaining: 16s
Step 1755 | Loss: 0.124589 | dt: 98ms | Remaining: 16s
Step 1760 | Loss: 0.118956 | dt: 101ms | Remaining: 15s
Step 1765 | Loss: 0.129519 | dt: 101ms | Remaining: 15s
Step 1770 | Loss: 0.132779 | dt: 1587ms | Remaining: 13s
Step 1775 | Loss: 0.136792 | dt: 100ms | Remaining: 12s
Step 1780 | Loss: 0.136140 | dt: 99ms | Remaining: 12s
Step 1785 | Loss: 0.130064 | dt: 98ms | Remaining: 11s
Step 1790 | Loss: 0.162081 | dt: 103ms | Remaining: 11s
Step 1795 | Loss: 0.156335 | dt: 100ms | Remaining: 10s
Step 1800 | Loss: 0.135395 | dt: 98ms | Remaining: 10s
Step 1805 | Loss: 0.118394 | dt: 101ms | Remaining: 9s
Step 1810 | Loss: 0.093457 | dt: 100ms | Remaining: 9s
Step 1815 | Loss: 0.135059 | dt: 104ms | Remaining: 4s
Step 1820 | Loss: 0.163994 | dt: 101ms | Remaining: 3s
Step 1825 | Loss: 0.210711 | dt: 98ms | Remaining: 3s
Step 1830 | Loss: 0.310042 | dt: 103ms | Remaining: 2s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.023660
train_loss:       0.305543
training_seconds: 301.0
total_seconds:    302.9
peak_vram_mb:     5153.2
num_steps:        1835
num_params_M:     2.262
throughput_Mvps:  0.60
Updated progress.png

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_079
- **Tweak**: heads_64
- **Status**: SUCCESS
- **Timestamp**: 21:52:50

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
s
Step 0230 | Loss: 0.029342 | dt: 447ms | Remaining: 177s
Step 0235 | Loss: 0.026533 | dt: 450ms | Remaining: 171s
Step 0240 | Loss: 0.026559 | dt: 433ms | Remaining: 169s
Step 0245 | Loss: 0.034459 | dt: 436ms | Remaining: 167s
Step 0250 | Loss: 0.052673 | dt: 436ms | Remaining: 165s
Step 0255 | Loss: 0.061231 | dt: 434ms | Remaining: 163s
Step 0260 | Loss: 0.051276 | dt: 443ms | Remaining: 158s
Step 0265 | Loss: 0.041417 | dt: 433ms | Remaining: 155s
Step 0270 | Loss: 0.033117 | dt: 434ms | Remaining: 153s
Step 0275 | Loss: 0.028041 | dt: 443ms | Remaining: 151s
Step 0280 | Loss: 0.022382 | dt: 434ms | Remaining: 148s
Step 0285 | Loss: 0.016385 | dt: 433ms | Remaining: 146s
Step 0290 | Loss: 0.012892 | dt: 434ms | Remaining: 144s
Step 0295 | Loss: 0.010768 | dt: 444ms | Remaining: 142s
Step 0300 | Loss: 0.012267 | dt: 443ms | Remaining: 137s
Step 0305 | Loss: 0.014653 | dt: 437ms | Remaining: 135s
Step 0310 | Loss: 0.015011 | dt: 438ms | Remaining: 132s
Step 0315 | Loss: 0.016265 | dt: 434ms | Remaining: 130s
Step 0320 | Loss: 0.014358 | dt: 1823ms | Remaining: 127s
Step 0325 | Loss: 0.011611 | dt: 439ms | Remaining: 124s
Step 0330 | Loss: 0.009846 | dt: 433ms | Remaining: 122s
Step 0335 | Loss: 0.008753 | dt: 435ms | Remaining: 120s
Step 0340 | Loss: 0.008515 | dt: 434ms | Remaining: 118s
Step 0345 | Loss: 0.025071 | dt: 436ms | Remaining: 113s
Step 0350 | Loss: 0.041314 | dt: 464ms | Remaining: 110s
Step 0355 | Loss: 0.043492 | dt: 436ms | Remaining: 108s
Step 0360 | Loss: 0.044828 | dt: 434ms | Remaining: 106s
Step 0365 | Loss: 0.036775 | dt: 447ms | Remaining: 103s
Step 0370 | Loss: 0.031576 | dt: 434ms | Remaining: 101s
Step 0375 | Loss: 0.026994 | dt: 434ms | Remaining: 99s
Step 0380 | Loss: 0.023674 | dt: 433ms | Remaining: 97s
Step 0385 | Loss: 0.031978 | dt: 453ms | Remaining: 92s
Step 0390 | Loss: 0.035167 | dt: 450ms | Remaining: 90s
Step 0395 | Loss: 0.038346 | dt: 448ms | Remaining: 87s
Step 0400 | Loss: 0.038071 | dt: 450ms | Remaining: 85s
Step 0405 | Loss: 0.035932 | dt: 2911ms | Remaining: 80s
Step 0410 | Loss: 0.027659 | dt: 434ms | Remaining: 78s
Step 0415 | Loss: 0.024848 | dt: 434ms | Remaining: 76s
Step 0420 | Loss: 0.021215 | dt: 450ms | Remaining: 74s
Step 0425 | Loss: 0.017897 | dt: 435ms | Remaining: 72s
Step 0430 | Loss: 0.017722 | dt: 453ms | Remaining: 63s
Step 0435 | Loss: 0.016765 | dt: 433ms | Remaining: 61s
Step 0440 | Loss: 0.014830 | dt: 445ms | Remaining: 58s
Step 0445 | Loss: 0.014395 | dt: 438ms | Remaining: 56s
Step 0450 | Loss: 0.013160 | dt: 443ms | Remaining: 53s
Step 0455 | Loss: 0.010253 | dt: 437ms | Remaining: 51s
Step 0460 | Loss: 0.008750 | dt: 437ms | Remaining: 49s
Step 0465 | Loss: 0.007549 | dt: 434ms | Remaining: 47s
Step 0470 | Loss: 0.006866 | dt: 436ms | Remaining: 44s
Step 0475 | Loss: 0.006359 | dt: 450ms | Remaining: 42s
Step 0480 | Loss: 0.005907 | dt: 433ms | Remaining: 39s
Step 0485 | Loss: 0.005707 | dt: 435ms | Remaining: 37s
Step 0490 | Loss: 0.005588 | dt: 1208ms | Remaining: 34s
Step 0495 | Loss: 0.005401 | dt: 446ms | Remaining: 32s
Step 0500 | Loss: 0.005290 | dt: 434ms | Remaining: 30s
Step 0505 | Loss: 0.005473 | dt: 433ms | Remaining: 28s
Step 0510 | Loss: 0.005613 | dt: 434ms | Remaining: 25s
Step 0515 | Loss: 0.008244 | dt: 448ms | Remaining: 18s
Step 0520 | Loss: 0.011446 | dt: 454ms | Remaining: 16s
Step 0525 | Loss: 0.013585 | dt: 434ms | Remaining: 14s
Step 0530 | Loss: 0.014148 | dt: 435ms | Remaining: 12s
Step 0535 | Loss: 0.013172 | dt: 436ms | Remaining: 9s
Step 0540 | Loss: 0.009891 | dt: 435ms | Remaining: 7s
Step 0545 | Loss: 0.007892 | dt: 441ms | Remaining: 5s
Step 0550 | Loss: 0.006730 | dt: 435ms | Remaining: 2s
Step 0555 | Loss: 0.006279 | dt: 450ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.001026 [NEW BEST]
train_loss:       0.006279
training_seconds: 300.4
total_seconds:    302.2
peak_vram_mb:     20486.3
num_steps:        556
num_params_M:     2.262
throughput_Mvps:  0.73
Updated progress.png

[RESULT] Improvement detected! Recommended: Keep changes.

```

---

# Night Shift Log: 2026-03-22_080
- **Tweak**: wd_0.0
- **Status**: SUCCESS
- **Timestamp**: 21:58:02

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
tep 0230 | Loss: 0.008687 | dt: 448ms | Remaining: 179s
Step 0235 | Loss: 0.010726 | dt: 434ms | Remaining: 173s
Step 0240 | Loss: 0.015642 | dt: 433ms | Remaining: 171s
Step 0245 | Loss: 0.020107 | dt: 435ms | Remaining: 169s
Step 0250 | Loss: 0.023053 | dt: 433ms | Remaining: 166s
Step 0255 | Loss: 0.023585 | dt: 436ms | Remaining: 164s
Step 0260 | Loss: 0.018866 | dt: 460ms | Remaining: 161s
Step 0265 | Loss: 0.015098 | dt: 450ms | Remaining: 159s
Step 0270 | Loss: 0.013244 | dt: 466ms | Remaining: 157s
Step 0275 | Loss: 0.012160 | dt: 435ms | Remaining: 154s
Step 0280 | Loss: 0.010988 | dt: 435ms | Remaining: 152s
Step 0285 | Loss: 0.010453 | dt: 437ms | Remaining: 149s
Step 0290 | Loss: 0.010004 | dt: 434ms | Remaining: 147s
Step 0295 | Loss: 0.010275 | dt: 434ms | Remaining: 145s
Step 0300 | Loss: 0.010266 | dt: 462ms | Remaining: 142s
Step 0305 | Loss: 0.010140 | dt: 434ms | Remaining: 140s
Step 0310 | Loss: 0.010271 | dt: 434ms | Remaining: 138s
Step 0315 | Loss: 0.010189 | dt: 435ms | Remaining: 136s
Step 0320 | Loss: 0.010924 | dt: 1085ms | Remaining: 133s
Step 0325 | Loss: 0.011741 | dt: 434ms | Remaining: 131s
Step 0330 | Loss: 0.012478 | dt: 439ms | Remaining: 128s
Step 0335 | Loss: 0.014907 | dt: 437ms | Remaining: 126s
Step 0340 | Loss: 0.023068 | dt: 433ms | Remaining: 124s
Step 0345 | Loss: 0.030730 | dt: 437ms | Remaining: 121s
Step 0350 | Loss: 0.030251 | dt: 452ms | Remaining: 119s
Step 0355 | Loss: 0.027206 | dt: 436ms | Remaining: 117s
Step 0360 | Loss: 0.024126 | dt: 434ms | Remaining: 114s
Step 0365 | Loss: 0.030159 | dt: 433ms | Remaining: 107s
Step 0370 | Loss: 0.035753 | dt: 435ms | Remaining: 104s
Step 0375 | Loss: 0.035288 | dt: 434ms | Remaining: 102s
Step 0380 | Loss: 0.032815 | dt: 433ms | Remaining: 100s
Step 0385 | Loss: 0.027103 | dt: 435ms | Remaining: 97s
Step 0390 | Loss: 0.019730 | dt: 434ms | Remaining: 95s
Step 0395 | Loss: 0.016972 | dt: 438ms | Remaining: 93s
Step 0400 | Loss: 0.014223 | dt: 435ms | Remaining: 91s
Step 0405 | Loss: 0.013440 | dt: 3341ms | Remaining: 86s
Step 0410 | Loss: 0.021657 | dt: 433ms | Remaining: 83s
Step 0415 | Loss: 0.028151 | dt: 433ms | Remaining: 81s
Step 0420 | Loss: 0.028778 | dt: 445ms | Remaining: 79s
Step 0425 | Loss: 0.027603 | dt: 434ms | Remaining: 77s
Step 0430 | Loss: 0.024629 | dt: 449ms | Remaining: 72s
Step 0435 | Loss: 0.024086 | dt: 433ms | Remaining: 70s
Step 0440 | Loss: 0.022360 | dt: 435ms | Remaining: 67s
Step 0445 | Loss: 0.021489 | dt: 438ms | Remaining: 65s
Step 0450 | Loss: 0.018268 | dt: 438ms | Remaining: 56s
Step 0455 | Loss: 0.014800 | dt: 435ms | Remaining: 54s
Step 0460 | Loss: 0.013526 | dt: 433ms | Remaining: 52s
Step 0465 | Loss: 0.013359 | dt: 434ms | Remaining: 50s
Step 0470 | Loss: 0.013924 | dt: 444ms | Remaining: 45s
Step 0475 | Loss: 0.016567 | dt: 435ms | Remaining: 42s
Step 0480 | Loss: 0.019292 | dt: 435ms | Remaining: 40s
Step 0485 | Loss: 0.016821 | dt: 434ms | Remaining: 38s
Step 0490 | Loss: 0.014845 | dt: 1080ms | Remaining: 35s
Step 0495 | Loss: 0.010970 | dt: 434ms | Remaining: 33s
Step 0500 | Loss: 0.008695 | dt: 448ms | Remaining: 31s
Step 0505 | Loss: 0.007049 | dt: 435ms | Remaining: 29s
Step 0510 | Loss: 0.006288 | dt: 449ms | Remaining: 26s
Step 0515 | Loss: 0.007466 | dt: 449ms | Remaining: 21s
Step 0520 | Loss: 0.009018 | dt: 450ms | Remaining: 19s
Step 0525 | Loss: 0.009921 | dt: 434ms | Remaining: 17s
Step 0530 | Loss: 0.010250 | dt: 436ms | Remaining: 14s
Step 0535 | Loss: 0.009496 | dt: 435ms | Remaining: 10s
Step 0540 | Loss: 0.008444 | dt: 434ms | Remaining: 8s
Step 0545 | Loss: 0.008724 | dt: 434ms | Remaining: 6s
Step 0550 | Loss: 0.008215 | dt: 433ms | Remaining: 4s
Step 0555 | Loss: 0.007065 | dt: 447ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.000750 [NEW BEST]
train_loss:       0.006781
training_seconds: 300.1
total_seconds:    301.9
peak_vram_mb:     20486.3
num_steps:        558
num_params_M:     2.262
throughput_Mvps:  0.73
Updated progress.png

[RESULT] Improvement detected! Recommended: Keep changes.

```

---

# Night Shift Log: 2026-03-22_081
- **Tweak**: blocks_16
- **Status**: REVERTED
- **Timestamp**: 22:03:15

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
| dt: 395ms | Remaining: 173s
Step 0260 | Loss: 0.029933 | dt: 408ms | Remaining: 165s
Step 0265 | Loss: 0.030580 | dt: 394ms | Remaining: 163s
Step 0270 | Loss: 0.027013 | dt: 396ms | Remaining: 161s
Step 0275 | Loss: 0.023847 | dt: 395ms | Remaining: 159s
Step 0280 | Loss: 0.022044 | dt: 395ms | Remaining: 154s
Step 0285 | Loss: 0.018797 | dt: 395ms | Remaining: 152s
Step 0290 | Loss: 0.017355 | dt: 395ms | Remaining: 150s
Step 0295 | Loss: 0.015814 | dt: 396ms | Remaining: 148s
Step 0300 | Loss: 0.019639 | dt: 396ms | Remaining: 146s
Step 0305 | Loss: 0.015762 | dt: 395ms | Remaining: 144s
Step 0310 | Loss: 0.012362 | dt: 407ms | Remaining: 142s
Step 0315 | Loss: 0.010924 | dt: 394ms | Remaining: 140s
Step 0320 | Loss: 0.011369 | dt: 3275ms | Remaining: 135s
Step 0325 | Loss: 0.015135 | dt: 395ms | Remaining: 133s
Step 0330 | Loss: 0.016258 | dt: 417ms | Remaining: 131s
Step 0335 | Loss: 0.017789 | dt: 395ms | Remaining: 129s
Step 0340 | Loss: 0.019949 | dt: 395ms | Remaining: 127s
Step 0345 | Loss: 0.021904 | dt: 395ms | Remaining: 121s
Step 0350 | Loss: 0.023301 | dt: 395ms | Remaining: 119s
Step 0355 | Loss: 0.023819 | dt: 410ms | Remaining: 117s
Step 0360 | Loss: 0.024269 | dt: 411ms | Remaining: 115s
Step 0365 | Loss: 0.021263 | dt: 420ms | Remaining: 112s
Step 0370 | Loss: 0.017401 | dt: 423ms | Remaining: 110s
Step 0375 | Loss: 0.015334 | dt: 430ms | Remaining: 108s
Step 0380 | Loss: 0.013458 | dt: 411ms | Remaining: 106s
Step 0385 | Loss: 0.018211 | dt: 415ms | Remaining: 101s
Step 0390 | Loss: 0.026185 | dt: 409ms | Remaining: 99s
Step 0395 | Loss: 0.025318 | dt: 397ms | Remaining: 97s
Step 0400 | Loss: 0.025833 | dt: 395ms | Remaining: 95s
Step 0405 | Loss: 0.103917 | dt: 4158ms | Remaining: 89s
Step 0410 | Loss: 0.235650 | dt: 396ms | Remaining: 87s
Step 0415 | Loss: 0.272900 | dt: 396ms | Remaining: 85s
Step 0420 | Loss: 0.205990 | dt: 395ms | Remaining: 83s
Step 0425 | Loss: 0.147640 | dt: 396ms | Remaining: 81s
Step 0430 | Loss: 0.119131 | dt: 398ms | Remaining: 76s
Step 0435 | Loss: 0.090460 | dt: 401ms | Remaining: 74s
Step 0440 | Loss: 0.070243 | dt: 398ms | Remaining: 72s
Step 0445 | Loss: 0.059187 | dt: 409ms | Remaining: 70s
Step 0450 | Loss: 0.046943 | dt: 395ms | Remaining: 68s
Step 0455 | Loss: 0.037187 | dt: 395ms | Remaining: 66s
Step 0460 | Loss: 0.028578 | dt: 396ms | Remaining: 64s
Step 0465 | Loss: 0.022170 | dt: 397ms | Remaining: 62s
Step 0470 | Loss: 0.018688 | dt: 397ms | Remaining: 59s
Step 0475 | Loss: 0.016407 | dt: 401ms | Remaining: 57s
Step 0480 | Loss: 0.014265 | dt: 409ms | Remaining: 55s
Step 0485 | Loss: 0.013581 | dt: 396ms | Remaining: 53s
Step 0490 | Loss: 0.013362 | dt: 6203ms | Remaining: 45s
Step 0495 | Loss: 0.019048 | dt: 408ms | Remaining: 43s
Step 0500 | Loss: 0.047579 | dt: 396ms | Remaining: 41s
Step 0505 | Loss: 0.062060 | dt: 395ms | Remaining: 39s
Step 0510 | Loss: 0.071818 | dt: 394ms | Remaining: 37s
Step 0515 | Loss: 0.117135 | dt: 397ms | Remaining: 32s
Step 0520 | Loss: 0.147747 | dt: 395ms | Remaining: 30s
Step 0525 | Loss: 0.123637 | dt: 397ms | Remaining: 28s
Step 0530 | Loss: 0.093771 | dt: 395ms | Remaining: 26s
Step 0535 | Loss: 0.072586 | dt: 402ms | Remaining: 22s
Step 0540 | Loss: 0.050368 | dt: 412ms | Remaining: 20s
Step 0545 | Loss: 0.035504 | dt: 416ms | Remaining: 18s
Step 0550 | Loss: 0.026649 | dt: 395ms | Remaining: 16s
Step 0555 | Loss: 0.020525 | dt: 410ms | Remaining: 14s
Step 0560 | Loss: 0.016075 | dt: 396ms | Remaining: 12s
Step 0565 | Loss: 0.013615 | dt: 397ms | Remaining: 10s
Step 0570 | Loss: 0.012259 | dt: 398ms | Remaining: 8s
Step 0575 | Loss: 0.011150 | dt: 397ms | Remaining: 6s
Step 0580 | Loss: 0.010270 | dt: 399ms | Remaining: 3s
Step 0585 | Loss: 0.009758 | dt: 399ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.003382
train_loss:       0.009643
training_seconds: 300.3
total_seconds:    302.1
peak_vram_mb:     19043.5
num_steps:        589
num_params_M:     2.016
throughput_Mvps:  0.77

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_082
- **Tweak**: dropout_0.4
- **Status**: REVERTED
- **Timestamp**: 22:08:25

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
 dt: 464ms | Remaining: 172s
Step 0230 | Loss: 0.028071 | dt: 451ms | Remaining: 170s
Step 0235 | Loss: 0.027969 | dt: 449ms | Remaining: 166s
Step 0240 | Loss: 0.023744 | dt: 462ms | Remaining: 164s
Step 0245 | Loss: 0.020069 | dt: 464ms | Remaining: 161s
Step 0250 | Loss: 0.017662 | dt: 451ms | Remaining: 159s
Step 0255 | Loss: 0.016081 | dt: 454ms | Remaining: 157s
Step 0260 | Loss: 0.015070 | dt: 449ms | Remaining: 154s
Step 0265 | Loss: 0.014192 | dt: 464ms | Remaining: 152s
Step 0270 | Loss: 0.013507 | dt: 449ms | Remaining: 149s
Step 0275 | Loss: 0.013217 | dt: 448ms | Remaining: 147s
Step 0280 | Loss: 0.012972 | dt: 449ms | Remaining: 144s
Step 0285 | Loss: 0.013024 | dt: 449ms | Remaining: 142s
Step 0290 | Loss: 0.013049 | dt: 449ms | Remaining: 140s
Step 0295 | Loss: 0.012725 | dt: 456ms | Remaining: 137s
Step 0300 | Loss: 0.027320 | dt: 448ms | Remaining: 132s
Step 0305 | Loss: 0.045625 | dt: 460ms | Remaining: 130s
Step 0310 | Loss: 0.052713 | dt: 449ms | Remaining: 128s
Step 0315 | Loss: 0.047013 | dt: 464ms | Remaining: 126s
Step 0320 | Loss: 0.036787 | dt: 1054ms | Remaining: 123s
Step 0325 | Loss: 0.027313 | dt: 466ms | Remaining: 120s
Step 0330 | Loss: 0.021058 | dt: 465ms | Remaining: 118s
Step 0335 | Loss: 0.017093 | dt: 462ms | Remaining: 116s
Step 0340 | Loss: 0.014726 | dt: 448ms | Remaining: 113s
Step 0345 | Loss: 0.013496 | dt: 452ms | Remaining: 110s
Step 0350 | Loss: 0.013029 | dt: 449ms | Remaining: 108s
Step 0355 | Loss: 0.013272 | dt: 449ms | Remaining: 106s
Step 0360 | Loss: 0.013266 | dt: 448ms | Remaining: 104s
Step 0365 | Loss: 0.054833 | dt: 449ms | Remaining: 99s
Step 0370 | Loss: 0.040810 | dt: 468ms | Remaining: 97s
Step 0375 | Loss: 0.139864 | dt: 450ms | Remaining: 95s
Step 0380 | Loss: 0.122076 | dt: 459ms | Remaining: 92s
Step 0385 | Loss: 0.092660 | dt: 451ms | Remaining: 89s
Step 0390 | Loss: 0.059525 | dt: 451ms | Remaining: 87s
Step 0395 | Loss: 0.040118 | dt: 461ms | Remaining: 85s
Step 0400 | Loss: 0.031246 | dt: 459ms | Remaining: 82s
Step 0405 | Loss: 0.038051 | dt: 3432ms | Remaining: 77s
Step 0410 | Loss: 0.111552 | dt: 470ms | Remaining: 75s
Step 0415 | Loss: 0.082093 | dt: 453ms | Remaining: 73s
Step 0420 | Loss: 0.061309 | dt: 459ms | Remaining: 70s
Step 0425 | Loss: 0.047039 | dt: 449ms | Remaining: 68s
Step 0430 | Loss: 0.033439 | dt: 452ms | Remaining: 64s
Step 0435 | Loss: 0.025102 | dt: 449ms | Remaining: 61s
Step 0440 | Loss: 0.019056 | dt: 449ms | Remaining: 59s
Step 0445 | Loss: 0.016136 | dt: 449ms | Remaining: 57s
Step 0450 | Loss: 0.012695 | dt: 449ms | Remaining: 54s
Step 0455 | Loss: 0.010326 | dt: 452ms | Remaining: 52s
Step 0460 | Loss: 0.008907 | dt: 449ms | Remaining: 49s
Step 0465 | Loss: 0.007940 | dt: 448ms | Remaining: 47s
Step 0470 | Loss: 0.007441 | dt: 448ms | Remaining: 44s
Step 0475 | Loss: 0.007347 | dt: 450ms | Remaining: 42s
Step 0480 | Loss: 0.007165 | dt: 450ms | Remaining: 40s
Step 0485 | Loss: 0.007260 | dt: 458ms | Remaining: 38s
Step 0490 | Loss: 0.007286 | dt: 2480ms | Remaining: 33s
Step 0495 | Loss: 0.009620 | dt: 448ms | Remaining: 31s
Step 0500 | Loss: 0.010982 | dt: 451ms | Remaining: 29s
Step 0505 | Loss: 0.011948 | dt: 449ms | Remaining: 27s
Step 0510 | Loss: 0.012079 | dt: 450ms | Remaining: 24s
Step 0515 | Loss: 0.011386 | dt: 448ms | Remaining: 20s
Step 0520 | Loss: 0.010731 | dt: 464ms | Remaining: 18s
Step 0525 | Loss: 0.010514 | dt: 451ms | Remaining: 15s
Step 0530 | Loss: 0.009443 | dt: 449ms | Remaining: 13s
Step 0535 | Loss: 0.008776 | dt: 449ms | Remaining: 10s
Step 0540 | Loss: 0.008110 | dt: 449ms | Remaining: 8s
Step 0545 | Loss: 0.007703 | dt: 449ms | Remaining: 6s
Step 0550 | Loss: 0.007569 | dt: 450ms | Remaining: 4s
Step 0555 | Loss: 0.007446 | dt: 462ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.003571
train_loss:       0.007552
training_seconds: 300.1
total_seconds:    301.8
peak_vram_mb:     22406.7
num_steps:        558
num_params_M:     2.262
throughput_Mvps:  0.73

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_083
- **Tweak**: lr_3e-4
- **Status**: REVERTED
- **Timestamp**: 22:13:35

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
dt: 448ms | Remaining: 185s
Step 0200 | Loss: 0.038093 | dt: 449ms | Remaining: 183s
Step 0205 | Loss: 0.028213 | dt: 449ms | Remaining: 181s
Step 0210 | Loss: 0.021786 | dt: 461ms | Remaining: 179s
Step 0215 | Loss: 0.021662 | dt: 461ms | Remaining: 173s
Step 0220 | Loss: 0.021629 | dt: 449ms | Remaining: 170s
Step 0225 | Loss: 0.019974 | dt: 452ms | Remaining: 168s
Step 0230 | Loss: 0.021048 | dt: 450ms | Remaining: 166s
Step 0235 | Loss: 0.019169 | dt: 454ms | Remaining: 163s
Step 0240 | Loss: 0.016338 | dt: 449ms | Remaining: 161s
Step 0245 | Loss: 0.013639 | dt: 454ms | Remaining: 158s
Step 0250 | Loss: 0.012526 | dt: 448ms | Remaining: 156s
Step 0255 | Loss: 0.011603 | dt: 449ms | Remaining: 154s
Step 0260 | Loss: 0.019090 | dt: 450ms | Remaining: 146s
Step 0265 | Loss: 0.018983 | dt: 449ms | Remaining: 144s
Step 0270 | Loss: 0.018498 | dt: 458ms | Remaining: 141s
Step 0275 | Loss: 0.019285 | dt: 449ms | Remaining: 139s
Step 0280 | Loss: 0.015519 | dt: 449ms | Remaining: 136s
Step 0285 | Loss: 0.011949 | dt: 448ms | Remaining: 134s
Step 0290 | Loss: 0.009781 | dt: 450ms | Remaining: 132s
Step 0295 | Loss: 0.008932 | dt: 450ms | Remaining: 129s
Step 0300 | Loss: 0.011614 | dt: 450ms | Remaining: 125s
Step 0305 | Loss: 0.020726 | dt: 449ms | Remaining: 122s
Step 0310 | Loss: 0.028491 | dt: 450ms | Remaining: 120s
Step 0315 | Loss: 0.027359 | dt: 450ms | Remaining: 118s
Step 0320 | Loss: 0.026725 | dt: 3335ms | Remaining: 113s
Step 0325 | Loss: 0.024296 | dt: 449ms | Remaining: 110s
Step 0330 | Loss: 0.022662 | dt: 448ms | Remaining: 108s
Step 0335 | Loss: 0.021686 | dt: 450ms | Remaining: 106s
Step 0340 | Loss: 0.021691 | dt: 450ms | Remaining: 104s
Step 0345 | Loss: 0.018809 | dt: 449ms | Remaining: 99s
Step 0350 | Loss: 0.016615 | dt: 450ms | Remaining: 96s
Step 0355 | Loss: 0.014663 | dt: 448ms | Remaining: 94s
Step 0360 | Loss: 0.013353 | dt: 449ms | Remaining: 92s
Step 0365 | Loss: 0.011775 | dt: 449ms | Remaining: 89s
Step 0370 | Loss: 0.009504 | dt: 449ms | Remaining: 87s
Step 0375 | Loss: 0.008615 | dt: 449ms | Remaining: 84s
Step 0380 | Loss: 0.007925 | dt: 451ms | Remaining: 82s
Step 0385 | Loss: 0.009630 | dt: 487ms | Remaining: 76s
Step 0390 | Loss: 0.012957 | dt: 463ms | Remaining: 74s
Step 0395 | Loss: 0.017642 | dt: 464ms | Remaining: 72s
Step 0400 | Loss: 0.019958 | dt: 489ms | Remaining: 69s
Step 0405 | Loss: 0.019540 | dt: 3078ms | Remaining: 64s
Step 0410 | Loss: 0.016659 | dt: 449ms | Remaining: 62s
Step 0415 | Loss: 0.015665 | dt: 451ms | Remaining: 60s
Step 0420 | Loss: 0.014299 | dt: 450ms | Remaining: 57s
Step 0425 | Loss: 0.012850 | dt: 448ms | Remaining: 55s
Step 0430 | Loss: 0.011501 | dt: 449ms | Remaining: 50s
Step 0435 | Loss: 0.011381 | dt: 450ms | Remaining: 47s
Step 0440 | Loss: 0.012176 | dt: 462ms | Remaining: 45s
Step 0445 | Loss: 0.010969 | dt: 460ms | Remaining: 43s
Step 0450 | Loss: 0.011215 | dt: 449ms | Remaining: 38s
Step 0455 | Loss: 0.011277 | dt: 448ms | Remaining: 36s
Step 0460 | Loss: 0.011877 | dt: 448ms | Remaining: 34s
Step 0465 | Loss: 0.011552 | dt: 448ms | Remaining: 31s
Step 0470 | Loss: 0.010887 | dt: 449ms | Remaining: 27s
Step 0475 | Loss: 0.012129 | dt: 452ms | Remaining: 25s
Step 0480 | Loss: 0.012974 | dt: 448ms | Remaining: 22s
Step 0485 | Loss: 0.012754 | dt: 451ms | Remaining: 20s
Step 0490 | Loss: 0.012234 | dt: 2006ms | Remaining: 16s
Step 0495 | Loss: 0.009947 | dt: 452ms | Remaining: 14s
Step 0500 | Loss: 0.008298 | dt: 449ms | Remaining: 12s
Step 0505 | Loss: 0.007988 | dt: 448ms | Remaining: 9s
Step 0510 | Loss: 0.008538 | dt: 449ms | Remaining: 7s
Step 0515 | Loss: 0.009750 | dt: 453ms | Remaining: 4s
Step 0520 | Loss: 0.008918 | dt: 459ms | Remaining: 2s
Step 0525 | Loss: 0.009186 | dt: 448ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.002050
train_loss:       0.009186
training_seconds: 300.1
total_seconds:    301.9
peak_vram_mb:     22406.7
num_steps:        526
num_params_M:     2.262
throughput_Mvps:  0.69

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_084
- **Tweak**: blocks_14
- **Status**: REVERTED
- **Timestamp**: 22:18:45

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64

## Run Output (Tail)
```
047527 | dt: 383ms | Remaining: 148s
Step 0330 | Loss: 0.047052 | dt: 372ms | Remaining: 146s
Step 0335 | Loss: 0.052178 | dt: 372ms | Remaining: 144s
Step 0340 | Loss: 0.045834 | dt: 371ms | Remaining: 142s
Step 0345 | Loss: 0.035620 | dt: 371ms | Remaining: 139s
Step 0350 | Loss: 0.029289 | dt: 371ms | Remaining: 137s
Step 0355 | Loss: 0.024294 | dt: 371ms | Remaining: 135s
Step 0360 | Loss: 0.021356 | dt: 371ms | Remaining: 133s
Step 0365 | Loss: 0.037169 | dt: 371ms | Remaining: 129s
Step 0370 | Loss: 0.055879 | dt: 371ms | Remaining: 127s
Step 0375 | Loss: 0.064904 | dt: 371ms | Remaining: 125s
Step 0380 | Loss: 0.067407 | dt: 371ms | Remaining: 123s
Step 0385 | Loss: 0.052286 | dt: 371ms | Remaining: 121s
Step 0390 | Loss: 0.037252 | dt: 371ms | Remaining: 119s
Step 0395 | Loss: 0.028895 | dt: 371ms | Remaining: 117s
Step 0400 | Loss: 0.022170 | dt: 371ms | Remaining: 115s
Step 0405 | Loss: 0.019428 | dt: 934ms | Remaining: 113s
Step 0410 | Loss: 0.017766 | dt: 371ms | Remaining: 111s
Step 0415 | Loss: 0.015638 | dt: 373ms | Remaining: 109s
Step 0420 | Loss: 0.014799 | dt: 371ms | Remaining: 107s
Step 0425 | Loss: 0.014746 | dt: 371ms | Remaining: 106s
Step 0430 | Loss: 0.033910 | dt: 372ms | Remaining: 101s
Step 0435 | Loss: 0.041377 | dt: 371ms | Remaining: 99s
Step 0440 | Loss: 0.045564 | dt: 371ms | Remaining: 97s
Step 0445 | Loss: 0.040566 | dt: 372ms | Remaining: 96s
Step 0450 | Loss: 0.033346 | dt: 371ms | Remaining: 92s
Step 0455 | Loss: 0.025404 | dt: 371ms | Remaining: 90s
Step 0460 | Loss: 0.020374 | dt: 372ms | Remaining: 88s
Step 0465 | Loss: 0.017638 | dt: 371ms | Remaining: 87s
Step 0470 | Loss: 0.015412 | dt: 385ms | Remaining: 84s
Step 0475 | Loss: 0.015004 | dt: 371ms | Remaining: 82s
Step 0480 | Loss: 0.014363 | dt: 371ms | Remaining: 80s
Step 0485 | Loss: 0.014623 | dt: 372ms | Remaining: 78s
Step 0490 | Loss: 0.014734 | dt: 965ms | Remaining: 76s
Step 0495 | Loss: 0.015017 | dt: 387ms | Remaining: 74s
Step 0500 | Loss: 0.015216 | dt: 373ms | Remaining: 72s
Step 0505 | Loss: 0.015100 | dt: 374ms | Remaining: 70s
Step 0510 | Loss: 0.015261 | dt: 372ms | Remaining: 68s
Step 0515 | Loss: 0.028396 | dt: 371ms | Remaining: 63s
Step 0520 | Loss: 0.039160 | dt: 371ms | Remaining: 61s
Step 0525 | Loss: 0.063316 | dt: 371ms | Remaining: 59s
Step 0530 | Loss: 0.104291 | dt: 372ms | Remaining: 58s
Step 0535 | Loss: 0.171481 | dt: 371ms | Remaining: 55s
Step 0540 | Loss: 0.114810 | dt: 383ms | Remaining: 53s
Step 0545 | Loss: 0.085250 | dt: 371ms | Remaining: 51s
Step 0550 | Loss: 0.065259 | dt: 370ms | Remaining: 50s
Step 0555 | Loss: 0.124277 | dt: 372ms | Remaining: 46s
Step 0560 | Loss: 0.308877 | dt: 381ms | Remaining: 44s
Step 0565 | Loss: 0.210250 | dt: 372ms | Remaining: 42s
Step 0570 | Loss: 0.157977 | dt: 371ms | Remaining: 40s
Step 0575 | Loss: 0.103054 | dt: 371ms | Remaining: 38s
Step 0580 | Loss: 0.065813 | dt: 373ms | Remaining: 36s
Step 0585 | Loss: 0.043917 | dt: 371ms | Remaining: 34s
Step 0590 | Loss: 0.031001 | dt: 371ms | Remaining: 32s
Step 0595 | Loss: 0.022791 | dt: 371ms | Remaining: 30s
Step 0600 | Loss: 0.031400 | dt: 371ms | Remaining: 26s
Step 0605 | Loss: 0.026043 | dt: 371ms | Remaining: 24s
Step 0610 | Loss: 0.048034 | dt: 371ms | Remaining: 22s
Step 0615 | Loss: 0.048667 | dt: 371ms | Remaining: 20s
Step 0620 | Loss: 0.061023 | dt: 371ms | Remaining: 18s
Step 0625 | Loss: 0.040940 | dt: 372ms | Remaining: 16s
Step 0630 | Loss: 0.029116 | dt: 371ms | Remaining: 14s
Step 0635 | Loss: 0.022089 | dt: 371ms | Remaining: 12s
Step 0640 | Loss: 0.046445 | dt: 3830ms | Remaining: 7s
Step 0645 | Loss: 0.062188 | dt: 371ms | Remaining: 5s
Step 0650 | Loss: 0.067778 | dt: 373ms | Remaining: 3s
Step 0655 | Loss: 0.049620 | dt: 371ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.005858
train_loss:       0.046783
training_seconds: 300.1
total_seconds:    301.9
peak_vram_mb:     19521.0
num_steps:        660
num_params_M:     1.770
throughput_Mvps:  0.86

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

# Night Shift Log: 2026-03-22_085
- **Tweak**: patch_size_48
- **Status**: REVERTED
- **Timestamp**: 22:23:54

## Dataset & Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 48

## Run Output (Tail)
```
: 0.055281 | dt: 260ms | Remaining: 130s
Step 0545 | Loss: 0.042509 | dt: 248ms | Remaining: 129s
Step 0550 | Loss: 0.035044 | dt: 248ms | Remaining: 128s
Step 0555 | Loss: 0.035788 | dt: 252ms | Remaining: 124s
Step 0560 | Loss: 0.046655 | dt: 259ms | Remaining: 123s
Step 0565 | Loss: 0.043823 | dt: 248ms | Remaining: 122s
Step 0570 | Loss: 0.048020 | dt: 253ms | Remaining: 120s
Step 0575 | Loss: 0.049521 | dt: 253ms | Remaining: 119s
Step 0580 | Loss: 0.042505 | dt: 248ms | Remaining: 116s
Step 0585 | Loss: 0.036823 | dt: 247ms | Remaining: 114s
Step 0590 | Loss: 0.033125 | dt: 247ms | Remaining: 113s
Step 0595 | Loss: 0.030261 | dt: 257ms | Remaining: 112s
Step 0600 | Loss: 0.025733 | dt: 247ms | Remaining: 109s
Step 0605 | Loss: 0.020256 | dt: 250ms | Remaining: 108s
Step 0610 | Loss: 0.017857 | dt: 247ms | Remaining: 106s
Step 0615 | Loss: 0.017006 | dt: 250ms | Remaining: 105s
Step 0620 | Loss: 0.024400 | dt: 256ms | Remaining: 99s
Step 0625 | Loss: 0.026904 | dt: 251ms | Remaining: 98s
Step 0630 | Loss: 0.031936 | dt: 268ms | Remaining: 96s
Step 0635 | Loss: 0.036137 | dt: 298ms | Remaining: 95s
Step 0640 | Loss: 0.041587 | dt: 2929ms | Remaining: 91s
Step 0645 | Loss: 0.038016 | dt: 248ms | Remaining: 90s
Step 0650 | Loss: 0.035164 | dt: 262ms | Remaining: 88s
Step 0655 | Loss: 0.029898 | dt: 265ms | Remaining: 87s
Step 0660 | Loss: 0.032625 | dt: 269ms | Remaining: 86s
Step 0665 | Loss: 0.036453 | dt: 252ms | Remaining: 79s
Step 0670 | Loss: 0.035549 | dt: 277ms | Remaining: 78s
Step 0675 | Loss: 0.035191 | dt: 248ms | Remaining: 77s
Step 0680 | Loss: 0.036037 | dt: 271ms | Remaining: 75s
Step 0685 | Loss: 0.031615 | dt: 251ms | Remaining: 71s
Step 0690 | Loss: 0.027652 | dt: 277ms | Remaining: 70s
Step 0695 | Loss: 0.025777 | dt: 254ms | Remaining: 69s
Step 0700 | Loss: 0.024686 | dt: 257ms | Remaining: 67s
Step 0705 | Loss: 0.022224 | dt: 249ms | Remaining: 65s
Step 0710 | Loss: 0.020416 | dt: 256ms | Remaining: 64s
Step 0715 | Loss: 0.019537 | dt: 252ms | Remaining: 63s
Step 0720 | Loss: 0.020272 | dt: 256ms | Remaining: 62s
Step 0725 | Loss: 0.019858 | dt: 4857ms | Remaining: 56s
Step 0730 | Loss: 0.026857 | dt: 251ms | Remaining: 54s
Step 0735 | Loss: 0.033275 | dt: 253ms | Remaining: 53s
Step 0740 | Loss: 0.041037 | dt: 247ms | Remaining: 52s
Step 0745 | Loss: 0.041921 | dt: 247ms | Remaining: 51s
Step 0750 | Loss: 0.042385 | dt: 248ms | Remaining: 42s
Step 0755 | Loss: 0.044665 | dt: 247ms | Remaining: 41s
Step 0760 | Loss: 0.042891 | dt: 247ms | Remaining: 40s
Step 0765 | Loss: 0.043205 | dt: 249ms | Remaining: 39s
Step 0770 | Loss: 0.037627 | dt: 255ms | Remaining: 37s
Step 0775 | Loss: 0.032561 | dt: 249ms | Remaining: 36s
Step 0780 | Loss: 0.028986 | dt: 248ms | Remaining: 34s
Step 0785 | Loss: 0.028556 | dt: 248ms | Remaining: 33s
Step 0790 | Loss: 0.028508 | dt: 247ms | Remaining: 32s
Step 0795 | Loss: 0.029690 | dt: 261ms | Remaining: 30s
Step 0800 | Loss: 0.029246 | dt: 250ms | Remaining: 29s
Step 0805 | Loss: 0.029432 | dt: 249ms | Remaining: 28s
Step 0810 | Loss: 0.027624 | dt: 2179ms | Remaining: 25s
Step 0815 | Loss: 0.030361 | dt: 247ms | Remaining: 23s
Step 0820 | Loss: 0.033554 | dt: 253ms | Remaining: 22s
Step 0825 | Loss: 0.031739 | dt: 250ms | Remaining: 21s
Step 0830 | Loss: 0.030617 | dt: 248ms | Remaining: 20s
Step 0835 | Loss: 0.027435 | dt: 248ms | Remaining: 16s
Step 0840 | Loss: 0.024530 | dt: 249ms | Remaining: 15s
Step 0845 | Loss: 0.024181 | dt: 251ms | Remaining: 14s
Step 0850 | Loss: 0.024084 | dt: 260ms | Remaining: 13s
Step 0855 | Loss: 0.028704 | dt: 249ms | Remaining: 7s
Step 0860 | Loss: 0.035326 | dt: 267ms | Remaining: 6s
Step 0865 | Loss: 0.038876 | dt: 247ms | Remaining: 4s
Step 0870 | Loss: 0.043805 | dt: 248ms | Remaining: 3s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.001750
train_loss:       0.045202
training_seconds: 301.1
total_seconds:    302.8
peak_vram_mb:     12675.9
num_steps:        875
num_params_M:     2.262
throughput_Mvps:  0.64

[RESULT] No improvement detected. Recommended: Revert changes.

```

---
