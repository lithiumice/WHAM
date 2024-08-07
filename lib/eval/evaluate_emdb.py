import os
import time
import os.path as osp
from glob import glob
from collections import defaultdict

import torch
import pickle
import numpy as np
from smplx import SMPL
from loguru import logger
from progress.bar import Bar
import sys

from configs import constants as _C
from configs.config import parse_args
from lib.data.dataloader import setup_eval_dataloader
from lib.models import build_network, build_body_model
from lib.eval.eval_utils import (
    compute_jpe,
    compute_rte,
    compute_jitter,
    compute_error_accel,
    compute_foot_sliding,
    batch_align_by_pelvis,
    first_align_joints,
    global_align_joints,
    compute_rte,
    compute_jitter,
    compute_foot_sliding,
    batch_compute_similarity_transform_torch,
    align_pcl,
)
from lib.utils import transforms
from lib.utils.utils import prepare_output_dir
from lib.utils.utils import prepare_batch
from lib.utils.imutils import avg_preds

"""
This is a tentative script to evaluate WHAM on EMDB dataset.
Current implementation requires EMDB dataset downloaded at ./datasets/EMDB/
"""

m2mm = 1e3
@torch.no_grad()
def main(cfg, args):
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    
    logger.info(f'GPU name -> {torch.cuda.get_device_name()}')
    logger.info(f'GPU feat -> {torch.cuda.get_device_properties("cuda")}')    
    
    # ========= Dataloaders ========= #
    eval_loader = setup_eval_dataloader(cfg, 'emdb', args.eval_split, cfg.MODEL.BACKBONE)
    logger.info(f'Dataset loaded')
    
    # ========= Load WHAM ========= #
    smpl_batch_size = cfg.TRAIN.BATCH_SIZE * cfg.DATASET.SEQLEN
    smpl = build_body_model(cfg.DEVICE, smpl_batch_size)
    network = build_network(cfg, smpl)
    network.eval()
    
    # Build SMPL models with each gender
    smpl = {k: SMPL(_C.BMODEL.FLDR, gender=k).to(cfg.DEVICE) for k in ['male', 'female', 'neutral']}
    
    # Load vertices -> joints regression matrix to evaluate
    pelvis_idxs = [1, 2]
    
    # WHAM uses Y-down coordinate system, while EMDB dataset uses Y-up one.
    yup2ydown = transforms.axis_angle_to_matrix(torch.tensor([[np.pi, 0, 0]])).float().to(cfg.DEVICE)
    
    # To torch tensor function
    tt = lambda x: torch.from_numpy(x).float().to(cfg.DEVICE)
    accumulator = defaultdict(list)
    bar = Bar('Inference', fill='#', max=len(eval_loader))
    
    
    # <===============
    # if args.eval_difftraj or args.vis_eval_traj_for_compare:
    sys.path.insert(0, "/home/hualin/MotionCapture/DiffTraj")
    
    from difftraj import DiffTraj
    from difftraj_api import DIFFTRAJ_CONFIG_1, DIFFTRAJ_CONFIG_2
    difftraj_traj_predictor = DiffTraj(**DIFFTRAJ_CONFIG_2)
    # difftraj_traj_predictor = DiffTraj(**DIFFTRAJ_CONFIG_1)

    from utils.traj_utils import (traj_local2global_heading, )
    from utils.tensor_utils import apply_cvt_R, apply_cvt_T, zup_to_yup, toth, tonp
    from eval.eval_difftraj import init_vae_model, infer_vae, infer_vae_from_axis
    vae_traj_predictor = init_vae_model()
    # ===============>
    
        
    with torch.no_grad():
        for i in range(len(eval_loader)):
            # Original batch
            batch = eval_loader.dataset.load_data(i, False)
            x, inits, features, kwargs, gt = prepare_batch(batch, cfg.DEVICE, cfg.TRAIN.STAGE == 'stage2')
            
            skpi_flag = False
            if args.skip_non_flat_ground:
                vid_id = batch['vid']
                keys_to_skip = ["up", "down"]
                for k in keys_to_skip:
                    if k in vid_id:
                        skpi_flag = True
                        break
            if skpi_flag: 
                print(f"\n => [WARN] {k} in {vid_id}, we remove non-flat ground case to evaluate difftraj...")
                continue     
                
            # Align with groundtruth data to the first frame
            cam2yup = batch['R'][0][:1].to(cfg.DEVICE)
            cam2ydown = cam2yup @ yup2ydown
            cam2root = transforms.rotation_6d_to_matrix(inits[1][:, 0, 0])
            ydown2root = cam2ydown.mT @ cam2root
            ydown2root = transforms.matrix_to_rotation_6d(ydown2root)
            kwargs['init_root'][:, 0] = ydown2root
            
            if cfg.FLIP_EVAL:
                flipped_batch = eval_loader.dataset.load_data(i, True)
                f_x, f_inits, f_features, f_kwargs, _ = prepare_batch(flipped_batch, cfg.DEVICE, cfg.TRAIN.STAGE == 'stage2')
            
                # Forward pass with flipped input
                flipped_pred = network(f_x, f_inits, f_features, **f_kwargs)
                
            # Forward pass with normal input
            pred = network(x, inits, features, **kwargs)
            
            if cfg.FLIP_EVAL:
                # Merge two predictions
                flipped_pose, flipped_shape = flipped_pred['pose'].squeeze(0), flipped_pred['betas'].squeeze(0)
                pose, shape = pred['pose'].squeeze(0), pred['betas'].squeeze(0)
                flipped_pose, pose = flipped_pose.reshape(-1, 24, 6), pose.reshape(-1, 24, 6)
                avg_pose, avg_shape = avg_preds(pose, shape, flipped_pose, flipped_shape)
                avg_pose = avg_pose.reshape(-1, 144)
                avg_contact = (flipped_pred['contact'][..., [2, 3, 0, 1]] + pred['contact']) / 2
                
                # Refine trajectory with merged prediction
                network.pred_pose = avg_pose.view_as(network.pred_pose)
                network.pred_shape = avg_shape.view_as(network.pred_shape)
                network.pred_contact = avg_contact.view_as(network.pred_contact)
                output = network.forward_smpl(**kwargs)
                pred = network.refine_trajectory(output, return_y_up=True, **kwargs)
                
            def totype(x): return x.float().cuda()
            # import ipdb;ipdb.set_trace()
            
            # Convert WHAM global orient to Y-up coordinate
            def convert_to_wham_gt(root, trans):
                poses_root = root.squeeze(0)
                pred_trans = trans.squeeze(0)
                poses_root = yup2ydown.mT @ poses_root
                pred_trans = (yup2ydown.mT @ pred_trans.unsqueeze(-1)).squeeze(-1)
                return poses_root, pred_trans
            
            wham_poses_root, wham_pred_trans = convert_to_wham_gt(pred['poses_root_world'], pred['trans_world'])
            
            if args.eval_difftraj or args.vis_eval_traj_for_compare:
                pred_trans_world = totype(pred["trans_world"][0])
                pred_root_world = totype(transforms.matrix_to_axis_angle(pred["poses_root_world"]).reshape(-1, 3))
                pred_body_pose = totype(transforms.matrix_to_axis_angle(pred["poses_body"]).reshape(-1, 69))
                root, trans = difftraj_traj_predictor(pred_root_world, pred_body_pose, pred_trans_world)
                root = transforms.axis_angle_to_matrix(root)
                difftraj_unified_root, difftraj_unified_trans = convert_to_wham_gt(root, trans)
                
            if args.eval_difftraj:
                pred["poses_root_world"] = root
                pred["trans_world"] = trans
                            
            if args.eval_vae or args.vis_eval_traj_for_compare:
                pred_body_pose = totype(transforms.matrix_to_axis_angle(pred["poses_body"]).reshape(-1, 23, 3))
                sample_rep_pred = infer_vae_from_axis(vae_traj_predictor, pred_body_pose)
                transl_amass_pred, orient_q_amass_pred = traj_local2global_heading(sample_rep_pred)
                root = apply_cvt_R(zup_to_yup, orient_q_amass_pred, in_type='quat', out_type='aa')
                trans = apply_cvt_T(zup_to_yup, transl_amass_pred)   
                root = transforms.axis_angle_to_matrix(root)
                vae_unified_root, vae_unified_trans = convert_to_wham_gt(root, trans)
                
            if args.eval_vae:
                pred["poses_root_world"] = root
                pred["trans_world"] = trans
                          
            # <======= Prepare groundtruth data
            subj, seq = batch['vid'][:2], batch['vid'][3:]
            annot_pth = glob(osp.join(_C.PATHS.EMDB_PTH, subj, seq, '*_data.pkl'))[0]
            annot = pickle.load(open(annot_pth, 'rb'))
            
            masks = annot['good_frames_mask']
            gender = annot['gender']
            poses_body = annot["smpl"]["poses_body"]
            poses_root = annot["smpl"]["poses_root"]
            betas = np.repeat(annot["smpl"]["betas"].reshape((1, -1)), repeats=annot["n_frames"], axis=0)
            trans = annot["smpl"]["trans"]
            extrinsics = annot["camera"]["extrinsics"]
            
            # # Map to camear coordinate
            poses_root_cam = transforms.matrix_to_axis_angle(tt(extrinsics[:, :3, :3]) @ transforms.axis_angle_to_matrix(tt(poses_root)))
            
            # Groundtruth global motion
            target_glob = smpl[gender](body_pose=tt(poses_body), global_orient=tt(poses_root), betas=tt(betas), transl=tt(trans))
            target_j3d_glob = target_glob.joints[:, :24][masks]
            
            # Groundtruth local motion
            target_cam = smpl[gender](body_pose=tt(poses_body), global_orient=poses_root_cam, betas=tt(betas))
            target_verts_cam = target_cam.vertices[masks]
            target_j3d_cam = target_cam.joints[:, :24][masks]
            # =======>
            
            def align_trans(target_trans, pred_trans):
                _min_len = min(len(target_trans), len(pred_trans))
                _, rot, trans = align_pcl(target_trans[None, :_min_len], pred_trans[None, :_min_len], fixed_scale=True)
                pred_trans_hat = (torch.einsum("tij,tnj->tni", rot, pred_trans[None, :]) + trans[None, :])[0]
                return pred_trans_hat
            
            # import ipdb;ipdb.set_trace()
            gt_trans = toth(trans)
            if args.vis_eval_traj_for_compare:
                np.savez(npz_save_path := f"debug/traj_for_vis_bs{i}.npz", vae_unified_root=tonp(vae_unified_root), vae_unified_trans=tonp(vae_unified_trans),
                         difftraj_unified_root=tonp(difftraj_unified_root), difftraj_unified_trans=tonp(difftraj_unified_trans),
                         wham_poses_root=tonp(wham_poses_root), wham_pred_trans=tonp(wham_pred_trans),
                         gt_poses_root=tonp(poses_root), gt_trans=tonp(gt_trans),
                         aligned_wham_trans=tonp(align_trans(gt_trans, wham_pred_trans.cpu())),
                         aligned_vae_trans=tonp(align_trans(gt_trans, vae_unified_trans.cpu())),
                         aligned_difftraj_trans=tonp(align_trans(gt_trans, difftraj_unified_trans.cpu())),)
                print(f"[INFO] npz data will saved to {npz_save_path}")
                                                  
                                                              
            # Convert WHAM global orient to Y-up coordinate
            poses_root, pred_trans = convert_to_wham_gt(pred['poses_root_world'], pred['trans_world'])
            
            # <======= Build predicted motion
            # Predicted global motion
            pred_glob = smpl['neutral'](body_pose=pred['poses_body'], global_orient=poses_root.unsqueeze(1), betas=pred['betas'].squeeze(0), transl=pred_trans, pose2rot=False)
            pred_j3d_glob = pred_glob.joints[:, :24]
            
            # Predicted local motion
            pred_cam = smpl['neutral'](body_pose=pred['poses_body'], global_orient=pred['poses_root_cam'], betas=pred['betas'].squeeze(0), pose2rot=False)
            pred_verts_cam = pred_cam.vertices
            pred_j3d_cam = pred_cam.joints[:, :24]
            # =======>
            
            # <======= Evaluation on the local motion
            pred_j3d_cam, target_j3d_cam, pred_verts_cam, target_verts_cam = batch_align_by_pelvis([pred_j3d_cam, target_j3d_cam, pred_verts_cam, target_verts_cam], pelvis_idxs)
            S1_hat = batch_compute_similarity_transform_torch(pred_j3d_cam, target_j3d_cam)
            pa_mpjpe = torch.sqrt(((S1_hat - target_j3d_cam) ** 2).sum(dim=-1)).mean(dim=-1).cpu().numpy() * m2mm
            mpjpe = torch.sqrt(((pred_j3d_cam - target_j3d_cam) ** 2).sum(dim=-1)).mean(dim=-1).cpu().numpy() * m2mm
            pve = torch.sqrt(((pred_verts_cam - target_verts_cam) ** 2).sum(dim=-1)).mean(dim=-1).cpu().numpy() * m2mm
            accel = compute_error_accel(joints_pred=pred_j3d_cam.cpu(), joints_gt=target_j3d_cam.cpu())[1:-1]
            accel = accel * (30 ** 2)       # per frame^s to per s^2
            

            
            # <======= Evaluation on the global motion
            chunk_length = 100
            w_mpjpe, wa_mpjpe = [], []
            for start in range(0, masks.sum(), chunk_length):
                end = min(masks.sum(), start + chunk_length)

                target_j3d = target_j3d_glob[start:end].clone().cpu()
                pred_j3d = pred_j3d_glob[start:end].clone().cpu()
                
                w_j3d = first_align_joints(target_j3d, pred_j3d)
                wa_j3d = global_align_joints(target_j3d, pred_j3d)
                
                w_jpe = compute_jpe(target_j3d, w_j3d)
                wa_jpe = compute_jpe(target_j3d, wa_j3d)
                w_mpjpe.append(w_jpe)
                wa_mpjpe.append(wa_jpe)
            
            w_mpjpe = np.concatenate(w_mpjpe) * m2mm
            wa_mpjpe = np.concatenate(wa_mpjpe) * m2mm
            
            # Additional metrics
            rte = compute_rte(torch.from_numpy(trans[masks]), pred_trans.cpu()) * 1e2
            jitter = compute_jitter(pred_glob, fps=30)
            foot_sliding = compute_foot_sliding(target_glob, pred_glob, masks) * m2mm
            # =======>
            
            # # Additional metrics
            # rte = compute_rte(torch.from_numpy(trans[masks]), pred_trans.cpu()) * 1e2
            # jitter = compute_jitter(pred_glob, fps=30)
            # foot_sliding = compute_foot_sliding(target_glob, pred_glob, masks) * m2mm
            
            # <======= Accumulate the results over entire sequences
            accumulator['pa_mpjpe'].append(pa_mpjpe)
            accumulator['mpjpe'].append(mpjpe)
            accumulator['pve'].append(pve)
            accumulator['accel'].append(accel)
            accumulator['wa_mpjpe'].append(wa_mpjpe)
            accumulator['w_mpjpe'].append(w_mpjpe)
            accumulator['RTE'].append(rte)
            accumulator['jitter'].append(jitter)
            accumulator['FS'].append(foot_sliding)
                
            summary_string = f"{batch['vid']} | PA-MPJPE: {pa_mpjpe.mean():.1f}mm   MPJPE: {mpjpe.mean():.1f}mm   PVE: {pve.mean():.1f}mm   "\
                                f"Accel: {accel.mean():.3f}mm/s^2   "\
                                f"wa_mpjpe_100: {wa_mpjpe.mean():.1f}   "\
                                f"w_mpjpe_100: {w_mpjpe.mean():.1f}   "\
                                f"RTE: {rte.mean():.1f}   "\
                                f"jitter: {jitter.mean():.1f}   "\
                                f"FS: {foot_sliding.mean():.1f}   "
            bar.suffix = summary_string
            bar.next()
            # =======>            
            
    for k, v in accumulator.items():
        accumulator[k] = np.concatenate(v).mean()

    print('')
    log_str = f'Evaluation on EMDB {args.eval_split}, '
    log_str += ' '.join([f'{k.upper()}: {v:.4f},'for k,v in accumulator.items()])
    logger.info(log_str)
            
if __name__ == '__main__':
    cfg, cfg_file, args = parse_args(test=True)
    cfg = prepare_output_dir(cfg, cfg_file)
    
    main(cfg, args)