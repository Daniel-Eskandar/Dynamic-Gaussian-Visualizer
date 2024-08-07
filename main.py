import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer
import imgui
import numpy as np
import util
import imageio
import util_gau
import tkinter as tk
from tkinter import filedialog
import os
import sys
import argparse
import time
from frenet_arcle import *
from renderer_ogl import OpenGLRenderer, GaussianRenderBase, OpenGLRendererAxes
from plyfile import PlyData, PlyElement

# Add the directory containing main.py to the Python path
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

# Change the current working directory to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


g_camera = util.Camera(720, 1280)
BACKEND_OGL=0
BACKEND_OGL_AXES=1
g_renderer_list = [
    None, None
]
g_renderer_idx = BACKEND_OGL
g_renderer: GaussianRenderBase = g_renderer_list[g_renderer_idx]
g_scale_modifier = 1.
g_auto_sort = True
g_show_control_win = True
g_show_help_win = True
g_show_camera_win = False
g_render_mode_tables = ["Ray", "Gaussian Ball", "Flat Ball", "Billboard", "Depth", "SH:0", "SH:0~1", "SH:0~2", "SH:0~3 (default)"]
g_render_mode = 8

###########
# Constants
###########

CLICK_THRESHOLD = 0.2
DISPLACEMENT_FACTOR = 1.5
AVATAR_SEPARATION = 0.1

g_selection_distance = 0.02
g_max_cutting_distance = 0.2
g_max_coloring_distance = 0.1

############################
# Mouse Controller Variables
############################

right_click_start_time = None
left_click_start_time = None

########################
# Head Avatars Variables
########################
gaussians = util_gau.naive_gaussian()
g_show_head_avatars_win = True
g_checkboxes = []
g_head_avatars = []
g_folder_paths = []
g_frame_folder = []
g_file_paths = []
g_n_gaussians = []
g_n_strands = []
g_n_gaussians_per_strand = []
g_n_hair_gaussians = []
g_max_distance = []
g_means = []
g_hair_points = []
g_hair_normals = []
g_z_max = 1
g_z_min = -1
g_cutting_mode = False
g_coloring_mode = False
g_keep_sh = True
g_selected_color = [0.5, 0.5, 0.5]
g_x_plane = []
g_x_plane_max = []
g_x_plane_min = []
g_invert_x_plane = []
g_y_plane = []
g_y_plane_max = []
g_y_plane_min = []
g_invert_y_plane = []
g_z_plane = []
g_z_plane_max = []
g_z_plane_min = []
g_invert_z_plane = []

g_strand_index = "None"
g_gaussian_index = "None"
g_gaussian_strand_index = "None"

######################
# Head Avatars Actions
######################
def open_head_avatar_ply():
    global gaussians, g_z_min, g_z_max, g_folder_paths, g_file_paths, g_n_gaussians, g_n_strands, g_n_gaussians_per_strand, g_n_hair_gaussians

    file_path = filedialog.askopenfilename(
        title="open ply",
        initialdir = f"./models/",
        filetypes=[('ply file', '.ply')]
    )
    if file_path:
        try:
            # Load head avatar
            head_avatar, head_avatar_constants = util_gau.load_ply(file_path)

            # Fill controller arrays
            g_head_avatars.append(head_avatar)
            g_means.append(np.mean(head_avatar.xyz, axis=0))
            g_max_distance.append(np.max(np.linalg.norm(head_avatar.xyz - g_means[-1], axis=1)))
            g_folder_paths.append(file_path.rsplit('/', 1)[0])
            g_frame_folder.append(g_folder_paths[-1] + "/320_to_320")
            g_file_paths.append(file_path)
            g_n_gaussians.append(head_avatar.xyz.shape[0])
            g_n_strands.append(head_avatar_constants[0])
            g_n_gaussians_per_strand.append(head_avatar_constants[1])
            g_n_hair_gaussians.append(head_avatar_constants[0] * head_avatar_constants[1])
            g_checkboxes.append(True)
            hair_points, hair_normals = get_hair_points(head_avatar.xyz, head_avatar.rot, head_avatar.scale, g_n_strands[-1], g_n_gaussians_per_strand[-1], g_n_hair_gaussians[-1])
            g_hair_points.append(hair_points)
            g_hair_normals.append(hair_normals)
            g_show_hair.append(True)
            g_show_head.append(True)
            g_hair_color.append([1, 0, 0])
            g_head_color.append([1, 1, 1])
            g_show_hair_color.append(False)
            g_show_head_color.append(False)
            g_hair_scale.append(1)
            g_wave_frequency.append(0)
            g_wave_amplitude.append(0)
            g_frame.append(0)
            g_x_plane.append(np.max(head_avatar.xyz[:, 0]))
            g_x_plane_max.append(np.max(head_avatar.xyz[:, 0]))
            g_x_plane_min.append(np.min(head_avatar.xyz[:, 0]))
            g_invert_x_plane.append(False)
            g_y_plane.append(np.max(head_avatar.xyz[:, 1]))
            g_y_plane_max.append(np.max(head_avatar.xyz[:, 1]))
            g_y_plane_min.append(np.min(head_avatar.xyz[:, 1]))
            g_invert_y_plane.append(False)
            g_z_plane.append(np.max(head_avatar.xyz[:, 2]))
            g_z_plane_max.append(np.max(head_avatar.xyz[:, 2]))
            g_z_plane_min.append(np.min(head_avatar.xyz[:, 2]))
            g_invert_z_plane.append(False)
            
            if len(g_head_avatars) == 1:
                # Append head avatar to the gaussians object sent to the shader
                xyz, rot, scale, opacity, sh = head_avatar.get_data()
                gaussians.xyz = xyz
                gaussians.rot = rot
                gaussians.scale = scale
                gaussians.opacity = np.ones_like(opacity)
                gaussians.sh = sh
            else:
                # Append head avatar to the gaussians object sent to the shader
                gaussians.xyz = np.vstack([gaussians.xyz, head_avatar.xyz]).astype(np.float32)
                gaussians.rot = np.vstack([gaussians.rot, head_avatar.rot]).astype(np.float32)
                gaussians.scale = np.vstack([gaussians.scale, head_avatar.scale]).astype(np.float32)
                gaussians.opacity = np.vstack([gaussians.opacity, head_avatar.opacity]).astype(np.float32)
                gaussians.sh = np.vstack([gaussians.sh, head_avatar.sh]).astype(np.float32)

            g_renderer.update_n_gaussians(g_n_gaussians[-1])
        except RuntimeError as e:
            pass

def export_head_avatar(file_path):
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    max_sh_degree = 3

    xyz = np.copy(gaussians.xyz[start:start+g_n_gaussians[i], :]) - np.array([get_displacement(i), 0, 0])
    rot = np.copy(gaussians.rot[start:start+g_n_gaussians[i], :])
    scale = np.copy(gaussians.scale[start:start+g_n_gaussians[i], :])
    opacity = np.copy(gaussians.opacity[start:start+g_n_gaussians[i], :])
    sh = np.copy(gaussians.sh[start:start+g_n_gaussians[i], :])

    # Remove strands
    n_removed_strands = 0
    mask = np.ones((xyz.shape[0], 1)).astype(np.int16)
    for j in range(g_n_strands[i]):
        if np.sum(opacity[j*g_n_gaussians_per_strand[i]:(j+1)*g_n_gaussians_per_strand[i], :]) == 0:
            mask[j*g_n_gaussians_per_strand[i]:(j+1)*g_n_gaussians_per_strand[i], :] = 0
            n_removed_strands += 1
    mask = mask.flatten().astype(bool)
    xyz = xyz[mask, :]
    rot = rot[mask, :]
    scale = scale[mask, :]
    opacity = opacity[mask, :]
    sh = sh[mask, :]

    num_pts = xyz.shape[0]
    num_additional_features = 3 * (max_sh_degree + 1) ** 2 - 3

    # Apply inverse operations to scales and opacities
    scale = np.log(scale)
    with np.errstate(divide='ignore', invalid='ignore'): 
        opacity = np.log(opacity / (1 - opacity))

    # Normalize rotations (ensure they are already normalized)
    rot = rot / np.linalg.norm(rot, axis=-1, keepdims=True)

    # Split the SH matrix into directional coefficients and additional features
    features_dc = sh[:, :3]
    features_extra = np.hstack([sh[:, 3::3], sh[:, 4::3], sh[:, 5::3]])

    # Prepare the dtype for the structured array
    properties = [
        ('x', 'f4'),
        ('y', 'f4'),
        ('z', 'f4'),
        ('opacity', 'f4')
    ]
    for j in range(scale.shape[1]):
        properties.append((f'scale_{j}', 'f4'))
    for j in range(rot.shape[1]):
        properties.append((f'rot_{j}', 'f4'))
    properties.extend([
        ('f_dc_0', 'f4'),
        ('f_dc_1', 'f4'),
        ('f_dc_2', 'f4')
    ])
    for j in range(num_additional_features):
        properties.append((f'f_rest_{j}', 'f4'))

    properties.append(('n_strands', 'i4'))
    properties.append(('n_gaussians_per_strand', 'i4'))

    # Create a structured array
    vertices = np.empty(num_pts, dtype=properties)
    # Gaussian means
    vertices['x'] = xyz[:, 0]
    vertices['y'] = xyz[:, 1]
    vertices['z'] = xyz[:, 2]
    # Opacities
    vertices['opacity'] = opacity[:, 0]
    # Scales
    for j in range(scale.shape[1]):
        vertices[f'scale_{j}'] = scale[:, j]
    # Rotations
    for j in range(rot.shape[1]):
        vertices[f'rot_{j}'] = rot[:, j]
    # Colors
    vertices['f_dc_0'] = features_dc[:, 0]
    vertices['f_dc_1'] = features_dc[:, 1]
    vertices['f_dc_2'] = features_dc[:, 2]
    for j in range(num_additional_features):
        vertices[f'f_rest_{j}'] = features_extra[:, j]

    vertices['n_strands'] = g_n_strands[i] - n_removed_strands
    vertices['n_gaussians_per_strand'] = g_n_gaussians_per_strand[i]

    # Create PLY element
    vertex_element = PlyElement.describe(vertices, 'vertex')

    # Write to PLY file
    PlyData([vertex_element]).write(file_path)


##################################
# Head Avatar Controller Variables
##################################
g_show_head_avatar_controller_win = True
g_selected_head_avatar_index = -1
g_selected_head_avatar_name = "None"
g_show_hair = []
g_show_head = []
g_hair_color = []
g_head_color = []
g_show_hair_color = []
g_show_head_color = []
g_hair_scale = []
g_wave_frequency = []
g_wave_amplitude = []
g_frame = []

################################
# Head Avatar Controller Actions
################################
def get_start_index(head_avatar_index):
    if head_avatar_index == 0:
        return 0
    return np.cumsum(g_n_gaussians)[head_avatar_index - 1]

def get_closest_head_avatar_index():
    if len(g_head_avatars) == 0 or np.sum(g_checkboxes) == 0:
        return -1

    # Get means of displayed head avatars
    avatar_means = np.vstack([g_means[i] for i in range(len(g_head_avatars)) if g_checkboxes[i]])

    # Get mouse 3D position
    mouse_pos_2d = imgui.get_io().mouse_pos
    mouse_pos_3d = util.glhUnProjectf(mouse_pos_2d.x, mouse_pos_2d.y, 1, g_camera.get_view_matrix(), g_camera.get_project_matrix(), gl.glGetIntegerv(gl.GL_VIEWPORT))

    # Compute ray direction
    ray_direction = mouse_pos_3d - g_camera.position
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    # Compute dot product to project each vector onto the ray
    ray_projection = (avatar_means - g_camera.position) @ ray_direction

    # Compute closest point on the ray for each head avatar mean
    closest_points_on_ray = g_camera.position + ray_projection[:, np.newaxis] * ray_direction

    # Compute distances between each head avatar mean and its closest point on the ray
    distances = np.linalg.norm(avatar_means - closest_points_on_ray, axis=1)

    # Get index of the closest point
    closest_point_index = np.argmin(distances)

    # Get index of closest head avatar
    closest_head_avatar_index = np.where(np.cumsum(g_checkboxes) - 1 == closest_point_index)[0][0]

    # Get minimal distance 
    min_dist = np.min(distances)
    if min_dist >= g_max_distance[closest_head_avatar_index]:
        return -1

    return closest_head_avatar_index

def select_head_avatar(head_avatar_index):
    global g_selected_head_avatar_index, g_selected_head_avatar_name

    if head_avatar_index == -1:
        g_selected_head_avatar_index = -1
        g_selected_head_avatar_name = "None"

        g_renderer.update_cutting_mode(False)
        g_renderer.update_coloring_mode(False)
    else:
        g_selected_head_avatar_index = head_avatar_index
        g_selected_head_avatar_name = "Head Avatar " + str(g_selected_head_avatar_index + 1)

        g_renderer.update_selected_head_avatar_index(g_selected_head_avatar_index)

        g_renderer.update_cutting_mode(g_cutting_mode)
        g_renderer.update_coloring_mode(g_coloring_mode)

        g_renderer.update_start(get_start_index(g_selected_head_avatar_index))
        g_renderer.update_n_gaussians(g_n_gaussians[g_selected_head_avatar_index])
        g_renderer.update_n_hair_gaussians(g_n_hair_gaussians[g_selected_head_avatar_index])

        g_renderer.update_x_plane(g_x_plane[g_selected_head_avatar_index] + get_displacement(g_selected_head_avatar_index))
        g_renderer.update_y_plane(g_y_plane[g_selected_head_avatar_index])
        g_renderer.update_z_plane(g_z_plane[g_selected_head_avatar_index])
        g_renderer.update_invert_x_plane(g_invert_x_plane[g_selected_head_avatar_index])
        g_renderer.update_invert_y_plane(g_invert_y_plane[g_selected_head_avatar_index])
        g_renderer.update_invert_z_plane(g_invert_z_plane[g_selected_head_avatar_index])


def select_closest_gaussian():
    if g_selected_head_avatar_index == -1:
        return None, None

    # Get means, colors, and opacities of selected head avatar
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    xyz = gaussians.xyz[start:start+g_n_gaussians[i], :]
    color = gaussians.sh[start:start+g_n_gaussians[i], :]
    opacity = gaussians.opacity[start:start+g_n_gaussians[i], :]

    # Filter rows according to opacity
    opacity_mask = (opacity != 0).flatten()
    xyz = xyz[opacity_mask, :]
    color = color[opacity_mask, :]

    # Filter rows according to xyz-planes
    if g_coloring_mode:
        if g_invert_x_plane[i]:
            x_mask = (xyz[:, 0] >= (g_x_plane[i] + get_displacement(i))).flatten()
        else:
            x_mask = (xyz[:, 0] <= (g_x_plane[i] + get_displacement(i))).flatten()
        if g_invert_y_plane[i]:
            y_mask = (xyz[:, 1] >= g_y_plane[i]).flatten()
        else:
            y_mask = (xyz[:, 1] <= g_y_plane[i]).flatten()
        if g_invert_z_plane[i]:
            z_mask = (xyz[:, 2] >= g_z_plane[i]).flatten()
        else:
            z_mask = (xyz[:, 2] <= g_z_plane[i]).flatten() 
        xyz = xyz[x_mask & y_mask & z_mask, :]
        color = color[x_mask & y_mask & z_mask, :]

    # Get mouse 3D position
    mouse_pos_2d = imgui.get_io().mouse_pos
    mouse_pos_3d = util.glhUnProjectf(mouse_pos_2d.x, mouse_pos_2d.y, 1, g_camera.get_view_matrix(), g_camera.get_project_matrix(), gl.glGetIntegerv(gl.GL_VIEWPORT))

    # Compute ray direction
    ray_direction = mouse_pos_3d - g_camera.position
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    # Compute dot product to project each vector onto the ray
    ray_projection = (xyz - g_camera.position) @ ray_direction

    # Compute closest point on the ray for each hair gaussian
    closest_points_on_ray = g_camera.position + ray_projection[:, np.newaxis] * ray_direction

    # Compute distances between each head avatar mean and its closest point on the ray
    distances = np.linalg.norm(xyz - closest_points_on_ray, axis=1)
    distance_mask = distances < g_selection_distance
    xyz = xyz[distance_mask, :]
    color = color[distance_mask, :]

    if len(xyz) == 0:
        return None, None

    # Index closest point
    closest_point_indices = np.argsort(np.linalg.norm(xyz - g_camera.position, axis=1))[:20]
    closest_point_relative_index = closest_point_indices[0]
    closest_point_index = np.where(np.all(gaussians.xyz[start:start+g_n_gaussians[i], :] == xyz[closest_point_relative_index], axis=1))[0][0]

    return closest_point_index, np.mean(color[closest_point_indices, 0:3], axis=0)

def update_displacements_and_opacities():
    global gaussians

    for i in range(len(g_head_avatars)):
        xyz, _, _, opacity, _ = g_head_avatars[i].get_data()
        start = get_start_index(i)

        if g_checkboxes[i] and (g_show_hair[i] or g_show_head[i]):
            update_means(i)
            gaussians.opacity[start:start+g_n_gaussians[i], :] = np.vstack([opacity[:g_n_hair_gaussians[i], :] * g_show_hair[i], opacity[g_n_hair_gaussians[i]:, :] * g_show_head[i]])
        else:
            gaussians.opacity[start:start+g_n_gaussians[i], :] = 0

def update_head_opacity():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    if g_show_head[i]:
        _, _, _, opacity, _ = g_head_avatars[i].get_data()
        gaussians.opacity[start+g_n_hair_gaussians[i]:start+g_n_gaussians[i], :] = opacity[g_n_hair_gaussians[i]:, :]
    else:
        gaussians.opacity[start+g_n_hair_gaussians[i]:start+g_n_gaussians[i], :] = 0

def update_hair_opacity():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    if g_show_hair[i]:
        _, _, _, opacity, _ = g_head_avatars[i].get_data()
        gaussians.opacity[start:start+g_n_hair_gaussians[i], :] = opacity[:g_n_hair_gaussians[i], :]
    else:
        gaussians.opacity[start:start+g_n_hair_gaussians[i], :] = 0

def update_head_color():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    if g_show_head_color[i]:
        gaussians.sh[start+g_n_hair_gaussians[i]:start+g_n_gaussians[i], 0:3] = np.asarray(g_head_color[i]).T
    else:
        _, _, _, _, sh = g_head_avatars[i].get_data()
        gaussians.sh[start+g_n_hair_gaussians[i]:start+g_n_gaussians[i], :] = sh[g_n_hair_gaussians[i]:, :]

def update_hair_color():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    if g_show_hair_color[i]:
        gaussians.sh[start:start+g_n_hair_gaussians[i], 0:3] = np.asarray(g_hair_color[i]).T
    else:
        _, _, _, _, sh = g_head_avatars[i].get_data()
        gaussians.sh[start:start+g_n_hair_gaussians[i], :] = sh[:g_n_hair_gaussians[i], :]

def update_hair_scale():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    _, _, scale, _, _ = g_head_avatars[i].get_data()
    gaussians.scale[start:start+g_n_hair_gaussians[i], :] = scale[:g_n_hair_gaussians[i]] * g_hair_scale[i]

def update_frame():
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    xyz, rot = get_frame(i)
    g_head_avatars[i].xyz[:g_n_hair_gaussians[i]] = xyz
    g_head_avatars[i].rot[:g_n_hair_gaussians[i]] = rot
    gaussians.rot[start:start+g_n_hair_gaussians[i], :] = rot
    update_means(i)

def update_means(head_avatar_index):
    i = head_avatar_index
    start = get_start_index(i)

    xyz, rot, scale, _, _ = g_head_avatars[i].get_data()
    gaussians.xyz[start:start+g_n_gaussians[i], :] = xyz

    f, _ = get_frame(i)
    gaussians.xyz[start:start+g_n_hair_gaussians[i], :] = f

    d = get_displacement(i)
    gaussians.xyz[start:start+g_n_gaussians[i], 0] += d

    gaussians.rot[start:start+g_n_gaussians[i], :] = rot[:g_n_gaussians[i], :]
    gaussians.scale[start:start+g_n_gaussians[i], :] = scale[:g_n_gaussians[i], :]

    # Handling case for which there are no hair strands. Able to open a generic gaussian ply
    # And the case where there's zero frequency or amplitude
    if (g_hair_points[i].shape[0] != 0  and 
        len(g_wave_amplitude)*len(g_wave_frequency)!=0 and g_wave_frequency[i]*g_wave_amplitude[i]!=0):
        points = np.copy(g_hair_points[i])
        points[:,:,0] += d
        
        global_nudging = get_curls(g_wave_amplitude[i], g_wave_frequency[i], g_hair_normals[i], g_n_gaussians_per_strand[i], g_n_strands[i])
        new_points = points+global_nudging
        xyz, scale = calculate_pts_scal(new_points)
        
        # New gaussians from new points either from file or calculated on the spot
        try:
            path = util.find_closest_file(g_wave_amplitude[i], g_wave_frequency[i], f"{g_folder_paths[i]}/rots/")
            rot = np.load(path)[:g_n_strands[i], :g_n_gaussians_per_strand[i]]

        except FileNotFoundError:
            rot = calculate_rot_quat(new_points)

        gaussians.xyz[start:start+g_n_hair_gaussians[i], :] = xyz.reshape(-1,3)
        gaussians.rot[start:start+g_n_hair_gaussians[i], :] = rot.reshape(-1,4)
        gaussians.scale[start:start+g_n_hair_gaussians[i], :] = scale.reshape(-1,3)*g_hair_scale[i]

    g_means[i] = np.mean(gaussians.xyz[start:start+g_n_gaussians[i]], axis=0)

def get_displacement(head_avatar_index):
    # Get index of first displayed head avatar index
    i = np.argmax(g_checkboxes)

    if head_avatar_index == i:
        return 0
    
    width = np.array(g_checkboxes) * (np.array(g_x_plane_max) - np.array(g_x_plane_min))

    d = g_x_plane_max[i] - g_x_plane_min[head_avatar_index] + AVATAR_SEPARATION
    for j in range(i + 1, head_avatar_index):
        d += width[j] + g_checkboxes[j] * AVATAR_SEPARATION
    
    return d

def get_hair_points(xyz, rot, scale, n_strands, n_gaussians_per_strand, n_hair_gaussians):
    if n_strands == 0:
        return np.array([]), np.array([]),

    strands = np.zeros((n_strands, n_gaussians_per_strand+1, 3))
    strands_xyz = xyz[:n_hair_gaussians].reshape(n_strands, n_gaussians_per_strand, -1)
    strands_rot = rot[:n_hair_gaussians].reshape(n_strands, n_gaussians_per_strand, -1)
    strands_scale = scale[:n_hair_gaussians].reshape(n_strands, n_gaussians_per_strand, -1)

    w, x, y, z = strands_rot.transpose(2, 0, 1)
    global_x_displacement = np.array([1. - 2. * (y * y + z * z), 2. * (x * y + w * z), 2. * (x * z - w * y)]).transpose(1,2,0)
    
    displacements = 0.5*strands_scale*global_x_displacement 
    strands[:,0] = strands_xyz[:,0] - displacements[:,0]
    strands[:,1:] = strands_xyz + displacements

    # Mean x-displacement of the hair gaussians after first couple gaussians
    start = n_gaussians_per_strand//10
    mean_last_disps = np.mean(global_x_displacement[:,start:], axis=1)

    # Orthogonal vectors which lie on the plane perpendicular to hair
    normals = np.zeros_like(mean_last_disps)
    normals[:, 0], normals[:, 1] = mean_last_disps[:, 1], -mean_last_disps[:, 0]
    binormals = np.cross(mean_last_disps, normals)
    normals /= np.linalg.norm(normals, axis=1)[:,np.newaxis]
    binormals /= np.linalg.norm(binormals, axis=1)[:,np.newaxis]
    disps = np.stack((normals, binormals))
    return strands, disps

def get_curls(amp, freq, hair_normals, n_gaussians_per_strand, n_strands):
    t = np.linspace(0, 2, n_gaussians_per_strand+1)[:,np.newaxis].T
    
    # Fixing random seed for future random initial frequency and overall noise
    np.random.seed(0)
    random_init_freq = np.random.uniform(low=0, high=2*np.pi, size=(n_strands,1))
    # Parameter t with random initial values so it doesn't look too uniform
    t_strands = t+random_init_freq
    # Multiplier to t value so it curls either way
    random_dir = np.random.choice([-1, 1], size=(n_strands,1))

    # Quadratic so hair roots are not displaced
    amplitude = (t**2*amp)[:,:,np.newaxis]
    # Sine and cosine to get coil shaped curls and not one-dimensional
    sin_wave = amplitude*np.sin(random_dir*(np.pi * freq * t + t_strands))[:,:,np.newaxis]
    cos_wave = amplitude*np.cos(random_dir*(np.pi * freq * t + t_strands))[:,:,np.newaxis]

    sin_noise = cos_noise = 0 
    if amp!=0:
        sin_noise = np.random.normal(0, amp/30, size=sin_wave.shape)
        cos_noise = np.random.normal(0, amp/30, size=cos_wave.shape)

    # The curls are applied along the two vectors that form the plane perpendicular to the hair
    global_nudging = (sin_wave+sin_noise)*hair_normals[0][:,np.newaxis] + (cos_wave+cos_noise)*hair_normals[1][:,np.newaxis]
    return global_nudging

def get_frame(head_avatar_index):
    i = head_avatar_index
    try:
        xyz = np.load(f"{g_frame_folder[i]}//frame_{g_frame[i]}_mean_frenet.npy").reshape(-1, 3)
        rot = np.load(f"{g_frame_folder[i]}//frame_{g_frame[i]}_rot_frenet.npy").transpose((0, 1, 3, 2))
        rot = TNB2qvecs(rot[:,:,0], rot[:,:,1], rot[:,:,2]).reshape(-1,4)
        _, _, scale, _, _ = g_head_avatars[i].get_data()
        hair_points, hair_normals = get_hair_points(xyz, rot, scale, g_n_strands[i], g_n_gaussians_per_strand[i], g_n_hair_gaussians[i])
        g_hair_points[i] = hair_points
        g_hair_normals[i] = hair_normals
    except Exception as e:
        xyz, rot, _, _, _ = g_head_avatars[i].get_data()
    return xyz[:g_n_hair_gaussians[i], :].astype(np.float32), rot[:g_n_hair_gaussians[i], :].astype(np.float32)

def cut_hair():
    # Get hair gaussians of selected head avatar
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    hair_gaussians = gaussians.xyz[start:start+g_n_hair_gaussians[i], :]

    # Get mouse 3D position
    mouse_pos_2d = imgui.get_io().mouse_pos
    mouse_pos_3d = util.glhUnProjectf(mouse_pos_2d.x, mouse_pos_2d.y, 1, g_camera.get_view_matrix(), g_camera.get_project_matrix(), gl.glGetIntegerv(gl.GL_VIEWPORT))

    # Compute ray direction
    ray_direction = mouse_pos_3d - g_camera.position
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    # Compute dot product to project each vector onto the ray
    ray_projection = (hair_gaussians - g_camera.position) @ ray_direction

    # Compute closest point on the ray for each hair gaussian
    closest_points_on_ray = g_camera.position + ray_projection[:, np.newaxis] * ray_direction

    # Compute distances between each head avatar mean and its closest point on the ray
    distances = np.linalg.norm(hair_gaussians - closest_points_on_ray, axis=1)

    # Zero the opacity of the closest hair gaussians
    g_head_avatars[i].opacity[:g_n_hair_gaussians[i], :][distances < g_max_cutting_distance, :] = 0
    gaussians.opacity[start:start+g_n_hair_gaussians[i], :][distances < g_max_cutting_distance, :] = 0

    # Make sure there are no flying strands
    for j in range(g_n_strands[i]):
        k = np.where(g_head_avatars[i].opacity[j*g_n_gaussians_per_strand[i]:(j+1)*g_n_gaussians_per_strand[i], :] == 0)[0]
        if len(k) > 0:
            k = k[0]
            g_head_avatars[i].opacity[j*g_n_gaussians_per_strand[i]+k:(j+1)*g_n_gaussians_per_strand[i], :] = 0
            gaussians.opacity[start+j*g_n_gaussians_per_strand[i]+k:start+(j+1)*g_n_gaussians_per_strand[i], :] = 0

            if k != 0:
                g_head_avatars[i].xyz[j*g_n_gaussians_per_strand[i]+k:(j+1)*g_n_gaussians_per_strand[i], :] = g_head_avatars[i].xyz[j*g_n_gaussians_per_strand[i]+k-1, :]
                gaussians.xyz[start+j*g_n_gaussians_per_strand[i]+k:start+(j+1)*g_n_gaussians_per_strand[i], :] = gaussians.xyz[start+j*g_n_gaussians_per_strand[i]+k, :]


def reset_cut():
    file_path = g_file_paths[g_selected_head_avatar_index]
    if file_path:
        try:
            # Set opacity from original head avatar
            head_avatar, _ = util_gau.load_ply(file_path)
            xyz, _, _, opacity, _ = head_avatar.get_data()
            i = g_selected_head_avatar_index
            start = get_start_index(i)
            g_head_avatars[i].opacity[:g_n_hair_gaussians[i], :] = opacity[:g_n_hair_gaussians[i], :]
            g_head_avatars[i].xyz = xyz
            update_hair_opacity()
        except RuntimeError as e:
                pass

def color_hair():
    # Get means, colors, and opacities of selected head avatar
    i = g_selected_head_avatar_index
    start = get_start_index(i)
    xyz = gaussians.xyz[start:start+g_n_gaussians[i], :]
    color = gaussians.sh[start:start+g_n_gaussians[i], :]
    opacity = gaussians.opacity[start:start+g_n_gaussians[i], :]

    # Filter rows according to opacity
    opacity_mask = (opacity != 0).flatten()
    xyz = xyz[opacity_mask, :]
    color = color[opacity_mask, :]

    # Filter rows according to xyz-planes
    if g_invert_x_plane[i]:
        x_mask = (xyz[:, 0] >= (g_x_plane[i] + get_displacement(i))).flatten()
    else:
        x_mask = (xyz[:, 0] <= (g_x_plane[i] + get_displacement(i))).flatten()
    if g_invert_y_plane[i]:
        y_mask = (xyz[:, 1] >= g_y_plane[i]).flatten()
    else:
        y_mask = (xyz[:, 1] <= g_y_plane[i]).flatten()
    if g_invert_z_plane[i]:
        z_mask = (xyz[:, 2] >= g_z_plane[i]).flatten()
    else:
        z_mask = (xyz[:, 2] <= g_z_plane[i]).flatten() 
    xyz = xyz[x_mask & y_mask & z_mask, :]
    color = color[x_mask & y_mask & z_mask, :]

    # Get mouse 3D position
    mouse_pos_2d = imgui.get_io().mouse_pos
    mouse_pos_3d = util.glhUnProjectf(mouse_pos_2d.x, mouse_pos_2d.y, 1, g_camera.get_view_matrix(), g_camera.get_project_matrix(), gl.glGetIntegerv(gl.GL_VIEWPORT))

    # Compute ray direction
    ray_direction = mouse_pos_3d - g_camera.position
    ray_direction = ray_direction / np.linalg.norm(ray_direction)

    # Compute dot product to project each vector onto the ray
    ray_projection = (xyz - g_camera.position) @ ray_direction

    # Compute closest point on the ray for each hair gaussian
    closest_points_on_ray = g_camera.position + ray_projection[:, np.newaxis] * ray_direction

    # Compute distances between each head avatar mean and its closest point on the ray
    distances = np.linalg.norm(xyz - closest_points_on_ray, axis=1)
    distance_mask = distances < g_max_coloring_distance

    # Compute final indices
    final_indices = np.where(opacity_mask)[0][np.where(x_mask & y_mask & z_mask)[0][np.where(distance_mask)[0]]]

    # Color the closest hair gaussians
    g_head_avatars[i].sh[final_indices, 0:3] = g_selected_color
    gaussians.sh[start:start+g_n_gaussians[i], :][final_indices, 0:3] = g_selected_color
    if not g_keep_sh:
        g_head_avatars[i].sh[final_indices, 3:] = 0
        gaussians.sh[start:start+g_n_gaussians[i], :][final_indices, 3:] = 0

def reset_coloring():
    file_path = g_file_paths[g_selected_head_avatar_index]
    if file_path:
        try:
            # Set opacity from original head avatar
            head_avatar, _ = util_gau.load_ply(file_path)
            _, _, _, _, color = head_avatar.get_data()
            i = g_selected_head_avatar_index
            start = get_start_index(i)
            g_head_avatars[i].sh = color
            gaussians.sh[start:start+g_n_gaussians[i], :] = color
            update_hair_color()
        except RuntimeError as e:
                pass

#####################

def impl_glfw_init():
    window_name = "Dynamic Gaussian Visualizer"

    if not glfw.init():
        print("Could not initialize OpenGL context")
        exit(1)

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    # glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

    # Create a windowed mode window and its OpenGL context
    global window
    window = glfw.create_window(
        g_camera.w, g_camera.h, window_name, None, None
    )
    glfw.make_context_current(window)
    glfw.swap_interval(0)
    # glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_NORMAL);
    if not window:
        glfw.terminate()
        print("Could not initialize Window")
        exit(1)

    return window

def cursor_pos_callback(window, xpos, ypos):
    if imgui.get_io().want_capture_mouse:
        g_camera.is_leftmouse_pressed = False
        g_camera.is_rightmouse_pressed = False
    if g_cutting_mode or g_coloring_mode or g_render_mode == 0:
        g_renderer.update_ray_direction(g_camera, imgui.get_io().mouse_pos)
    g_camera.process_mouse(xpos, ypos)

def mouse_button_callback(window, button, action, mod):
    if imgui.get_io().want_capture_mouse:
        return
    pressed = action == glfw.PRESS
    g_camera.is_leftmouse_pressed = (button == glfw.MOUSE_BUTTON_LEFT and pressed)
    g_camera.is_rightmouse_pressed = (button == glfw.MOUSE_BUTTON_RIGHT and pressed)

    # Mouse Controller Variables
    global left_click_start_time, right_click_start_time, g_selected_color, g_strand_index, g_gaussian_index, g_gaussian_strand_index

    # Record the time when the left mouse button is pressed
    if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
        left_click_start_time = time.time()

    # Record the time when the right mouse button is pressed
    if button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
        right_click_start_time = time.time()

    # Select closest head avatar and/or select color
    if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.RELEASE:
        end_time = time.time()
        left_click_duration = end_time - left_click_start_time
        
        if left_click_duration < CLICK_THRESHOLD:
            closest_head_avatar_index = get_closest_head_avatar_index()
            select_head_avatar(closest_head_avatar_index)
            closest_point_index, selected_color = select_closest_gaussian()
            if closest_point_index is None:
                g_strand_index = "None"
                g_gaussian_index = "None"
                g_gaussian_strand_index = "None"

                select_head_avatar(-1)
            else:
                g_gaussian_index = closest_point_index
                if closest_point_index < g_n_hair_gaussians[g_selected_head_avatar_index]:
                    g_strand_index = closest_point_index // g_n_gaussians_per_strand[g_selected_head_avatar_index]
                    g_gaussian_strand_index = closest_point_index % g_n_gaussians_per_strand[g_selected_head_avatar_index]
                else:
                    g_strand_index = "None"
                    g_gaussian_strand_index = "None"

                if g_coloring_mode:
                    g_selected_color = selected_color
                    g_renderer.update_selected_color(g_selected_color)           

    # Cut or Color
    if button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.RELEASE:
        end_time = time.time()
        right_click_duration = end_time - right_click_start_time
        
        if right_click_duration < CLICK_THRESHOLD and g_cutting_mode and g_selected_head_avatar_index != -1:
            cut_hair()
            g_renderer.update_gaussian_data(gaussians)

        if right_click_duration < CLICK_THRESHOLD and g_coloring_mode and g_selected_head_avatar_index != -1:
            color_hair()
            g_renderer.update_gaussian_data(gaussians)

def wheel_callback(window, dx, dy):
    g_camera.process_wheel(dx, dy)

def key_callback(window, key, scancode, action, mods):
    if action == glfw.REPEAT or action == glfw.PRESS:
        if key == glfw.KEY_Q:
            g_camera.process_roll_key(1)
        elif key == glfw.KEY_E:
            g_camera.process_roll_key(-1)

def update_camera_pose_lazy():
    if g_camera.is_pose_dirty:
        g_renderer.update_camera_pose(g_camera)
        g_camera.is_pose_dirty = False

def update_camera_intrin_lazy():
    if g_camera.is_intrin_dirty:
        g_renderer.update_camera_intrin(g_camera)
        g_camera.is_intrin_dirty = False

def update_activated_renderer_state(gaussians: util_gau.GaussianData):
    g_renderer.update_gaussian_data(gaussians)
    g_renderer.sort_and_update(g_camera)
    g_renderer.set_scale_modifier(g_scale_modifier)
    g_renderer.set_render_mod(g_render_mode - 3)
    g_renderer.update_camera_pose(g_camera)
    g_renderer.update_camera_intrin(g_camera)
    g_renderer.set_render_reso(g_camera.w, g_camera.h)

def window_resize_callback(window, width, height):
    gl.glViewport(0, 0, width, height)
    g_camera.update_resolution(height, width)
    g_renderer.set_render_reso(width, height)


def main():
    global g_camera, g_renderer, g_renderer_list, g_renderer_idx, g_scale_modifier, g_auto_sort, \
        g_show_control_win, g_show_help_win, g_show_camera_win, \
        g_render_mode, g_render_mode_tables

    # Head Avatars Global Variables
    global gaussians, g_show_head_avatars_win, g_checkboxes, g_cutting_mode, \
        g_coloring_mode, g_keep_sh, g_selected_color, g_max_cutting_distance, g_max_coloring_distance, g_x_min, g_x_max, g_x_plane, g_invert_x_plane, \
         g_y_min, g_y_max, g_y_plane, g_invert_y_plane, g_z_min, g_z_max, g_z_plane, g_invert_z_plane, g_hair_points, g_hair_normals

    # Head Avatar Controller Global Variables
    global g_show_head_avatar_controller_win, g_selected_head_avatar_index, g_selected_head_avatar_name, \
        g_show_hair, g_show_head, g_hair_color, g_head_color, g_show_hair_color, g_show_head_color, g_hair_scale, \
        g_wave_frequency, g_wave_amplitude, g_frame
        
    imgui.create_context()
    if args.hidpi:
        imgui.get_io().font_global_scale = 1.5
    window = impl_glfw_init()
    impl = GlfwRenderer(window)
    root = tk.Tk()  # used for file dialog
    root.withdraw()
   
    glfw.set_cursor_pos_callback(window, cursor_pos_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_scroll_callback(window, wheel_callback)
    glfw.set_key_callback(window, key_callback)
    
    glfw.set_window_size_callback(window, window_resize_callback)

    # init renderer
    g_renderer_list[BACKEND_OGL] = OpenGLRenderer(g_camera.w, g_camera.h)
    g_renderer_list[BACKEND_OGL_AXES] = OpenGLRendererAxes(g_camera.w, g_camera.h)
    g_renderer = g_renderer_list[g_renderer_idx]

    # gaussian data
    update_activated_renderer_state(gaussians)    

    # Set parameters in shader
    g_renderer.update_cutting_mode(g_cutting_mode)
    g_renderer.update_max_cutting_distance(g_max_cutting_distance)
    g_renderer.update_max_coloring_distance(g_max_coloring_distance)
    g_renderer.update_coloring_mode(g_coloring_mode)
    g_renderer.update_keep_sh(g_keep_sh)
    g_renderer.update_selected_color(g_selected_color)

    # maximize window
    glfw.maximize_window(window)
    
    # settings
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        
        gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        update_camera_pose_lazy()
        update_camera_intrin_lazy()
        
        g_renderer.draw()

        # imgui ui
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("Window", True):
                clicked, g_show_control_win = imgui.menu_item(
                    "Show Control", None, g_show_control_win
                )
                clicked, g_show_help_win = imgui.menu_item(
                    "Show Help", None, g_show_help_win
                )
                clicked, g_show_camera_win = imgui.menu_item(
                    "Show Camera Control", None, g_show_camera_win
                )
                clicked, g_show_head_avatars_win = imgui.menu_item(
                    "Show Head Avatars", None, g_show_head_avatars_win
                )
                clicked, g_show_head_avatar_controller_win = imgui.menu_item(
                    "Show Head Avatar Controller", None, g_show_head_avatar_controller_win
                )
                imgui.end_menu()
            imgui.end_main_menu_bar()
        
        if g_show_control_win:
            if imgui.begin("Control", True):
                # rendering backend
                changed, g_renderer_idx = imgui.combo("backend", g_renderer_idx, ["ogl", "axes"][:len(g_renderer_list)])
                if changed:
                    g_renderer = g_renderer_list[g_renderer_idx]
                    update_activated_renderer_state(gaussians)

                imgui.text(f"fps = {imgui.get_io().framerate:.1f}")

                changed, g_renderer.reduce_updates = imgui.checkbox( "reduce updates", g_renderer.reduce_updates,)

                imgui.text(f"# of Gaus = {gaussians.xyz.shape[0]}")
                if imgui.button(label='open ply'):
                    file_path = filedialog.askopenfilename(title="open ply",
                        initialdir="./data",
                        filetypes=[('ply file', '.ply')]
                        )
                    if file_path:
                        try:
                            gaussians, _ = util_gau.load_ply(file_path)
                            g_renderer.update_gaussian_data(gaussians)
                            g_renderer.sort_and_update(g_camera)
                        except RuntimeError as e:
                            pass
                
                # camera fov
                changed, g_camera.fovy = imgui.slider_float(
                    "fov", g_camera.fovy, 0.001, np.pi - 0.001, "fov = %.3f"
                )
                g_camera.is_intrin_dirty = changed
                update_camera_intrin_lazy()
                
                # scale modifier
                changed, g_scale_modifier = imgui.slider_float(
                    "scale", g_scale_modifier, 0.1, 10, "scale modifier = %.3f"
                )
                imgui.same_line()
                if imgui.button(label="reset"):
                    g_scale_modifier = 1.
                    changed = True
                    
                if changed:
                    g_renderer.set_scale_modifier(g_scale_modifier)
                
                # render mode
                changed, g_render_mode = imgui.combo("shading", g_render_mode, g_render_mode_tables)
                if changed:
                    g_renderer.set_render_mod(g_render_mode - 5)
                
                # sort button
                if imgui.button(label='sort Gaussians'):
                    g_renderer.sort_and_update(g_camera)
                imgui.same_line()
                changed, g_auto_sort = imgui.checkbox(
                        "auto sort", g_auto_sort,
                    )
                if g_auto_sort:
                    g_renderer.sort_and_update(g_camera)
                
                if imgui.button(label='save image'):
                    width, height = glfw.get_framebuffer_size(window)
                    nrChannels = 3;
                    stride = nrChannels * width;
                    stride += (4 - stride % 4) if stride % 4 else 0
                    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 4)
                    gl.glReadBuffer(gl.GL_FRONT)
                    bufferdata = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
                    img = np.frombuffer(bufferdata, np.uint8, -1).reshape(height, width, 3)
                    imageio.imwrite("save.png", img[::-1])
                    # save intermediate information
                    # np.savez(
                    #     "save.npz",
                    #     gau_xyz=gaussians.xyz,
                    #     gau_s=gaussians.scale,
                    #     gau_rot=gaussians.rot,
                    #     gau_c=gaussians.sh,
                    #     gau_a=gaussians.opacity,
                    #     viewmat=g_camera.get_view_matrix(),
                    #     projmat=g_camera.get_project_matrix(),
                    #     hfovxyfocal=g_camera.get_htanfovxy_focal()
                    # )
                imgui.end()

        if g_show_camera_win:
            if imgui.button(label='rot 180'):
                g_camera.flip_ground()

            changed, g_camera.target_dist = imgui.slider_float(
                    "t", g_camera.target_dist, 1., 8., "target dist = %.3f"
                )
            if changed:
                g_camera.update_target_distance()

            changed, g_camera.rot_sensitivity = imgui.slider_float(
                    "r", g_camera.rot_sensitivity, 0.002, 0.1, "rotate speed = %.3f"
                )
            imgui.same_line()
            if imgui.button(label="reset r"):
                g_camera.rot_sensitivity = 0.002

            changed, g_camera.trans_sensitivity = imgui.slider_float(
                    "m", g_camera.trans_sensitivity, 0.001, 0.03, "move speed = %.3f"
                )
            imgui.same_line()
            if imgui.button(label="reset m"):
                g_camera.trans_sensitivity = 0.01

            changed, g_camera.zoom_sensitivity = imgui.slider_float(
                    "z", g_camera.zoom_sensitivity, 0.001, 0.05, "zoom speed = %.3f"
                )
            imgui.same_line()
            if imgui.button(label="reset z"):
                g_camera.zoom_sensitivity = 0.01

            changed, g_camera.roll_sensitivity = imgui.slider_float(
                    "ro", g_camera.roll_sensitivity, 0.003, 0.1, "roll speed = %.3f"
                )
            imgui.same_line()
            if imgui.button(label="reset ro"):
                g_camera.roll_sensitivity = 0.03

        if g_show_help_win:
            imgui.begin("Help", True)
            imgui.text("Open Gaussian Splatting PLY file \n  by click 'open ply' button")
            imgui.text("Use left click & move to rotate camera")
            imgui.text("Use right click & move to translate camera")
            imgui.text("Press Q/E to roll camera")
            imgui.text("Use scroll to zoom in/out")
            imgui.text("Use control panel to change setting \n")
            imgui.text("\n")
            imgui.text("Open Gaussian Splatting Head PLY file \n  by click 'open head avatar ply' button")
            imgui.text("Left click on avatar to select and show its \n Head Avatar Controller window")
            imgui.text("In coloring and cutting hair mode, \n right click to color model or cut hair")
            imgui.text("Use Head Avatar Controller to cut hair, \n color model, change hair frequency and \n amplitude, select frame, and export \n modified model")
            imgui.end()

        # Head Avatars Window
        if g_show_head_avatars_win:
            imgui.begin("Head Avatars", True)

            # Load Head avatar button
            if imgui.button(label='open head avatar ply'):
                open_head_avatar_ply()
                update_displacements_and_opacities()
                select_head_avatar(len(g_head_avatars) - 1)
                g_renderer.update_gaussian_data(gaussians)
                
            # Display Head Avatar Checkboxes
            for i in range(len(g_head_avatars)):
                changed, g_checkboxes[i] = imgui.checkbox(f"Head Avatar {i + 1}", g_checkboxes[i])
                if changed:
                    if not g_checkboxes[i] and i == g_selected_head_avatar_index:
                        g_selected_head_avatar_index = -1
                    if g_checkboxes[i]:
                        g_selected_head_avatar_index = i
                    select_head_avatar(g_selected_head_avatar_index)
                    update_displacements_and_opacities()
                    g_renderer.update_gaussian_data(gaussians)
            
            imgui.end()

        # Head Avatar Controller Window
        if g_show_head_avatar_controller_win:
            imgui.begin("Head Avatar Controller", True)

            imgui.text(f"Selected: {g_selected_head_avatar_name}")

            if g_selected_head_avatar_index != -1:
                i = g_selected_head_avatar_index

                imgui.text(f"Selected Gaussian Index: {g_gaussian_index}")
                imgui.text(f"Selected Strand Index: {g_strand_index}")                
                imgui.text(f"Selected Gaussian Index (Relative to Strand): {g_gaussian_strand_index}")

                changed, g_cutting_mode = imgui.checkbox("Cutting Mode", g_cutting_mode)
                if changed:
                    g_coloring_mode = False
                    g_renderer.update_cutting_mode(g_cutting_mode)
                    g_renderer.update_coloring_mode(g_coloring_mode)              

                changed, g_max_cutting_distance = imgui.slider_float("Cutting Area", g_max_cutting_distance, 0.01, 0.5, "%.2f")
                if changed:
                    g_renderer.update_max_cutting_distance(g_max_cutting_distance)

                if imgui.button(label="Reset Hair Style"):
                    reset_cut()
                    update_means(g_selected_head_avatar_index)
                    g_renderer.update_gaussian_data(gaussians)

                changed, g_coloring_mode = imgui.checkbox("Coloring Mode", g_coloring_mode)
                if changed:
                    g_cutting_mode = False
                    g_renderer.update_cutting_mode(g_cutting_mode)
                    g_renderer.update_coloring_mode(g_coloring_mode)

                imgui.same_line()

                changed, g_keep_sh = imgui.checkbox("Keep Simple Harmonics", g_keep_sh)
                if changed:
                    g_renderer.update_keep_sh(g_keep_sh)

                changed, g_selected_color = imgui.color_edit3("Selected Color", *g_selected_color)
                if changed:
                    g_renderer.update_selected_color(g_selected_color)

                changed, g_max_coloring_distance = imgui.slider_float("Coloring Area", g_max_coloring_distance, 0.01, 0.5, "%.2f")
                if changed:
                    g_renderer.update_max_coloring_distance(g_max_coloring_distance) 

                changed, g_x_plane[g_selected_head_avatar_index] = imgui.slider_float("X-Plane", g_x_plane[g_selected_head_avatar_index], g_x_plane_min[g_selected_head_avatar_index], g_x_plane_max[g_selected_head_avatar_index], "x = %.3f")
                if changed:
                    g_renderer.update_x_plane(g_x_plane[g_selected_head_avatar_index] + get_displacement(g_selected_head_avatar_index))

                imgui.same_line()

                changed, g_invert_x_plane[g_selected_head_avatar_index] = imgui.checkbox("Invert X-Plane", g_invert_x_plane[g_selected_head_avatar_index])
                if changed:
                    g_renderer.update_invert_x_plane(g_invert_x_plane[g_selected_head_avatar_index])

                changed, g_y_plane[g_selected_head_avatar_index] = imgui.slider_float("Y-Plane", g_y_plane[g_selected_head_avatar_index], g_y_plane_min[g_selected_head_avatar_index], g_y_plane_max[g_selected_head_avatar_index], "y = %.3f")
                if changed:
                    g_renderer.update_y_plane(g_y_plane[g_selected_head_avatar_index])

                imgui.same_line()

                changed, g_invert_y_plane[g_selected_head_avatar_index] = imgui.checkbox("Invert Y-Plane", g_invert_y_plane[g_selected_head_avatar_index])
                if changed:
                    g_renderer.update_invert_y_plane(g_invert_y_plane[g_selected_head_avatar_index])                 

                changed, g_z_plane[g_selected_head_avatar_index] = imgui.slider_float("Z-Plane", g_z_plane[g_selected_head_avatar_index], g_z_plane_min[g_selected_head_avatar_index], g_z_plane_max[g_selected_head_avatar_index], "z = %.3f")
                if changed:
                    g_renderer.update_z_plane(g_z_plane[g_selected_head_avatar_index])

                imgui.same_line()

                changed, g_invert_z_plane[g_selected_head_avatar_index] = imgui.checkbox("Invert Z-Plane", g_invert_z_plane[g_selected_head_avatar_index])
                if changed:
                    g_renderer.update_invert_z_plane(g_invert_z_plane[g_selected_head_avatar_index])

                if imgui.button(label="Reset Colors"):
                    reset_coloring()
                    g_renderer.update_gaussian_data(gaussians)

                changed, g_show_hair[i] = imgui.checkbox("Show Hair", g_show_hair[i])
                if changed:
                    update_hair_opacity()
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                changed, g_show_head[i] = imgui.checkbox("Show Head", g_show_head[i])
                if changed:
                    update_head_opacity()
                    g_renderer.update_gaussian_data(gaussians)

                changed, g_hair_color[i] = imgui.color_edit3("Hair Color", *g_hair_color[i])
                if changed:
                    update_hair_color()
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                changed, g_show_hair_color[i] = imgui.checkbox("Show Hair Color", g_show_hair_color[i])
                if changed:
                    update_hair_color()
                    g_renderer.update_gaussian_data(gaussians)

                changed, g_head_color[i] = imgui.color_edit3("Head Color", *g_head_color[i])
                if changed:
                    update_head_color()
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                changed, g_show_head_color[i] = imgui.checkbox("Show Head Color", g_show_head_color[i])
                if changed:
                    update_head_color()
                    g_renderer.update_gaussian_data(gaussians)

                changed, g_hair_scale[i] = imgui.slider_float("Hair Scale", g_hair_scale[i], 0.5, 2, "Hair Scale = %.3f")
                if changed:
                    update_hair_scale()
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                if imgui.button(label="Reset Hair Scale"):
                    g_hair_scale[i] = 1
                    update_hair_scale()
                    g_renderer.update_gaussian_data(gaussians)   

                changed, g_wave_frequency[i] = imgui.slider_float("Wave Frequency", g_wave_frequency[i], 0, 3, "Wave Frequency = %.2f")
                if changed:
                    update_means(g_selected_head_avatar_index)
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                if imgui.button(label="Reset Wave Frequency"):
                    g_wave_frequency[i] = 0
                    update_means(g_selected_head_avatar_index)
                    g_renderer.update_gaussian_data(gaussians) 

                changed, g_wave_amplitude[i] = imgui.slider_float("Wave Amplitude", g_wave_amplitude[i], 0, 0.025, "Wave Amplitude = %.3f")
                if changed:
                    update_means(g_selected_head_avatar_index)
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                if imgui.button(label="Reset Wave Height"):
                    g_wave_amplitude[i] = 0
                    update_means(g_selected_head_avatar_index)
                    g_renderer.update_gaussian_data(gaussians) 

                changed, g_frame[i] = imgui.slider_int("Frame", g_frame[i], 0, 100, "Frame = %d")
                if changed:
                    update_frame()
                    g_renderer.update_gaussian_data(gaussians)

                imgui.same_line()

                if imgui.button(label='Select Frames Folder'):
                    g_frame_folder[g_selected_head_avatar_index] = filedialog.askdirectory(
                        title="Select Folder",
                        initialdir="./models/"
                    )

                if imgui.button(label='Export'):
                    file_path = filedialog.asksaveasfilename(
                        title="Save ply",
                        initialdir=f"./models/",
                        defaultextension=".ply",
                        filetypes=[('ply file', '.ply')]
                    )
                    if file_path:
                        try:
                            export_head_avatar(file_path)
                        except Exception as e:
                            print(f"An error occurred: {e}")

            imgui.end()
        
        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    global args
    parser = argparse.ArgumentParser(description="Dynamic Gaussian Visualizer")
    parser.add_argument("--hidpi", action="store_true", help="Enable HiDPI scaling for the interface.")
    args = parser.parse_args()

    main()
