from frenet_arcle import TNB2qvecs
import argparse
import os
import re
import numpy as np

def main(args):
    n_frames = 0
    for filename in os.listdir(args.path):
        if filename.endswith(".npy"): 
            curr_int = int(filename.split('_')[1].split('.')[0])
            if curr_int > n_frames:
                n_frames = curr_int

    xyz = np.load(os.path.join(args.path, "frame_1_mean_frenet.npy"))
    n_gaussians = xyz.shape[0]
    
    frame_array = np.zeros((n_frames, n_gaussians*31, 3 + 4 + 1))

    if args.rot_format == 'mat':
        for frame in range(n_frames):
            xyz = np.load(f"{args.path}//frame_{str(frame+1)}_mean_frenet.npy").reshape(-1, 3)
            rot = np.load(f"{args.path}//frame_{str(frame+1)}_rot_frenet.npy").transpose((0, 1, 3, 2))
            rot = TNB2qvecs(rot[:,:,0], rot[:,:,1], rot[:,:,2]).reshape(-1,4)
            scale = np.load(f"{args.path}//frame_{str(frame+1)}_scale_frenet.npy").reshape(n_gaussians, 31, -1)

            frame_array[frame, :, :3] = xyz
            frame_array[frame, :, 3:7] = rot
            frame_array[frame, :, 7] = scale.flatten() if scale.shape[2]==1 else scale[:,:,0].flatten()
    else:
        for frame in range(n_frames):
            xyz = np.load(f"{args.path}//frame_{str(frame+1)}_mean_frenet.npy").reshape(-1, 3)
            rot = np.load(f"{args.path}//frame_{str(frame+1)}_rot_frenet.npy").reshape(-1,4)
            scale = np.load(f"{args.path}//frame_{str(frame+1)}_scale_frenet.npy").reshape(n_gaussians, 31, -1)

            frame_array[frame, :, :3] = xyz
            frame_array[frame, :, 3:7] = rot
            frame_array[frame, :, 7] = scale.flatten() if scale.shape[2]==1 else scale[:,:,0].flatten()
        

    path = os.path.join(os.path.dirname(os.path.dirname(args.path)), "frames.npy")
    np.save(path, frame_array)

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(conflict_handler='resolve')
    parser.add_argument('path', type=str)
    parser.add_argument('--rot_format', choices=['quat', 'mat'], help='Format of rotation in input files, either rotation matrix (mat) or quaternion (quat)', default='mat', type=str)

    args, _ = parser.parse_known_args()
    args = parser.parse_args()

    main(args)

