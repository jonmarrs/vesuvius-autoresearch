# Sprint Log: 2026-03-22_sprint_001 (Vesuvius Autoresearch (Night Shift))
- **Start Time**: 22:30:52
- **Goal**: Monotonic val_bpb optimization via 5-min cycles.

## Cycle 1: wd_0.001 (REVERTED)
- **Timestamp**: 22:35:58
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
dt: 450ms | Remaining: 172s
Step 0240 | Loss: 0.019105 | dt: 449ms | Remaining: 170s
Step 0245 | Loss: 0.016242 | dt: 448ms | Remaining: 168s
Step 0250 | Loss: 0.014376 | dt: 449ms | Remaining: 165s
Step 0255 | Loss: 0.012218 | dt: 461ms | Remaining: 163s
Step 0260 | Loss: 0.012227 | dt: 449ms | Remaining: 160s
Step 0265 | Loss: 0.011740 | dt: 448ms | Remaining: 158s
Step 0270 | Loss: 0.010823 | dt: 448ms | Remaining: 156s
Step 0275 | Loss: 0.011078 | dt: 450ms | Remaining: 153s
Step 0280 | Loss: 0.143490 | dt: 449ms | Remaining: 148s
Step 0285 | Loss: 0.184661 | dt: 448ms | Remaining: 146s
Step 0290 | Loss: 0.137028 | dt: 449ms | Remaining: 144s
Step 0295 | Loss: 0.097057 | dt: 449ms | Remaining: 142s
Step 0300 | Loss: 0.073238 | dt: 448ms | Remaining: 139s
Step 0305 | Loss: 0.046169 | dt: 449ms | Remaining: 137s
Step 0310 | Loss: 0.030793 | dt: 450ms | Remaining: 134s
Step 0315 | Loss: 0.021686 | dt: 450ms | Remaining: 132s
Step 0320 | Loss: 0.016259 | dt: 1037ms | Remaining: 129s
Step 0325 | Loss: 0.013009 | dt: 450ms | Remaining: 127s
Step 0330 | Loss: 0.010858 | dt: 448ms | Remaining: 125s
Step 0335 | Loss: 0.009735 | dt: 449ms | Remaining: 123s
Step 0340 | Loss: 0.009189 | dt: 449ms | Remaining: 120s
Step 0345 | Loss: 0.022997 | dt: 449ms | Remaining: 115s
Step 0350 | Loss: 0.023892 | dt: 448ms | Remaining: 113s
Step 0355 | Loss: 0.024451 | dt: 450ms | Remaining: 111s
Step 0360 | Loss: 0.023452 | dt: 449ms | Remaining: 109s
Step 0365 | Loss: 0.018359 | dt: 449ms | Remaining: 106s
Step 0370 | Loss: 0.013133 | dt: 449ms | Remaining: 103s
Step 0375 | Loss: 0.009958 | dt: 456ms | Remaining: 101s
Step 0380 | Loss: 0.008253 | dt: 449ms | Remaining: 99s
Step 0385 | Loss: 0.007209 | dt: 462ms | Remaining: 96s
Step 0390 | Loss: 0.007223 | dt: 462ms | Remaining: 94s
Step 0395 | Loss: 0.006867 | dt: 450ms | Remaining: 92s
Step 0400 | Loss: 0.006661 | dt: 449ms | Remaining: 89s
Step 0405 | Loss: 0.006829 | dt: 1023ms | Remaining: 86s
Step 0410 | Loss: 0.007077 | dt: 449ms | Remaining: 84s
Step 0415 | Loss: 0.006996 | dt: 450ms | Remaining: 82s
Step 0420 | Loss: 0.007352 | dt: 450ms | Remaining: 80s
Step 0425 | Loss: 0.007597 | dt: 449ms | Remaining: 77s
Step 0430 | Loss: 0.023552 | dt: 448ms | Remaining: 73s
Step 0435 | Loss: 0.024699 | dt: 448ms | Remaining: 71s
Step 0440 | Loss: 0.026022 | dt: 454ms | Remaining: 68s
Step 0445 | Loss: 0.034597 | dt: 449ms | Remaining: 66s
Step 0450 | Loss: 0.025685 | dt: 449ms | Remaining: 63s
Step 0455 | Loss: 0.019249 | dt: 449ms | Remaining: 61s
Step 0460 | Loss: 0.016136 | dt: 450ms | Remaining: 59s
Step 0465 | Loss: 0.013874 | dt: 450ms | Remaining: 57s
Step 0470 | Loss: 0.012537 | dt: 459ms | Remaining: 54s
Step 0475 | Loss: 0.012296 | dt: 449ms | Remaining: 51s
Step 0480 | Loss: 0.012160 | dt: 450ms | Remaining: 49s
Step 0485 | Loss: 0.012446 | dt: 450ms | Remaining: 47s
Step 0490 | Loss: 0.022675 | dt: 3606ms | Remaining: 42s
Step 0495 | Loss: 0.032947 | dt: 456ms | Remaining: 39s
Step 0500 | Loss: 0.037388 | dt: 449ms | Remaining: 37s
Step 0505 | Loss: 0.038659 | dt: 448ms | Remaining: 35s
Step 0510 | Loss: 0.043998 | dt: 449ms | Remaining: 33s
Step 0515 | Loss: 0.039548 | dt: 449ms | Remaining: 30s
Step 0520 | Loss: 0.034504 | dt: 449ms | Remaining: 27s
Step 0525 | Loss: 0.030489 | dt: 451ms | Remaining: 25s
Step 0530 | Loss: 0.028327 | dt: 450ms | Remaining: 23s
Step 0535 | Loss: 0.075694 | dt: 448ms | Remaining: 16s
Step 0540 | Loss: 0.114786 | dt: 450ms | Remaining: 14s
Step 0545 | Loss: 0.106472 | dt: 449ms | Remaining: 11s
Step 0550 | Loss: 0.103256 | dt: 451ms | Remaining: 9s
Step 0555 | Loss: 0.082019 | dt: 448ms | Remaining: 6s
Step 0560 | Loss: 0.058814 | dt: 452ms | Remaining: 4s
Step 0565 | Loss: 0.045637 | dt: 448ms | Remaining: 2s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.002049
train_loss:       0.039521
training_seconds: 300.1
total_seconds:    302.2
peak_vram_mb:     22406.7
num_steps:        570
num_params_M:     2.262
throughput_Mvps:  0.75

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 2: patch_size_64 (REVERTED)
- **Timestamp**: 22:41:09
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
: 467ms | Remaining: 178s
Step 0235 | Loss: 0.020108 | dt: 462ms | Remaining: 173s
Step 0240 | Loss: 0.022268 | dt: 450ms | Remaining: 171s
Step 0245 | Loss: 0.023470 | dt: 463ms | Remaining: 168s
Step 0250 | Loss: 0.026006 | dt: 461ms | Remaining: 166s
Step 0255 | Loss: 0.029739 | dt: 504ms | Remaining: 164s
Step 0260 | Loss: 0.028887 | dt: 464ms | Remaining: 161s
Step 0265 | Loss: 0.032354 | dt: 469ms | Remaining: 159s
Step 0270 | Loss: 0.040257 | dt: 464ms | Remaining: 156s
Step 0275 | Loss: 0.046252 | dt: 464ms | Remaining: 154s
Step 0280 | Loss: 0.051266 | dt: 454ms | Remaining: 151s
Step 0285 | Loss: 0.049826 | dt: 450ms | Remaining: 149s
Step 0290 | Loss: 0.041933 | dt: 450ms | Remaining: 146s
Step 0295 | Loss: 0.036570 | dt: 451ms | Remaining: 144s
Step 0300 | Loss: 0.031618 | dt: 455ms | Remaining: 141s
Step 0305 | Loss: 0.027013 | dt: 449ms | Remaining: 139s
Step 0310 | Loss: 0.025428 | dt: 451ms | Remaining: 137s
Step 0315 | Loss: 0.023348 | dt: 448ms | Remaining: 135s
Step 0320 | Loss: 0.022347 | dt: 1042ms | Remaining: 132s
Step 0325 | Loss: 0.021408 | dt: 449ms | Remaining: 129s
Step 0330 | Loss: 0.019230 | dt: 451ms | Remaining: 127s
Step 0335 | Loss: 0.018960 | dt: 449ms | Remaining: 125s
Step 0340 | Loss: 0.018322 | dt: 450ms | Remaining: 123s
Step 0345 | Loss: 0.017898 | dt: 456ms | Remaining: 120s
Step 0350 | Loss: 0.017512 | dt: 449ms | Remaining: 118s
Step 0355 | Loss: 0.019244 | dt: 449ms | Remaining: 115s
Step 0360 | Loss: 0.021464 | dt: 449ms | Remaining: 113s
Step 0365 | Loss: 0.024976 | dt: 450ms | Remaining: 110s
Step 0370 | Loss: 0.030952 | dt: 448ms | Remaining: 108s
Step 0375 | Loss: 0.038643 | dt: 449ms | Remaining: 106s
Step 0380 | Loss: 0.040701 | dt: 449ms | Remaining: 103s
Step 0385 | Loss: 0.073703 | dt: 449ms | Remaining: 98s
Step 0390 | Loss: 0.075444 | dt: 448ms | Remaining: 95s
Step 0395 | Loss: 0.060642 | dt: 450ms | Remaining: 93s
Step 0400 | Loss: 0.046097 | dt: 451ms | Remaining: 91s
Step 0405 | Loss: 0.037600 | dt: 3188ms | Remaining: 86s
Step 0410 | Loss: 0.029105 | dt: 450ms | Remaining: 84s
Step 0415 | Loss: 0.022507 | dt: 449ms | Remaining: 81s
Step 0420 | Loss: 0.019319 | dt: 452ms | Remaining: 79s
Step 0425 | Loss: 0.017540 | dt: 449ms | Remaining: 77s
Step 0430 | Loss: 0.018441 | dt: 448ms | Remaining: 72s
Step 0435 | Loss: 0.020030 | dt: 451ms | Remaining: 70s
Step 0440 | Loss: 0.018716 | dt: 449ms | Remaining: 67s
Step 0445 | Loss: 0.022480 | dt: 449ms | Remaining: 65s
Step 0450 | Loss: 0.019707 | dt: 459ms | Remaining: 62s
Step 0455 | Loss: 0.016824 | dt: 488ms | Remaining: 60s
Step 0460 | Loss: 0.016687 | dt: 485ms | Remaining: 57s
Step 0465 | Loss: 0.016184 | dt: 448ms | Remaining: 55s
Step 0470 | Loss: 0.078778 | dt: 449ms | Remaining: 50s
Step 0475 | Loss: 0.089694 | dt: 449ms | Remaining: 48s
Step 0480 | Loss: 0.077711 | dt: 448ms | Remaining: 45s
Step 0485 | Loss: 0.083945 | dt: 449ms | Remaining: 43s
Step 0490 | Loss: 0.082835 | dt: 3147ms | Remaining: 38s
Step 0495 | Loss: 0.070970 | dt: 450ms | Remaining: 36s
Step 0500 | Loss: 0.056467 | dt: 449ms | Remaining: 34s
Step 0505 | Loss: 0.044579 | dt: 448ms | Remaining: 31s
Step 0510 | Loss: 0.036696 | dt: 449ms | Remaining: 29s
Step 0515 | Loss: 0.027767 | dt: 449ms | Remaining: 26s
Step 0520 | Loss: 0.021282 | dt: 448ms | Remaining: 24s
Step 0525 | Loss: 0.017334 | dt: 449ms | Remaining: 22s
Step 0530 | Loss: 0.014510 | dt: 462ms | Remaining: 20s
Step 0535 | Loss: 0.015008 | dt: 449ms | Remaining: 14s
Step 0540 | Loss: 0.015887 | dt: 449ms | Remaining: 11s
Step 0545 | Loss: 0.016465 | dt: 449ms | Remaining: 9s
Step 0550 | Loss: 0.016535 | dt: 454ms | Remaining: 7s
Step 0555 | Loss: 0.015288 | dt: 451ms | Remaining: 3s
Step 0560 | Loss: 0.013922 | dt: 448ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.003369
train_loss:       0.013626
training_seconds: 300.1
total_seconds:    302.0
peak_vram_mb:     22406.7
num_steps:        562
num_params_M:     2.262
throughput_Mvps:  0.74

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 3: base_feat_64 (REVERTED)
- **Timestamp**: 22:46:19
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
t: 462ms | Remaining: 172s
Step 0240 | Loss: 0.029674 | dt: 449ms | Remaining: 170s
Step 0245 | Loss: 0.035007 | dt: 449ms | Remaining: 167s
Step 0250 | Loss: 0.036845 | dt: 453ms | Remaining: 165s
Step 0255 | Loss: 0.035439 | dt: 450ms | Remaining: 163s
Step 0260 | Loss: 0.027812 | dt: 450ms | Remaining: 160s
Step 0265 | Loss: 0.022411 | dt: 449ms | Remaining: 158s
Step 0270 | Loss: 0.019478 | dt: 450ms | Remaining: 155s
Step 0275 | Loss: 0.016935 | dt: 450ms | Remaining: 153s
Step 0280 | Loss: 0.015658 | dt: 458ms | Remaining: 150s
Step 0285 | Loss: 0.015088 | dt: 448ms | Remaining: 148s
Step 0290 | Loss: 0.014311 | dt: 449ms | Remaining: 146s
Step 0295 | Loss: 0.014529 | dt: 449ms | Remaining: 144s
Step 0300 | Loss: 0.084018 | dt: 450ms | Remaining: 139s
Step 0305 | Loss: 0.067115 | dt: 449ms | Remaining: 136s
Step 0310 | Loss: 0.065266 | dt: 466ms | Remaining: 134s
Step 0315 | Loss: 0.057809 | dt: 457ms | Remaining: 132s
Step 0320 | Loss: 0.047510 | dt: 1046ms | Remaining: 129s
Step 0325 | Loss: 0.033620 | dt: 450ms | Remaining: 127s
Step 0330 | Loss: 0.025900 | dt: 453ms | Remaining: 124s
Step 0335 | Loss: 0.022443 | dt: 452ms | Remaining: 122s
Step 0340 | Loss: 0.022732 | dt: 449ms | Remaining: 120s
Step 0345 | Loss: 0.032200 | dt: 449ms | Remaining: 117s
Step 0350 | Loss: 0.032723 | dt: 449ms | Remaining: 115s
Step 0355 | Loss: 0.030587 | dt: 450ms | Remaining: 113s
Step 0360 | Loss: 0.026766 | dt: 449ms | Remaining: 110s
Step 0365 | Loss: 0.022775 | dt: 449ms | Remaining: 107s
Step 0370 | Loss: 0.020575 | dt: 449ms | Remaining: 105s
Step 0375 | Loss: 0.018310 | dt: 450ms | Remaining: 103s
Step 0380 | Loss: 0.016876 | dt: 448ms | Remaining: 101s
Step 0385 | Loss: 0.029306 | dt: 452ms | Remaining: 93s
Step 0390 | Loss: 0.035970 | dt: 451ms | Remaining: 90s
Step 0395 | Loss: 0.032433 | dt: 449ms | Remaining: 88s
Step 0400 | Loss: 0.028875 | dt: 451ms | Remaining: 86s
Step 0405 | Loss: 0.025636 | dt: 3135ms | Remaining: 81s
Step 0410 | Loss: 0.026917 | dt: 451ms | Remaining: 79s
Step 0415 | Loss: 0.024819 | dt: 450ms | Remaining: 76s
Step 0420 | Loss: 0.023942 | dt: 449ms | Remaining: 74s
Step 0425 | Loss: 0.021791 | dt: 451ms | Remaining: 72s
Step 0430 | Loss: 0.016346 | dt: 452ms | Remaining: 68s
Step 0435 | Loss: 0.012986 | dt: 449ms | Remaining: 66s
Step 0440 | Loss: 0.010421 | dt: 448ms | Remaining: 63s
Step 0445 | Loss: 0.009312 | dt: 449ms | Remaining: 61s
Step 0450 | Loss: 0.008468 | dt: 448ms | Remaining: 58s
Step 0455 | Loss: 0.007833 | dt: 450ms | Remaining: 56s
Step 0460 | Loss: 0.007124 | dt: 450ms | Remaining: 54s
Step 0465 | Loss: 0.006783 | dt: 449ms | Remaining: 51s
Step 0470 | Loss: 0.008920 | dt: 455ms | Remaining: 46s
Step 0475 | Loss: 0.023745 | dt: 448ms | Remaining: 44s
Step 0480 | Loss: 0.032925 | dt: 448ms | Remaining: 42s
Step 0485 | Loss: 0.050524 | dt: 450ms | Remaining: 40s
Step 0490 | Loss: 0.049052 | dt: 1094ms | Remaining: 37s
Step 0495 | Loss: 0.031525 | dt: 449ms | Remaining: 34s
Step 0500 | Loss: 0.021188 | dt: 449ms | Remaining: 32s
Step 0505 | Loss: 0.015173 | dt: 449ms | Remaining: 30s
Step 0510 | Loss: 0.011709 | dt: 449ms | Remaining: 28s
Step 0515 | Loss: 0.009508 | dt: 463ms | Remaining: 25s
Step 0520 | Loss: 0.007891 | dt: 449ms | Remaining: 23s
Step 0525 | Loss: 0.007252 | dt: 449ms | Remaining: 20s
Step 0530 | Loss: 0.006888 | dt: 449ms | Remaining: 18s
Step 0535 | Loss: 0.006909 | dt: 449ms | Remaining: 15s
Step 0540 | Loss: 0.006788 | dt: 449ms | Remaining: 13s
Step 0545 | Loss: 0.006822 | dt: 449ms | Remaining: 11s
Step 0550 | Loss: 0.006986 | dt: 464ms | Remaining: 8s
Step 0555 | Loss: 0.007582 | dt: 450ms | Remaining: 6s
Step 0560 | Loss: 0.008684 | dt: 449ms | Remaining: 3s
Step 0565 | Loss: 0.010198 | dt: 449ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.006580
train_loss:       0.011518
training_seconds: 300.3
total_seconds:    302.2
peak_vram_mb:     22406.7
num_steps:        569
num_params_M:     2.262
throughput_Mvps:  0.74

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 4: dropout_0.0 (REVERTED)
- **Timestamp**: 22:51:30
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
t: 436ms | Remaining: 181s
Step 0225 | Loss: 0.040694 | dt: 435ms | Remaining: 178s
Step 0230 | Loss: 0.035371 | dt: 435ms | Remaining: 176s
Step 0235 | Loss: 0.031615 | dt: 446ms | Remaining: 171s
Step 0240 | Loss: 0.026974 | dt: 434ms | Remaining: 168s
Step 0245 | Loss: 0.024040 | dt: 434ms | Remaining: 166s
Step 0250 | Loss: 0.022034 | dt: 434ms | Remaining: 164s
Step 0255 | Loss: 0.021162 | dt: 434ms | Remaining: 162s
Step 0260 | Loss: 0.016549 | dt: 435ms | Remaining: 159s
Step 0265 | Loss: 0.013268 | dt: 433ms | Remaining: 157s
Step 0270 | Loss: 0.010974 | dt: 435ms | Remaining: 155s
Step 0275 | Loss: 0.010084 | dt: 434ms | Remaining: 153s
Step 0280 | Loss: 0.012820 | dt: 435ms | Remaining: 147s
Step 0285 | Loss: 0.012957 | dt: 473ms | Remaining: 145s
Step 0290 | Loss: 0.014345 | dt: 437ms | Remaining: 142s
Step 0295 | Loss: 0.015143 | dt: 435ms | Remaining: 140s
Step 0300 | Loss: 0.014210 | dt: 434ms | Remaining: 135s
Step 0305 | Loss: 0.011269 | dt: 436ms | Remaining: 133s
Step 0310 | Loss: 0.009415 | dt: 434ms | Remaining: 131s
Step 0315 | Loss: 0.008289 | dt: 433ms | Remaining: 129s
Step 0320 | Loss: 0.007814 | dt: 1041ms | Remaining: 126s
Step 0325 | Loss: 0.007594 | dt: 433ms | Remaining: 124s
Step 0330 | Loss: 0.007620 | dt: 446ms | Remaining: 122s
Step 0335 | Loss: 0.007604 | dt: 434ms | Remaining: 120s
Step 0340 | Loss: 0.007966 | dt: 434ms | Remaining: 117s
Step 0345 | Loss: 0.012330 | dt: 434ms | Remaining: 109s
Step 0350 | Loss: 0.013876 | dt: 434ms | Remaining: 107s
Step 0355 | Loss: 0.013816 | dt: 433ms | Remaining: 105s
Step 0360 | Loss: 0.015329 | dt: 440ms | Remaining: 103s
Step 0365 | Loss: 0.014828 | dt: 433ms | Remaining: 98s
Step 0370 | Loss: 0.015282 | dt: 435ms | Remaining: 96s
Step 0375 | Loss: 0.014279 | dt: 434ms | Remaining: 93s
Step 0380 | Loss: 0.013985 | dt: 433ms | Remaining: 91s
Step 0385 | Loss: 0.013828 | dt: 434ms | Remaining: 86s
Step 0390 | Loss: 0.014090 | dt: 436ms | Remaining: 84s
Step 0395 | Loss: 0.013574 | dt: 434ms | Remaining: 82s
Step 0400 | Loss: 0.013387 | dt: 435ms | Remaining: 80s
Step 0405 | Loss: 0.012765 | dt: 1051ms | Remaining: 77s
Step 0410 | Loss: 0.010041 | dt: 434ms | Remaining: 75s
Step 0415 | Loss: 0.008157 | dt: 439ms | Remaining: 73s
Step 0420 | Loss: 0.007108 | dt: 435ms | Remaining: 71s
Step 0425 | Loss: 0.006454 | dt: 436ms | Remaining: 68s
Step 0430 | Loss: 0.006170 | dt: 434ms | Remaining: 66s
Step 0435 | Loss: 0.006139 | dt: 433ms | Remaining: 63s
Step 0440 | Loss: 0.006152 | dt: 434ms | Remaining: 61s
Step 0445 | Loss: 0.006184 | dt: 434ms | Remaining: 59s
Step 0450 | Loss: 0.006246 | dt: 433ms | Remaining: 56s
Step 0455 | Loss: 0.006201 | dt: 433ms | Remaining: 54s
Step 0460 | Loss: 0.006368 | dt: 450ms | Remaining: 52s
Step 0465 | Loss: 0.006569 | dt: 433ms | Remaining: 50s
Step 0470 | Loss: 0.006583 | dt: 435ms | Remaining: 47s
Step 0475 | Loss: 0.006738 | dt: 434ms | Remaining: 45s
Step 0480 | Loss: 0.006868 | dt: 433ms | Remaining: 43s
Step 0485 | Loss: 0.007108 | dt: 433ms | Remaining: 40s
Step 0490 | Loss: 0.007420 | dt: 1070ms | Remaining: 38s
Step 0495 | Loss: 0.007663 | dt: 433ms | Remaining: 35s
Step 0500 | Loss: 0.008240 | dt: 435ms | Remaining: 33s
Step 0505 | Loss: 0.008486 | dt: 434ms | Remaining: 31s
Step 0510 | Loss: 0.008638 | dt: 434ms | Remaining: 29s
Step 0515 | Loss: 0.015582 | dt: 442ms | Remaining: 24s
Step 0520 | Loss: 0.026680 | dt: 434ms | Remaining: 22s
Step 0525 | Loss: 0.026239 | dt: 435ms | Remaining: 20s
Step 0530 | Loss: 0.029341 | dt: 434ms | Remaining: 18s
Step 0535 | Loss: 0.022772 | dt: 442ms | Remaining: 10s
Step 0540 | Loss: 0.017926 | dt: 433ms | Remaining: 7s
Step 0545 | Loss: 0.015452 | dt: 434ms | Remaining: 5s
Step 0550 | Loss: 0.014787 | dt: 435ms | Remaining: 3s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.003008
train_loss:       0.013004
training_seconds: 301.3
total_seconds:    303.1
peak_vram_mb:     20486.3
num_steps:        555
num_params_M:     2.262
throughput_Mvps:  0.72

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 5: lr_1e-5 (REVERTED)
- **Timestamp**: 22:56:40
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
dt: 449ms | Remaining: 179s
Step 0215 | Loss: 0.157824 | dt: 464ms | Remaining: 174s
Step 0220 | Loss: 0.170043 | dt: 450ms | Remaining: 171s
Step 0225 | Loss: 0.157814 | dt: 449ms | Remaining: 169s
Step 0230 | Loss: 0.152945 | dt: 464ms | Remaining: 167s
Step 0235 | Loss: 0.151654 | dt: 458ms | Remaining: 164s
Step 0240 | Loss: 0.134720 | dt: 449ms | Remaining: 162s
Step 0245 | Loss: 0.122196 | dt: 449ms | Remaining: 159s
Step 0250 | Loss: 0.113514 | dt: 449ms | Remaining: 157s
Step 0255 | Loss: 0.105617 | dt: 450ms | Remaining: 155s
Step 0260 | Loss: 0.099930 | dt: 449ms | Remaining: 152s
Step 0265 | Loss: 0.095037 | dt: 462ms | Remaining: 150s
Step 0270 | Loss: 0.092405 | dt: 450ms | Remaining: 147s
Step 0275 | Loss: 0.087985 | dt: 450ms | Remaining: 145s
Step 0280 | Loss: 0.102842 | dt: 451ms | Remaining: 140s
Step 0285 | Loss: 0.122366 | dt: 459ms | Remaining: 137s
Step 0290 | Loss: 0.127976 | dt: 468ms | Remaining: 135s
Step 0295 | Loss: 0.128632 | dt: 468ms | Remaining: 133s
Step 0300 | Loss: 0.119943 | dt: 452ms | Remaining: 130s
Step 0305 | Loss: 0.103273 | dt: 465ms | Remaining: 127s
Step 0310 | Loss: 0.090808 | dt: 451ms | Remaining: 125s
Step 0315 | Loss: 0.082806 | dt: 449ms | Remaining: 123s
Step 0320 | Loss: 0.078725 | dt: 2886ms | Remaining: 118s
Step 0325 | Loss: 0.085342 | dt: 454ms | Remaining: 116s
Step 0330 | Loss: 0.085582 | dt: 449ms | Remaining: 114s
Step 0335 | Loss: 0.086108 | dt: 450ms | Remaining: 111s
Step 0340 | Loss: 0.089505 | dt: 452ms | Remaining: 109s
Step 0345 | Loss: 0.091802 | dt: 449ms | Remaining: 104s
Step 0350 | Loss: 0.098304 | dt: 449ms | Remaining: 102s
Step 0355 | Loss: 0.101478 | dt: 449ms | Remaining: 99s
Step 0360 | Loss: 0.099994 | dt: 454ms | Remaining: 97s
Step 0365 | Loss: 0.087500 | dt: 450ms | Remaining: 94s
Step 0370 | Loss: 0.076904 | dt: 467ms | Remaining: 92s
Step 0375 | Loss: 0.069508 | dt: 449ms | Remaining: 90s
Step 0380 | Loss: 0.065258 | dt: 449ms | Remaining: 87s
Step 0385 | Loss: 0.063108 | dt: 452ms | Remaining: 85s
Step 0390 | Loss: 0.061594 | dt: 449ms | Remaining: 82s
Step 0395 | Loss: 0.060296 | dt: 451ms | Remaining: 80s
Step 0400 | Loss: 0.059049 | dt: 461ms | Remaining: 78s
Step 0405 | Loss: 0.062579 | dt: 3416ms | Remaining: 73s
Step 0410 | Loss: 0.080784 | dt: 448ms | Remaining: 70s
Step 0415 | Loss: 0.085099 | dt: 450ms | Remaining: 68s
Step 0420 | Loss: 0.088054 | dt: 450ms | Remaining: 66s
Step 0425 | Loss: 0.087851 | dt: 449ms | Remaining: 64s
Step 0430 | Loss: 0.074114 | dt: 470ms | Remaining: 61s
Step 0435 | Loss: 0.063693 | dt: 449ms | Remaining: 58s
Step 0440 | Loss: 0.057608 | dt: 450ms | Remaining: 56s
Step 0445 | Loss: 0.053101 | dt: 449ms | Remaining: 54s
Step 0450 | Loss: 0.059228 | dt: 449ms | Remaining: 48s
Step 0455 | Loss: 0.071087 | dt: 448ms | Remaining: 46s
Step 0460 | Loss: 0.073243 | dt: 449ms | Remaining: 44s
Step 0465 | Loss: 0.075531 | dt: 449ms | Remaining: 42s
Step 0470 | Loss: 0.072440 | dt: 455ms | Remaining: 37s
Step 0475 | Loss: 0.069574 | dt: 460ms | Remaining: 35s
Step 0480 | Loss: 0.062628 | dt: 452ms | Remaining: 32s
Step 0485 | Loss: 0.060091 | dt: 449ms | Remaining: 30s
Step 0490 | Loss: 0.057913 | dt: 3427ms | Remaining: 25s
Step 0495 | Loss: 0.073100 | dt: 466ms | Remaining: 23s
Step 0500 | Loss: 0.072775 | dt: 455ms | Remaining: 20s
Step 0505 | Loss: 0.071584 | dt: 450ms | Remaining: 18s
Step 0510 | Loss: 0.070604 | dt: 453ms | Remaining: 16s
Step 0515 | Loss: 0.063853 | dt: 450ms | Remaining: 13s
Step 0520 | Loss: 0.056886 | dt: 448ms | Remaining: 11s
Step 0525 | Loss: 0.051808 | dt: 451ms | Remaining: 8s
Step 0530 | Loss: 0.049825 | dt: 449ms | Remaining: 6s
Step 0535 | Loss: 0.047657 | dt: 448ms | Remaining: 3s
Step 0540 | Loss: 0.046319 | dt: 464ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.004490
train_loss:       0.045253
training_seconds: 300.3
total_seconds:    302.0
peak_vram_mb:     22406.7
num_steps:        544
num_params_M:     2.262
throughput_Mvps:  0.71

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 6: heads_8 (REVERTED)
- **Timestamp**: 23:01:51
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
 | dt: 416ms | Remaining: 161s
Step 0275 | Loss: 0.170808 | dt: 402ms | Remaining: 159s
Step 0280 | Loss: 0.129300 | dt: 417ms | Remaining: 156s
Step 0285 | Loss: 0.081488 | dt: 417ms | Remaining: 154s
Step 0290 | Loss: 0.052755 | dt: 416ms | Remaining: 152s
Step 0295 | Loss: 0.035313 | dt: 403ms | Remaining: 150s
Step 0300 | Loss: 0.027550 | dt: 420ms | Remaining: 143s
Step 0305 | Loss: 0.025525 | dt: 427ms | Remaining: 141s
Step 0310 | Loss: 0.023712 | dt: 407ms | Remaining: 139s
Step 0315 | Loss: 0.021680 | dt: 420ms | Remaining: 137s
Step 0320 | Loss: 0.018556 | dt: 1063ms | Remaining: 134s
Step 0325 | Loss: 0.013615 | dt: 418ms | Remaining: 132s
Step 0330 | Loss: 0.010844 | dt: 407ms | Remaining: 130s
Step 0335 | Loss: 0.009171 | dt: 411ms | Remaining: 128s
Step 0340 | Loss: 0.008108 | dt: 402ms | Remaining: 126s
Step 0345 | Loss: 0.007545 | dt: 404ms | Remaining: 123s
Step 0350 | Loss: 0.007180 | dt: 403ms | Remaining: 121s
Step 0355 | Loss: 0.006950 | dt: 404ms | Remaining: 119s
Step 0360 | Loss: 0.006888 | dt: 402ms | Remaining: 117s
Step 0365 | Loss: 0.006892 | dt: 402ms | Remaining: 114s
Step 0370 | Loss: 0.006905 | dt: 402ms | Remaining: 112s
Step 0375 | Loss: 0.006852 | dt: 417ms | Remaining: 110s
Step 0380 | Loss: 0.006877 | dt: 402ms | Remaining: 108s
Step 0385 | Loss: 0.007009 | dt: 405ms | Remaining: 105s
Step 0390 | Loss: 0.007113 | dt: 409ms | Remaining: 103s
Step 0395 | Loss: 0.007233 | dt: 408ms | Remaining: 101s
Step 0400 | Loss: 0.007475 | dt: 402ms | Remaining: 99s
Step 0405 | Loss: 0.008089 | dt: 3186ms | Remaining: 95s
Step 0410 | Loss: 0.029705 | dt: 405ms | Remaining: 93s
Step 0415 | Loss: 0.031527 | dt: 408ms | Remaining: 91s
Step 0420 | Loss: 0.033957 | dt: 402ms | Remaining: 89s
Step 0425 | Loss: 0.039866 | dt: 402ms | Remaining: 87s
Step 0430 | Loss: 0.029002 | dt: 402ms | Remaining: 84s
Step 0435 | Loss: 0.020527 | dt: 414ms | Remaining: 82s
Step 0440 | Loss: 0.015117 | dt: 403ms | Remaining: 80s
Step 0445 | Loss: 0.011767 | dt: 411ms | Remaining: 78s
Step 0450 | Loss: 0.031762 | dt: 402ms | Remaining: 73s
Step 0455 | Loss: 0.041994 | dt: 402ms | Remaining: 71s
Step 0460 | Loss: 0.042517 | dt: 402ms | Remaining: 69s
Step 0465 | Loss: 0.035145 | dt: 402ms | Remaining: 67s
Step 0470 | Loss: 0.037817 | dt: 402ms | Remaining: 63s
Step 0475 | Loss: 0.034867 | dt: 406ms | Remaining: 61s
Step 0480 | Loss: 0.029462 | dt: 402ms | Remaining: 59s
Step 0485 | Loss: 0.028988 | dt: 405ms | Remaining: 56s
Step 0490 | Loss: 0.026783 | dt: 1003ms | Remaining: 54s
Step 0495 | Loss: 0.019973 | dt: 401ms | Remaining: 52s
Step 0500 | Loss: 0.015917 | dt: 402ms | Remaining: 50s
Step 0505 | Loss: 0.013428 | dt: 402ms | Remaining: 48s
Step 0510 | Loss: 0.012073 | dt: 462ms | Remaining: 46s
Step 0515 | Loss: 0.062489 | dt: 402ms | Remaining: 41s
Step 0520 | Loss: 0.061383 | dt: 402ms | Remaining: 39s
Step 0525 | Loss: 0.065461 | dt: 402ms | Remaining: 37s
Step 0530 | Loss: 0.054350 | dt: 402ms | Remaining: 35s
Step 0535 | Loss: 0.049615 | dt: 402ms | Remaining: 30s
Step 0540 | Loss: 0.047321 | dt: 401ms | Remaining: 28s
Step 0545 | Loss: 0.053621 | dt: 402ms | Remaining: 26s
Step 0550 | Loss: 0.049465 | dt: 402ms | Remaining: 24s
Step 0555 | Loss: 0.042376 | dt: 402ms | Remaining: 20s
Step 0560 | Loss: 0.031515 | dt: 401ms | Remaining: 18s
Step 0565 | Loss: 0.025061 | dt: 402ms | Remaining: 16s
Step 0570 | Loss: 0.021679 | dt: 402ms | Remaining: 14s
Step 0575 | Loss: 0.020122 | dt: 402ms | Remaining: 12s
Step 0580 | Loss: 0.019385 | dt: 402ms | Remaining: 10s
Step 0585 | Loss: 0.019554 | dt: 421ms | Remaining: 8s
Step 0590 | Loss: 0.020473 | dt: 402ms | Remaining: 6s
Step 0595 | Loss: 0.021849 | dt: 402ms | Remaining: 3s
Step 0600 | Loss: 0.023984 | dt: 402ms | Remaining: 1s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.002115
train_loss:       0.025558
training_seconds: 300.3
total_seconds:    302.4
peak_vram_mb:     15602.7
num_steps:        604
num_params_M:     2.262
throughput_Mvps:  0.79

[RESULT] No improvement detected. Recommended: Revert changes.

```

---

## Cycle 7: blocks_8 (SUCCESS)
- **Timestamp**: 23:07:04
### Model Parameters
- **train_uri**: s3://vesuvius-challenge-open-data/PHerc0172/volumes/20241024131838-7.910um-53keV-masked.zarr/0/
- **batch_size**: 6
- **patch_size**: 64
### Output Snippet
```
1753 | dt: 207ms | Remaining: 89s
Step 0805 | Loss: 0.018352 | dt: 208ms | Remaining: 88s
Step 0810 | Loss: 0.015134 | dt: 3799ms | Remaining: 83s
Step 0815 | Loss: 0.012595 | dt: 221ms | Remaining: 82s
Step 0820 | Loss: 0.011042 | dt: 222ms | Remaining: 81s
Step 0825 | Loss: 0.009705 | dt: 226ms | Remaining: 80s
Step 0830 | Loss: 0.009005 | dt: 209ms | Remaining: 79s
Step 0835 | Loss: 0.008846 | dt: 225ms | Remaining: 75s
Step 0840 | Loss: 0.008230 | dt: 208ms | Remaining: 74s
Step 0845 | Loss: 0.007058 | dt: 214ms | Remaining: 73s
Step 0850 | Loss: 0.006679 | dt: 231ms | Remaining: 72s
Step 0855 | Loss: 0.005605 | dt: 213ms | Remaining: 71s
Step 0860 | Loss: 0.004491 | dt: 210ms | Remaining: 69s
Step 0865 | Loss: 0.003755 | dt: 220ms | Remaining: 68s
Step 0870 | Loss: 0.003381 | dt: 222ms | Remaining: 67s
Step 0875 | Loss: 0.003138 | dt: 221ms | Remaining: 66s
Step 0880 | Loss: 0.003139 | dt: 208ms | Remaining: 65s
Step 0885 | Loss: 0.003037 | dt: 209ms | Remaining: 64s
Step 0890 | Loss: 0.003070 | dt: 208ms | Remaining: 63s
Step 0895 | Loss: 0.003200 | dt: 208ms | Remaining: 62s
Step 0900 | Loss: 0.003016 | dt: 208ms | Remaining: 59s
Step 0905 | Loss: 0.003063 | dt: 207ms | Remaining: 58s
Step 0910 | Loss: 0.002921 | dt: 208ms | Remaining: 57s
Step 0915 | Loss: 0.002864 | dt: 214ms | Remaining: 56s
Step 0920 | Loss: 0.002878 | dt: 207ms | Remaining: 55s
Step 0925 | Loss: 0.002844 | dt: 208ms | Remaining: 54s
Step 0930 | Loss: 0.002796 | dt: 207ms | Remaining: 53s
Step 0935 | Loss: 0.002652 | dt: 213ms | Remaining: 52s
Step 0940 | Loss: 0.005176 | dt: 208ms | Remaining: 49s
Step 0945 | Loss: 0.008083 | dt: 209ms | Remaining: 48s
Step 0950 | Loss: 0.009524 | dt: 208ms | Remaining: 47s
Step 0955 | Loss: 0.008721 | dt: 207ms | Remaining: 46s
Step 0960 | Loss: 0.008533 | dt: 543ms | Remaining: 44s
Step 0965 | Loss: 0.006114 | dt: 208ms | Remaining: 43s
Step 0970 | Loss: 0.004602 | dt: 209ms | Remaining: 42s
Step 0975 | Loss: 0.003726 | dt: 207ms | Remaining: 41s
Step 0980 | Loss: 0.003097 | dt: 208ms | Remaining: 40s
Step 0985 | Loss: 0.005136 | dt: 208ms | Remaining: 38s
Step 0990 | Loss: 0.007740 | dt: 208ms | Remaining: 37s
Step 0995 | Loss: 0.007554 | dt: 207ms | Remaining: 36s
Step 1000 | Loss: 0.008260 | dt: 212ms | Remaining: 35s
Step 1005 | Loss: 0.007787 | dt: 208ms | Remaining: 32s
Step 1010 | Loss: 0.006886 | dt: 207ms | Remaining: 31s
Step 1015 | Loss: 0.007717 | dt: 210ms | Remaining: 30s
Step 1020 | Loss: 0.007289 | dt: 222ms | Remaining: 29s
Step 1025 | Loss: 0.005806 | dt: 222ms | Remaining: 27s
Step 1030 | Loss: 0.004350 | dt: 208ms | Remaining: 26s
Step 1035 | Loss: 0.003394 | dt: 207ms | Remaining: 25s
Step 1040 | Loss: 0.003004 | dt: 209ms | Remaining: 24s
Step 1045 | Loss: 0.002748 | dt: 518ms | Remaining: 23s
Step 1050 | Loss: 0.002633 | dt: 207ms | Remaining: 22s
Step 1055 | Loss: 0.002519 | dt: 207ms | Remaining: 21s
Step 1060 | Loss: 0.002380 | dt: 208ms | Remaining: 20s
Step 1065 | Loss: 0.002304 | dt: 209ms | Remaining: 19s
Step 1070 | Loss: 0.006075 | dt: 223ms | Remaining: 15s
Step 1075 | Loss: 0.007945 | dt: 212ms | Remaining: 14s
Step 1080 | Loss: 0.009050 | dt: 208ms | Remaining: 13s
Step 1085 | Loss: 0.009296 | dt: 208ms | Remaining: 12s
Step 1090 | Loss: 0.007427 | dt: 208ms | Remaining: 11s
Step 1095 | Loss: 0.005603 | dt: 207ms | Remaining: 10s
Step 1100 | Loss: 0.004392 | dt: 208ms | Remaining: 9s
Step 1105 | Loss: 0.003660 | dt: 223ms | Remaining: 8s
Step 1110 | Loss: 0.004649 | dt: 208ms | Remaining: 5s
Step 1115 | Loss: 0.008458 | dt: 210ms | Remaining: 4s
Step 1120 | Loss: 0.010430 | dt: 208ms | Remaining: 3s
Step 1125 | Loss: 0.010838 | dt: 207ms | Remaining: 2s
Step 1130 | Loss: 0.011196 | dt: 1776ms | Remaining: 0s
Evaluating val_bpb on validation chunk...

--- Foundation Pretraining Complete ---
val_bpb:          0.000501 [NEW BEST]
train_loss:       0.011196
training_seconds: 300.9
total_seconds:    302.6
peak_vram_mb:     8388.5
num_steps:        1131
num_params_M:     1.032
throughput_Mvps:  1.48
Updated progress.png

[RESULT] Improvement detected! Recommended: Keep changes.

```

---
