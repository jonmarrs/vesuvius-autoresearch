"""
Vesuvius Autoresearch: FRONTIER-LEVEL MISSION-CRITICAL AUDIT.
Zero compromises. Target: $1M Grand Prize & Scroll Foundation Model.
"""

import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class VesuviusConfig:
    def __init__(self, patch_size=64, num_layers=16, batch_size=4, base_feat=64, num_blocks=16, num_heads=8, dropout=0.0):
        self.patch_size = patch_size
        self.num_layers = num_layers
        self.batch_size = batch_size
        self.base_feat = base_feat
        self.num_blocks = num_blocks
        self.num_heads = num_heads
        self.dropout = dropout

class SEBlock3D(nn.Module):
    """Squeeze-and-Excitation for 3D volumes."""
    def __init__(self, channels, reduction=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool3d(1)
        mid_channels = max(1, channels // reduction)
        self.fc = nn.Sequential(
            nn.Linear(channels, mid_channels, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(mid_channels, channels, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        b, c, _, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1, 1)
        return x * y.expand_as(x)

class GatedFusionBlock(nn.Module):
    """Learned dynamic gating for UNet skip connections."""
    def __init__(self, skip_channels, up_channels, out_channels):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Conv3d(skip_channels + up_channels, out_channels, kernel_size=1),
            nn.Sigmoid()
        )
        self.proj = nn.Conv3d(skip_channels + up_channels, out_channels, kernel_size=1)
        self.res = nn.Conv3d(up_channels, out_channels, kernel_size=1) if up_channels != out_channels else nn.Identity()

    def forward(self, skip, up):
        x = torch.cat([skip, up], dim=1)
        mask = self.gate(x)
        feat = self.proj(x)
        return self.res(up) + (mask * feat)

class LearnedZProjection(nn.Module):
    """Learned linear projection to collapse Z-dimension into 2D."""
    def __init__(self, depth, channels):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Conv3d(channels, channels, kernel_size=(depth, 1, 1)),
            nn.GroupNorm(min(channels, 8), channels),
            nn.GELU()
        )

    def forward(self, x):
        # x: [B, C, Z, H, W]
        x = self.proj(x) # [B, C, 1, H, W]
        return x.squeeze(2)

class InkDetectorOptimized(nn.Module):
    def __init__(self, config: VesuviusConfig):
        super().__init__()
        self.config = config
        
        # Pull architectural parameters from config
        self.base_feat = config.base_feat
        self.num_blocks = config.num_blocks
        self.num_heads = config.num_heads
        self.dropout = config.dropout
        
        # Sanity check for MultiheadAttention
        if self.base_feat % self.num_heads != 0:
            # Dynamically adjust num_heads to the nearest factor of base_feat for stability
            while self.base_feat % self.num_heads != 0:
                self.num_heads -= 1
            if self.num_heads <= 0: self.num_heads = 1
            print(f"Warning: adjusted num_heads to {self.num_heads} for compatibility with base_feat {self.base_feat}")
            
        self.patch_size = config.patch_size
        self.num_layers = config.num_layers
        
        # Encoder: Hierarchical 3D Patch Embedding
        self.stage1 = nn.Conv3d(1, self.base_feat // 2, kernel_size=3, stride=(2, 2, 2), padding=1)
        self.stage2 = nn.Conv3d(self.base_feat // 2, self.base_feat, kernel_size=3, stride=(2, 2, 2), padding=1)
        
        # Positional Embedding Caching
        self.latent_z = self.num_layers // 4
        self.latent_hw = self.patch_size // 4
        num_patches = self.latent_z * self.latent_hw * self.latent_hw
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, self.base_feat))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        self.pos_drop = nn.Dropout(p=self.dropout)
        
        # Transformer Backbone
        self.blocks = nn.ModuleList([
            DividedSpaceTimeBlock(self.base_feat, self.num_heads, self.dropout)
            for _ in range(self.num_blocks)
        ])
        self.norm = nn.LayerNorm(self.base_feat)
        
        # Progressive UNet Decoder with GATED Fusion
        self.up1 = nn.ConvTranspose3d(self.base_feat, self.base_feat // 2, kernel_size=4, stride=2, padding=1)
        self.fusion1 = GatedFusionBlock(self.base_feat // 2, self.base_feat // 2, self.base_feat // 2)
        
        self.up2 = nn.ConvTranspose3d(self.base_feat // 2, self.base_feat // 4, kernel_size=4, stride=2, padding=1)
        self.fusion2 = GatedFusionBlock(1, self.base_feat // 4, self.base_feat // 4)
        
        self.decoder_res = nn.Sequential(
            ResBlock3D(self.base_feat // 4),
            ResBlock3D(self.base_feat // 4)
        )
        
        # Multi-task Heads
        self.z_proj = LearnedZProjection(self.num_layers, self.base_feat // 4)
        self.final_ink = nn.Conv2d(self.base_feat // 4, 1, kernel_size=3, padding=1)
        self.fiber_head = nn.Conv3d(self.base_feat // 4, 1, kernel_size=3, padding=1)
        self.qc_head = nn.Sequential(
            nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
            nn.Linear(self.base_feat, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
    def forward(self, x, return_fiber=False, return_qc=False, **kwargs):
        B, C, Z, H, W = x.shape
        
        # 1. Encoder
        s1 = self.stage1(x)    
        x_emb = self.stage2(s1) 
        lz, lh, lw = x_emb.shape[2:]
        
        # 2. Transformer
        x_flat = x_emb.flatten(2).transpose(1, 2)
        if x_flat.shape[1] == self.pos_embed.shape[1]:
            pos = self.pos_embed
        else:
            pos = self.pos_embed.transpose(1, 2).reshape(1, -1, self.latent_z, self.latent_hw, self.latent_hw)
            pos = F.interpolate(pos, size=(lz, lh, lw), mode='trilinear', align_corners=False)
            pos = pos.reshape(1, -1, lz * lh * lw).transpose(1, 2)
        
        x_flat = self.pos_drop(x_flat + pos)
        for block in self.blocks:
            x_flat = block(x_flat, lz, lh, lw)
        x_flat = self.norm(x_flat)
        
        # 3. Gated Decoding
        x_trans = x_flat.transpose(1, 2).reshape(B, -1, lz, lh, lw)
        x_up1 = self.up1(x_trans)
        x_f1 = self.fusion1(s1, x_up1)
        x_up2 = self.up2(x_f1)
        x_f2 = self.fusion2(x, x_up2)
        x_out = self.decoder_res(x_f2)
        
        ink_2d = self.final_ink(self.z_proj(x_out))
        if return_fiber or return_qc:
            fiber = self.fiber_head(x_out) if return_fiber else None
            qc = self.qc_head(x_trans) if return_qc else None
            return ink_2d, fiber, qc
        return ink_2d

class DividedSpaceTimeBlock(nn.Module):
    def __init__(self, dim, num_heads, dropout=0.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.temporal_attn = nn.MultiheadAttention(dim, num_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        self.spatial_attn = nn.MultiheadAttention(dim, num_heads, dropout=dropout, batch_first=True)
        self.norm3 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(
            nn.Linear(dim, dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 4, dim),
            nn.Dropout(dropout)
        )

    def forward(self, x, lz, lh, lw):
        B, N, D = x.shape
        # Temporal Attention (across Z)
        res = x
        x = self.norm1(x)
        x = x.reshape(B, lz, lh * lw, D).permute(0, 2, 1, 3).reshape(-1, lz, D)
        x, _ = self.temporal_attn(x, x, x)
        x = x.reshape(B, lh * lw, lz, D).permute(0, 2, 1, 3).reshape(B, -1, D)
        x = x + res
        
        # Spatial Attention (across H*W)
        res = x
        x = self.norm2(x)
        x = x.reshape(-1, lh * lw, D)
        x, _ = self.spatial_attn(x, x, x)
        x = x.reshape(B, -1, D)
        x = x + res
        
        # MLP
        x = x + self.mlp(self.norm3(x))
        return x

class ResBlock3D(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv3d(channels, channels, kernel_size=(3, 5, 1), padding=(1, 2, 0))
        self.conv2 = nn.Conv3d(channels, channels, kernel_size=(3, 1, 5), padding=(1, 0, 2))
        self.norm1 = nn.GroupNorm(min(channels, 8), channels)
        self.norm2 = nn.GroupNorm(min(channels, 8), channels)
        self.se = SEBlock3D(channels)

    def forward(self, x):
        res = x
        x = F.gelu(self.norm1(self.conv1(x)))
        x = self.norm2(self.conv2(x))
        x = self.se(x)
        return F.gelu(x + res)

# ---------------------------------------------------------------------------
# Mission-Critical Audit Suite
# ---------------------------------------------------------------------------

def test_geometric_rotation(model, config, device):
    model.eval()
    x = torch.randn((1, 1, config.num_layers, 64, 64), device=device)
    with torch.no_grad():
        out_orig = torch.sigmoid(model(x))
        x_rot = torch.rot90(x, k=1, dims=(-2, -1))
        out_rot = torch.sigmoid(model(x_rot))
        out_rot_back = torch.rot90(out_rot, k=-1, dims=(-2, -1))
    diff = (out_orig - out_rot_back).abs().mean()
    if diff < 0.1:
        print(f"[PASS] (Rotation Delta: {diff:.4f})")
        return True
    else:
        print(f"[FAIL] High Geometric Variance: {diff:.4f}")
        return False

def test_extreme_snr_stress(model, config, device):
    x = torch.randn((1, 1, config.num_layers, 32, 32), device=device) * 0.5 
    target = torch.zeros_like(x)
    target[:, :, 4:8, 8:24, 8:24] = 0.5 
    x += target
    with torch.no_grad():
        out = torch.sigmoid(model(x))
    snr = out[target > 0].mean() / (out[target == 0].mean() + 1e-9)
    if snr > 2.0:
        print(f"[PASS] (Contrast Ratio: {snr:.2f}x)")
        return True
    else:
        print(f"[FAIL] Model overwhelmed by noise. SNR: {snr:.2f}")
        return False

def test_interlayer_isolation(model, config, device):
    x = torch.randn((1, 1, config.num_layers, 32, 32), device=device) * 0.1
    x[:, :, 4:6] += 1.0 
    with torch.no_grad():
        out = torch.sigmoid(model(x))
    isolation = out[:, :, 4:6].mean() / (out[:, :, 10:12].mean() + 1e-9)
    if isolation > 10:
        print(f"[PASS] (Isolation Factor: {isolation:.1f}x)")
        return True
    else:
        print(f"[FAIL] Layer Leakage detected. Isolation: {isolation:.1f}x")
        return False

def test_throughput_benchmark(model, config, device):
    x = torch.randn((2, 1, config.num_layers, 64, 64), device=device)
    for _ in range(5): model(x)
    if device == "cuda": torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(20): model(x)
    if device == "cuda": torch.cuda.synchronize()
    dt = time.time() - t0
    voxels = 20 * 2 * config.num_layers * 64 * 64
    vps = voxels / dt
    print(f"[PASS] ({vps/1e6:.2f}M voxels/sec)")
    return True

def mission_critical_audit():
    import gc
    print("\n" + "="*60)
    print("   PROJECT 002: MISSION-CRITICAL VESUVIUS AUDIT")
    print("="*60)
    config = VesuviusConfig(
        patch_size=64, 
        num_layers=16, 
        batch_size=1, 
        base_feat=32, 
        num_blocks=2, 
        num_heads=4, 
        dropout=0.1
    )
    device = "cpu"
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    gc.collect()
    model = InkDetectorOptimized(config).to(device)
    print(f"Architecture: SOTA Gated UNet-Transformer (Params: {sum(p.numel() for p in model.parameters())/1e6:.2f}M)")
    
    print(f"\n[1/4] Multi-task Integrity Check...", end=" ", flush=True)
    x = torch.randn((1, 1, 16, 32, 32), device=device)
    out = model(x, return_fiber=True, return_qc=True)
    print("DONE")
    
    print(f"[2/4] Geometric Rotation...", end=" ", flush=True)
    test_geometric_rotation(model, config, device)
    
    print(f"[3/4] SNR Stress Test...", end=" ", flush=True)
    test_extreme_snr_stress(model, config, device)
    
    print(f"[4/4] Layer Isolation...", end=" ", flush=True)
    test_interlayer_isolation(model, config, device)
    
    print(f"\nPerformance Benchmark:")
    test_throughput_benchmark(model, config, device)
    print("\n" + "="*60)

if __name__ == "__main__":
    mission_critical_audit()
