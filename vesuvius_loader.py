import torch
from torch.utils.data import Dataset
class FastVesuviusVolume:
    def __init__(self, *args, **kwargs): self.shape = (16, 1024, 1024)
    def __getitem__(self, key): return torch.zeros((16, 64, 64))
class VesuviusLabeledDataset(Dataset):
    def __init__(self, *args, **kwargs): self.shape = (16, 1024, 1024)
    def __len__(self): return 10
    def __getitem__(self, idx): return torch.zeros((1, 16, 64, 64)), torch.zeros((64, 64))
class VesuviusS3Dataset(Dataset):
    def __init__(self, *args, **kwargs): self.shape = (16, 1024, 1024)
    def __len__(self): return 10
    def __getitem__(self, idx): return torch.zeros((1, 16, 64, 64)), torch.zeros((64, 64))
