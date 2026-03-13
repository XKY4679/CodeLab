import shutil
import os
import os.path as op
import re
import subprocess

DIR_1 = u'D:\\2023大刊牛文'

def get_dir_size(path):
    for root, dirs, files in os.walk(path):
        return sum((op.getsize(op.join(root, f)) for f in files))
        

for d in os.listdir(DIR_1):
    full_path = op.join(DIR_1, d)
    if d.startswith('.') or not os.path.isdir(full_path):
        continue
    print(d + '%.2f' % (get_dir_size(full_path) / 1024 / 1024))


OUTPUT_DIR = '/Volumes/PurpleOld/Output'

num_pattern = re.compile(r'(\d{12})')

# walk: https://docs.python.org/3/library/os.html


CMD_I = ["-extra_hw_frames",  '16',  "-y" , '-vsync', '0', '-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', '-i']

CMD_O = ["-c:a",  'aac', '-c:v', 'h264_nvenc' ,  '-profile:v' , 'main', '-vf',  'format=yuv420p']
# '-b:v',  '2500k',

last_num = ''

total_size = 0
for root, dirs, files in os.walk(DIR_1):
    m = re.search(num_pattern, root)
    if m:
        last_num = m.group(1)
    for f in files:
        full_path = op.join(root, f)
        rootext = op.splitext(full_path)
        new_path =rootext[0] + '-s.mp4'
        ext = rootext[-1]

        if not f.startswith('.') and ext in ('.mp4', '.MP4', '.m4v'):
            # print(last_num + '--' + f)
            size = op.getsize(full_path) / 1024 / 1024
            total_size = total_size + size

            cmd = ['ffmpeg'] + CMD_I + [full_path] + CMD_O + [new_path]
            output = subprocess.check_output(cmd, shell=True)
            print(output)
            os.remove(full_path)
            # print('%.2f MB' % (size) ) 

print(total_size)

