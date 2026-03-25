#!/bin/bash
git add local_data/PHerc0139_div_*_1GB
git add local_data/PHerc0332_div_*_1GB
git add local_data/PHerc0172_div_*_1GB
git commit -m "Add 11x 1GB cross-sectional division datasets for Scroll 1 (PHerc139), Scroll 3 (PHerc332), and Scroll 5 (PHerc172)"
git push
