"""A stand-in for wandb, first on the path when the 2023 Grand Prize inference script runs (finding 122).

The script calls wandb.init and logs its prediction images, which would send them to wandb's servers. Every call
here does nothing and nothing is imported that could reach the network.
"""


class Image:
    def __init__(self, *args, **kwargs):
        pass


def init(*args, **kwargs):
    return None


def log(*args, **kwargs):
    return None


def finish(*args, **kwargs):
    return None
