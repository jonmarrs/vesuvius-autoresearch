import sys

sys.stdout.reconfigure(line_buffering=True)
import os

sys.path.append(os.path.abspath("villa/vesuvius/src"))
sys.path.append(os.path.abspath("villa/ink-detection"))
print("1")
print("2")
try:
    from vesuvius.image_proc.geometry.structure_tensor import StructureTensorComputer
except ImportError:
    pass
print("3")
try:
    from models.resnetall import generate_model as generate_resnet3d
except ImportError:
    pass
print("4")
try:
    from models.i3dallnl import InceptionI3d
except ImportError:
    pass
print("5")
try:
    from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
    from dynamic_network_architectures.building_blocks.helper import (
        convert_dim_to_conv_op,
        get_matching_instancenorm,
    )
except ImportError:
    pass
print("6")
try:
    from vesuvius.models.augmentation.pipelines.training_transforms import (
        create_training_transforms,
    )
except ImportError:
    pass
print("7")
try:
    import albumentations as A
except ImportError:
    pass
print("8")
print("9")
print("10")
