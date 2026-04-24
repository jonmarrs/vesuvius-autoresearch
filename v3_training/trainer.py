import torch
import torch.nn as nn
import torch.nn.functional as F
import sys
import os
import numpy as np

# Add project root and villa paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VILLA_TRAIN_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "villa/segmentation/models/multi-task-3d-unet"))
VILLA_SRC = os.path.abspath(os.path.join(PROJECT_ROOT, "villa/vesuvius/src"))

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if VILLA_TRAIN_PATH not in sys.path:
    sys.path.append(VILLA_TRAIN_PATH)
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)

from vesuvius_model import InkDetectorOptimized, VesuviusConfig
from vesuvius_loader import VesuviusLabeledDataset, VesuviusS3Dataset
from training.trainers.basetrainer import BaseTrainer
from torch.utils.data import DataLoader
from vesuvius.models.training.trainers.semi_supervised.two_stream_batch_sampler import TwoStreamBatchSampler
from vesuvius.models.training.trainers.semi_supervised import ramps
from vesuvius.models.training.loss.sigreg import SIGRegLoss

class VesuviusTrainer(BaseTrainer):
    """
    Enhanced Vesuvius Trainer.
    Supports:
    1. Challenge Standard Multi-task Learning
    2. Uncertainty-Aware Mean Teacher (UA-MT) - Sprint 020
    3. LeJEPA Self-Supervised Pretraining (SIGReg) - Sprint 019
    """
    
    def __init__(self, config_file: str, verbose: bool = True, debug_dataloader: bool = False):
        super().__init__(config_file, verbose, debug_dataloader)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # SSL Configs
        self.use_uamt = self.mgr.tr_configs.get('use_uamt', False)
        self.use_lejepa = self.mgr.tr_configs.get('use_lejepa', False)
        
        if self.use_uamt:
            self.ema_decay = self.mgr.tr_configs.get('ema_decay', 0.99)
            self.consistency_weight = self.mgr.tr_configs.get('consistency_weight', 0.1)
            self.consistency_rampup = self.mgr.tr_configs.get('consistency_rampup', 200)
            self.uncertainty_T = self.mgr.tr_configs.get('uncertainty_T', 4)
            self.labeled_bs = self.mgr.tr_configs.get('labeled_batch_size', self.mgr.train_batch_size // 2)

        if self.use_lejepa:
            self.sigreg = SIGRegLoss(num_slices=256, lambd=self.mgr.tr_configs.get('sigreg_lambda', 0.02))

    def _get_loss(self):
        return {
            "ink": nn.BCEWithLogitsLoss(),
            "fiber": nn.BCEWithLogitsLoss(),
            "surface_normals": nn.MSELoss(),
            "distance_transform": nn.L1Loss(),
            "structure_tensor": nn.MSELoss()
        }

    def _build_model(self):
        print("--- Building v3.1.0 Omni-Sensing Model ---")
        config = self.mgr
        v_config = VesuviusConfig(
            patch_size=config.train_patch_size[1],
            num_layers=config.train_patch_size[0],
            base_feat=config.model_config.get('base_feat', 64),
            in_channels=config.model_config.get('in_channels', 1)
        )
        model = InkDetectorOptimized(v_config)
        # Dynamic Multi-task heads
        model.surface_normal_head = nn.Conv3d(v_config.base_feat // 4, 3, kernel_size=1)
        model.dist_transform_head = nn.Conv3d(v_config.base_feat // 4, 1, kernel_size=1)
        model.st_head = nn.Conv3d(v_config.base_feat // 4, 6, kernel_size=1)
        model.to(self.device)
        return model

    def _build_dataloaders(self):
        config = self.mgr
        # Note: In LeJEPA mode, we only need unlabeled data
        if self.use_lejepa:
             ds = VesuviusS3Dataset(
                uri=os.path.join(PROJECT_ROOT, "local_data/PHerc0139_div_0_1GB/0/"),
                patch_size=config.train_patch_size[1],
                num_layers=config.train_patch_size[0],
                is_unlabeled=True
            )
             loader = DataLoader(ds, batch_size=config.train_batch_size, shuffle=True, 
                                 num_workers=config.train_num_dataloader_workers)
             return loader, None

        # Labeled dataset path
        target_name = list(config.targets.keys())[0]
        vol_info = config.targets[target_name]['volumes'][0]
        ds_labeled = VesuviusLabeledDataset(
            volume_uri=os.path.join(PROJECT_ROOT, vol_info.get('data_volume')),
            labels_path=os.path.join(PROJECT_ROOT, vol_info.get('label_volume')),
            mask_path=os.path.join(PROJECT_ROOT, vol_info.get('mask_volume')) if vol_info.get('mask_volume') else None,
            patch_size=config.train_patch_size[1],
            num_layers=config.train_patch_size[0],
            is_unlabeled=False
        )

        if not self.use_uamt:
            dataset_size = len(ds_labeled)
            indices = list(range(dataset_size))
            split = int(np.floor(config.tr_val_split * dataset_size))
            np.random.shuffle(indices)
            train_loader = DataLoader(ds_labeled, batch_size=config.train_batch_size, 
                                     sampler=torch.utils.data.SubsetRandomSampler(indices[:split]), 
                                     num_workers=config.train_num_dataloader_workers)
            val_loader = DataLoader(ds_labeled, batch_size=config.train_batch_size, 
                                   sampler=torch.utils.data.SubsetRandomSampler(indices[split:]), 
                                   num_workers=config.train_num_dataloader_workers)
            return train_loader, val_loader

        # UA-MT mixing logic...
        ds_unlabeled = VesuviusS3Dataset(
            uri=os.path.join(PROJECT_ROOT, "local_data/PHerc0139_div_0_1GB/0/"),
            patch_size=config.train_patch_size[1],
            num_layers=config.train_patch_size[0],
            is_unlabeled=True
        )
        ds_combined = ds_labeled + ds_unlabeled
        labeled_indices = list(range(len(ds_labeled)))
        unlabeled_indices = list(range(len(ds_labeled), len(ds_combined)))
        batch_sampler = TwoStreamBatchSampler(labeled_indices, unlabeled_indices, config.train_batch_size, config.train_batch_size - self.labeled_bs)
        train_loader = DataLoader(ds_combined, batch_sampler=batch_sampler, num_workers=config.train_num_dataloader_workers)
        val_loader = DataLoader(ds_labeled, batch_size=config.train_batch_size, num_workers=config.train_num_dataloader_workers)
        return train_loader, val_loader

    def train(self):
        if self.use_lejepa:
            return self._train_lejepa()
        if self.use_uamt:
            return self._train_uamt()
        return super().train()

    def _train_lejepa(self):
        print("Starting LeJEPA Foundation Pretraining (SIGReg)...")
        model = self._build_model()
        optimizer = self._get_optimizer(model)
        train_loader, _ = self._build_dataloaders()
        
        global_step = 0
        for epoch in range(self.mgr.max_epoch):
            model.train()
            for i, (img, _) in enumerate(train_loader):
                img = img.to(self.device)
                
                # Multi-view generation (simplified LeJEPA)
                # In a full LeJEPA we'd use local/global crops
                # Here we use two augmented views of the same patch
                # using our integrated batchgeneratorsv2 pipeline
                
                # Forward with return_proj=True to get embeddings
                out1, proj1 = model(img, return_proj=True)
                
                # View 2
                with torch.no_grad():
                    img2 = img + torch.randn_like(img) * 0.05 # Simple noise view
                out2, proj2 = model(img2, return_proj=True)
                
                # SIGReg Loss
                # sigreg expects (V_g, B, K) for global, (V, B, K) for all
                global_projs = proj1.unsqueeze(0) # [1, B, K]
                all_projs = torch.stack([proj1, proj2]) # [2, B, K]
                
                loss, loss_dict = self.sigreg(global_projs, all_projs, global_step)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                global_step += 1
                if global_step % 10 == 0:
                    print(f"Step {global_step} | Loss: {loss.item():.4f} | Invar: {loss_dict['invariance_loss']:.4f} | SIGReg: {loss_dict['sigreg_loss']:.4f}")

    def _train_uamt(self):
        print(f"Starting UA-MT Training with labeled_bs={self.labeled_bs}")
        model = self._build_model()
        ema_model = self._build_model()
        for param in ema_model.parameters():
            param.detach_()
            
        optimizer = self._get_optimizer(model)
        train_loader, val_loader = self._build_dataloaders()
        
        global_step = 0
        for epoch in range(self.mgr.max_epoch):
            model.train()
            for i, (img, target) in enumerate(train_loader):
                img, target = img.to(self.device), target.to(self.device)
                
                # Forward student
                outputs = model(img)
                if isinstance(outputs, tuple): outputs = outputs[0]
                
                # Loss on labeled samples only
                loss_seg = F.binary_cross_entropy_with_logits(outputs[:self.labeled_bs], target[:self.labeled_bs].unsqueeze(1))
                
                # Consistency with Teacher (EMA)
                with torch.no_grad():
                    # UA-MT: multiple forward passes for uncertainty estimation
                    ema_inputs = img[self.labeled_bs:].repeat(self.uncertainty_T, 1, 1, 1, 1)
                    ema_inputs += torch.clamp(torch.randn_like(ema_inputs) * 0.1, -0.2, 0.2)
                    
                    ema_out = ema_model(ema_inputs)
                    if isinstance(ema_out, tuple): ema_out = ema_out[0]
                    
                    T, B_u, C, H, W = self.uncertainty_T, img.shape[0] - self.labeled_bs, 1, img.shape[3], img.shape[4]
                    ema_out = ema_out.reshape(T, B_u, C, H, W)
                    
                    ema_prob = torch.sigmoid(ema_out)
                    ema_avg_prob = ema_prob.mean(dim=0)
                    uncertainty = -1.0 * torch.sum(ema_avg_prob * torch.log(ema_avg_prob + 1e-6), dim=1, keepdim=True)
                
                # Consistency loss (MSE) weighted by uncertainty
                consistency_dist = (torch.sigmoid(outputs[self.labeled_bs:]) - ema_avg_prob) ** 2
                threshold = (0.75 + (1.0 - 0.75) * ramps.sigmoid_rampup(epoch, self.consistency_rampup))
                mask = (uncertainty < threshold).float()
                
                consistency_loss = (consistency_dist * mask).sum() / (mask.sum() + 1e-6)
                consistency_weight = self.consistency_weight * ramps.sigmoid_rampup(epoch, self.consistency_rampup)
                
                total_loss = loss_seg + consistency_weight * consistency_loss
                
                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()
                
                self._update_ema_variables(model, ema_model, self.ema_decay, global_step)
                global_step += 1
                
                if global_step % 10 == 0:
                    print(f"Step {global_step} | Loss Seg: {loss_seg.item():.4f} | Cons: {consistency_loss.item():.4f}")

if __name__ == "__main__":
    from configuration.config_manager import ConfigManager
    config_path = os.path.join(os.path.dirname(__file__), "task.yaml")
    if os.path.exists(config_path):
        trainer = VesuviusTrainer(config_path)
        print("Trainer initialized successfully.")
    else:
        print(f"Config {config_path} not found.")
