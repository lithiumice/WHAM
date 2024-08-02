

```bash
# # Evaluate on EMDB dataset (also computes W-MPJPE and WA-MPJPE)
# python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 1 TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar   # EMDB 1
# # 2024-07-24 16:51:11.460 | INFO     | __main__:main:232 - Evaluation on EMDB 1, 
# # PA_MPJPE: 50.4424, MPJPE: 79.6760, PVE: 94.3941, ACCEL: 5.3397, WA_MPJPE: 177.8460, W_MPJPE: 353.0438, RTE: 3.3671, JITTER: 22.5126, FS: 4.6029,


# original wham
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar   # EMDB 2
# PA_MPJPE: 38.1531, MPJPE: 59.2949, PVE: 71.5892, ACCEL: 4.9934, WA_MPJPE: 131.0739, W_MPJPE: 335.3340, RTE: 4.0709, JITTER: 20.9980, FS: 4.3861,



# python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 1 --eval_difftraj TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# # conclusion: worse than original...
# # PA_MPJPE: 50.4424, MPJPE: 79.6760, PVE: 94.3941, ACCEL: 5.3397, WA_MPJPE: 182.1308, W_MPJPE: 368.3256, RTE: 3.2960, JITTER: 23.0215, FS: 5.6755,



# difftraj old model
# EMDB 2
# non flat
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --eval_difftraj TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 38.1531, MPJPE: 59.2949, PVE: 71.5892, ACCEL: 4.9934, WA_MPJPE: 125.4108, W_MPJPE: 319.6152, RTE: 3.7564, JITTER: 18.2137, FS: 5.4969,



# difftraj new model
# EMDB 2
# non flat
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --eval_difftraj TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 38.1531, MPJPE: 59.2949, PVE: 71.5892, ACCEL: 4.9934, WA_MPJPE: 122.1361, W_MPJPE: 320.7436, RTE: 3.6576, JITTER: 16.2915, FS: 5.0751,




# original wham
# EMDB 2
# flat
# done: remove non-flat ground cases and redo evaluation.
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --skip_non_flat_ground TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 37.5727, MPJPE: 57.7865, PVE: 70.2673, ACCEL: 4.9417, WA_MPJPE: 128.3450, W_MPJPE: 327.7562, RTE: 4.0122, JITTER: 20.5294, FS: 4.1440,



# difftraj
# EMDB 2
# flat
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --skip_non_flat_ground --eval_difftraj TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 37.5727, MPJPE: 57.7865, PVE: 70.2673, ACCEL: 4.9417, WA_MPJPE: 121.0880, W_MPJPE: 306.9847, RTE: 3.7459, JITTER: 18.0282, FS: 5.2395,


# VAE
# EMDB 2
# non flat
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --eval_vae TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 38.1531, MPJPE: 59.2949, PVE: 71.5892, ACCEL: 4.9934, WA_MPJPE: 185.8667, W_MPJPE: 541.1070, RTE: 12.8720, JITTER: 19.0784, FS: 7.2105,


# VAE
# EMDB 2
# flat
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --skip_non_flat_ground --eval_vae TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
# PA_MPJPE: 37.5727, MPJPE: 57.7865, PVE: 70.2673, ACCEL: 4.9417, WA_MPJPE: 184.0561, W_MPJPE: 533.0132, RTE: 13.7616, JITTER: 18.8347, FS: 6.9683,


# export data for visualize
python -m lib.eval.evaluate_emdb --cfg configs/yamls/demo.yaml --eval-split 2 --vis_eval_traj_for_compare TRAIN.CHECKPOINT checkpoints/wham_vit_w_3dpw.pth.tar 
```