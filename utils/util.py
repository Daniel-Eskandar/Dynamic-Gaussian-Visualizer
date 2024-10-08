from OpenGL.GL import *
import OpenGL.GL.shaders as shaders
import numpy as np
import glm
import ctypes
import os
from plyfile import PlyData, PlyElement
import argparse

class Camera:
    def __init__(self, h, w):
        self.znear = 0.01
        self.zfar = 100
        self.h = h
        self.w = w
        self.fovy = np.pi / 5
        self.position = np.array([-0.21758494, 0.7880028, 3.165345]).astype(np.float32)
        self.target = np.array([-0.30512613, 0.5187428, 0.24818137]).astype(np.float32)
        self.up = np.array([0.0, 1.0, 0.0]).astype(np.float32)
        self.yaw = -np.pi / 2
        self.pitch = -0.184
        
        self.is_pose_dirty = True
        self.is_intrin_dirty = True
        
        self.last_x = 640
        self.last_y = 360
        self.first_mouse = True
        
        self.is_leftmouse_pressed = False
        self.is_rightmouse_pressed = False
        
        self.rot_sensitivity = 0.002
        self.trans_sensitivity = 0.01
        self.zoom_sensitivity = 0.3
        self.roll_sensitivity = 0.03
        self.target_dist = 3.
    
    def _global_rot_mat(self):
        x = np.array([1, 0, 0])
        z = np.cross(x, self.up)
        z = z / np.linalg.norm(z)
        x = np.cross(self.up, z)
        return np.stack([x, self.up, z], axis=-1)

    def get_view_matrix(self):
        return np.array(glm.lookAt(self.position, self.target, self.up))

    def get_project_matrix(self):
        # htanx, htany, focal = self.get_htanfovxy_focal()
        # f_n = self.zfar - self.znear
        # proj_mat = np.array([
        #     1 / htanx, 0, 0, 0,
        #     0, 1 / htany, 0, 0,
        #     0, 0, self.zfar / f_n, - 2 * self.zfar * self.znear / f_n,
        #     0, 0, 1, 0
        # ])
        project_mat = glm.perspective(
            self.fovy,
            self.w / self.h,
            self.znear,
            self.zfar
        )
        return np.array(project_mat).astype(np.float32)

    def get_htanfovxy_focal(self):
        htany = np.tan(self.fovy / 2)
        htanx = htany / self.h * self.w
        focal = self.h / (2 * htany)
        return [htanx, htany, focal]

    def get_focal(self):
        return self.h / (2 * np.tan(self.fovy / 2))

    def process_mouse(self, xpos, ypos):
        if self.first_mouse:
            self.last_x = xpos
            self.last_y = ypos
            self.first_mouse = False

        xoffset = xpos - self.last_x
        yoffset = self.last_y - ypos
        self.last_x = xpos
        self.last_y = ypos

        if self.is_leftmouse_pressed:
            self.yaw += xoffset * self.rot_sensitivity
            self.pitch += yoffset * self.rot_sensitivity

            self.pitch = np.clip(self.pitch, -np.pi / 2, np.pi / 2)

            front = np.array([np.cos(self.yaw) * np.cos(self.pitch), 
                            np.sin(self.pitch), np.sin(self.yaw) * 
                            np.cos(self.pitch)])
            front = self._global_rot_mat() @ front.reshape(3, 1)
            front = front[:, 0]
            self.position[:] = - front * np.linalg.norm(self.position - self.target) + self.target
            
            self.is_pose_dirty = True
        
        if self.is_rightmouse_pressed:
            front = self.target - self.position
            front = front / np.linalg.norm(front)
            right = np.cross(self.up, front)
            self.position += right * xoffset * self.trans_sensitivity
            self.target += right * xoffset * self.trans_sensitivity
            cam_up = np.cross(right, front)
            self.position += cam_up * yoffset * self.trans_sensitivity
            self.target += cam_up * yoffset * self.trans_sensitivity
            
            self.is_pose_dirty = True
        
    def process_wheel(self, dx, dy):
        front = self.target - self.position
        front = front / np.linalg.norm(front)
        self.position += front * dy * self.zoom_sensitivity
        self.target += front * dy * self.zoom_sensitivity
        self.is_pose_dirty = True
        
    def process_roll_key(self, d):
        front = self.target - self.position
        right = np.cross(front, self.up)
        new_up = self.up + right * (d * self.roll_sensitivity / np.linalg.norm(right))
        self.up = new_up / np.linalg.norm(new_up)
        self.is_pose_dirty = True

    def flip_ground(self):
        self.up = -self.up
        self.is_pose_dirty = True

    def update_target_distance(self):
        _dir = self.target - self.position
        _dir = _dir / np.linalg.norm(_dir)
        self.target = self.position + _dir * self.target_dist
        
    def update_resolution(self, height, width):
        self.h = max(height, 1)
        self.w = max(width, 1)
        self.is_intrin_dirty = True


def load_shaders(vs, fs):
    vertex_shader = open(vs, 'r').read()        
    fragment_shader = open(fs, 'r').read()

    active_shader = shaders.compileProgram(
        shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
        shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER),
    )
    return active_shader


def compile_shaders(vertex_shader, fragment_shader):
    active_shader = shaders.compileProgram(
        shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
        shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER),
    )
    return active_shader


# called with arguments (self.program, ["position"], [self.quad_v]) where 
# self.quad_v = np.array([-1,  1, 1,  1, 1, -1, -1, -1], dtype=np.float32).reshape(4, 2)
def set_attributes(program, keys, values, vao=None, buffer_ids=None):
    glUseProgram(program)
    # Vertex Array objects stores calls to gl(Dis/En)ableVertexAttribArray
    # with its Vertex attribute configurations via glVertexAttribPointer.
    # Vertex buffer objects associated with vertex attributes by calls to glVertexAttribPointer.
    if vao is None:
        vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    if buffer_ids is None:
        buffer_ids = [None] * len(keys)
    for i, (key, value, b) in enumerate(zip(keys, values, buffer_ids)):
        if b is None:
            # generates a buffer with unique ID b, then saved to buffer_ids
            b = glGenBuffers(1)
            buffer_ids[i] = b
        # binds to the GL_ARRAY_BUFFER type to then load data
        glBindBuffer(GL_ARRAY_BUFFER, b)
        # copies type GL_ARRAY_BUFFER, value.nbytes size of data (quad_v), which is set only once and used many times
        glBufferData(GL_ARRAY_BUFFER, value.nbytes, value.reshape(-1), GL_STATIC_DRAW)
        # gets the atribute location of "position" which is 0 as set in the vertex shader, and the length is 2
        length = value.shape[-1]
        pos = glGetAttribLocation(program, key)
        # how to interpret the data: configuring 0 "position", which are vec3, float elements, 
        # unnormalized, zero stride, with no offset to where the data begins
        glVertexAttribPointer(pos, length, GL_FLOAT, False, 0, None)
        # enable what was before setup again, for the 0 "position" data
        glEnableVertexAttribArray(pos)
    
    # map to first buffer 0 since we have kept track of the buffer ids anyway
    glBindBuffer(GL_ARRAY_BUFFER,0)
    return vao, buffer_ids

def set_attribute_instanced(program, key, value, instance_stride=1, vao=None, buffer_id=None):
    glUseProgram(program)
    if vao is None:
        vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    if buffer_id is None:
        buffer_id = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, buffer_id)
    glBufferData(GL_ARRAY_BUFFER, value.nbytes, value.reshape(-1), GL_STATIC_DRAW)
    length = value.shape[-1]
    pos = glGetAttribLocation(program, key)
    glVertexAttribPointer(pos, length, GL_FLOAT, False, 0, None)
    glEnableVertexAttribArray(pos)
    glVertexAttribDivisor(pos, instance_stride)
    glBindBuffer(GL_ARRAY_BUFFER,0)
    return vao, buffer_id

def set_storage_buffer_data(program, key, value: np.ndarray, bind_idx, vao=None, buffer_id=None):
    glUseProgram(program)
    # if vao is None:  # TODO: if this is really unnecessary?
    #     vao = glGenVertexArrays(1)
    if vao is not None:
        glBindVertexArray(vao)
    
    if buffer_id is None:
        buffer_id = glGenBuffers(1)
    glBindBuffer(GL_SHADER_STORAGE_BUFFER, buffer_id)
    glBufferData(GL_SHADER_STORAGE_BUFFER, value.nbytes, value.reshape(-1), GL_STATIC_DRAW)
    # pos = glGetProgramResourceIndex(program, GL_SHADER_STORAGE_BLOCK, key)  # TODO: ???
    glBindBufferBase(GL_SHADER_STORAGE_BUFFER, bind_idx, buffer_id)
    # glShaderStorageBlockBinding(program, pos, pos)  # TODO: ???
    glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)
    return buffer_id

# called with arguments (vao, self.quad_f) where quad_f = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32).reshape(2, 3)
# Very similar strucuture to set_attributes but already exploiting VAO created in set_attributes
def set_faces_tovao(vao, faces: np.ndarray):
    # faces
    glBindVertexArray(vao)
    element_buffer = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, element_buffer)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL_STATIC_DRAW)
    return element_buffer

def set_gl_bindings(vertices, faces):
    # vertices
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)
    # vertex_buffer = glGenVertexArrays(1)
    vertex_buffer = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 4, GL_FLOAT, False, 0, None)
    glEnableVertexAttribArray(0)

    # faces
    element_buffer = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, element_buffer)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL_STATIC_DRAW)
    # glVertexAttribPointer(1, 3, GL_FLOAT, False, 36, ctypes.c_void_p(12))
    # glEnableVertexAttribArray(1)
    # glVertexAttribPointer(2, 3, GL_FLOAT, False, 36, ctypes.c_void_p(12))
    # glEnableVertexAttribArray(2)

def set_uniform_mat4(shader, content, name):
    glUseProgram(shader)
    if isinstance(content, glm.mat4):
        content = np.array(content).astype(np.float32)
    else:
        content = content.T
    glUniformMatrix4fv(
        glGetUniformLocation(shader, name), 
        1,
        GL_FALSE,
        content.astype(np.float32)
    )

def set_uniform_1f(shader, content, name):
    glUseProgram(shader)
    glUniform1f(
        glGetUniformLocation(shader, name), 
        content,
    )

def set_uniform_1int(shader, content, name):
    glUseProgram(shader)
    glUniform1i(
        glGetUniformLocation(shader, name), 
        content
    )

def set_uniform_v3f(shader, contents, name):
    glUseProgram(shader)
    glUniform3fv(
        glGetUniformLocation(shader, name),
        len(contents),
        contents
    )

def set_uniform_v3(shader, contents, name):
    glUseProgram(shader)
    glUniform3f(
        glGetUniformLocation(shader, name),
        contents[0], contents[1], contents[2]
    )

def set_uniform_v1f(shader, contents, name):
    glUseProgram(shader)
    glUniform1fv(
        glGetUniformLocation(shader, name),
        len(contents),
        contents
    )
    
def set_uniform_v2(shader, contents, name):
    glUseProgram(shader)
    glUniform2f(
        glGetUniformLocation(shader, name),
        contents[0], contents[1]
    )

def set_texture2d(img, texid=None):
    h, w, c = img.shape
    assert img.dtype == np.uint8
    if texid is None:
        texid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texid)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGB, w, h, 0,   
        GL_RGB, GL_UNSIGNED_BYTE, img
    )
    glActiveTexture(GL_TEXTURE0)  # can be removed
    # glGenerateMipmap(GL_TEXTURE_2D)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
    return texid

def update_texture2d(img, texid, offset):
    x1, y1 = offset
    h, w = img.shape[:2]
    glBindTexture(GL_TEXTURE_2D, texid)
    glTexSubImage2D(
        GL_TEXTURE_2D, 0, x1, y1, w, h,
        GL_RGB, GL_UNSIGNED_BYTE, img
    )

# adapted from https://www.khronos.org/opengl/wiki/GluProject_and_gluUnProject_code
def glhUnProjectf(winx, winy, winz, modelview, projection, viewport):
    try:
        A = projection @ modelview
        m = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        return np.array([0, 0, 0])

    # screen coordinates to normalized device coordinates
    in_vec = np.array([
        (winx - viewport[0]) / viewport[2] * 2.0 - 1.0,
        -((winy - viewport[1]) / viewport[3] * 2.0 - 1.0),
        2.0 * winz - 1.0,
        1.0
    ])

    # normalized device coordinates to world coordinates
    out_vec = m @ in_vec

    if out_vec[3] == 0.0:
        return np.array([0, 0, 0])

    out_vec /= out_vec[3]
    return out_vec[:3]

def find_closest_file(target_amp, target_freq, base_directory):
    # Find the closest amplitude directory
    amp_dirs = os.listdir(base_directory)
    amp_values = np.array([float(d) for d in amp_dirs])
    closest_amp_index = np.argmin(np.abs(amp_values - target_amp))
    closest_amp_dir = amp_dirs[closest_amp_index]
    
    # Path to the directory with the closest amplitude
    closest_amp_path = os.path.join(base_directory, closest_amp_dir)
    
    # Find the closest frequency file in the selected amplitude directory
    freq_files = os.listdir(closest_amp_path)
    freq_values = np.array([float(f.replace('.npy', '')) for f in freq_files])
    closest_freq_index = np.argmin(np.abs(freq_values - target_freq))
    closest_freq_file = freq_files[closest_freq_index]
    
    # Construct and return the full path
    full_path = os.path.join(base_directory, closest_amp_dir, closest_freq_file)
    return full_path

# Taken from https://stackoverflow.com/a/5356645
def join_struct_arrays(arrays):
    newdtype = sum((a.dtype.descr for a in arrays), [])
    newrecarray = np.empty(len(arrays[0]), dtype = newdtype)
    for a in arrays:
        for name in a.dtype.names:
            newrecarray[name] = a[name]
    return newrecarray

def main(args):
    # Read the PLY data
    plydata = PlyData.read(args.path)
    vertices = plydata.elements[0].data

    # Check if the attributes already exist
    if "n_strands" not in vertices.dtype.names:
        # Add the attributes
        new_fields = [('n_strands', 'i4'), ('n_gaussians_per_strand', 'i4')]
        vertices = join_struct_arrays([vertices, np.zeros(len(vertices), new_fields)])

    # Update the attributes
    vertices[0]['n_strands'] = args.n_strands
    vertices[0]['n_gaussians_per_strand'] = args.n_gaussians_per_strand
    updated_data = np.array(vertices, dtype=vertices.dtype)
    
    new_element = PlyElement.describe(updated_data, 'vertex')

    # Write the updated plydata to a new file (or overwrite the existing file)
    updated_path = args.path.replace(".ply", "_updated.ply")
    PlyData([new_element]).write(updated_path)

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(conflict_handler='resolve')
    parser.add_argument('path', type=str)
    parser.add_argument('--n_strands', default=12000, type=int)
    parser.add_argument('--n_gaussians_per_strand', default=31, type=int)

    args, _ = parser.parse_known_args()
    args = parser.parse_args()

    main(args)
