#导入必要的库
import os
from mutagen.id3 import ID3, USLT, ID3NoHeaderError
from mutagen.mp3 import MP3

# 定义文件路径
mp3_path = r'D:\你一定能看见.mp3'
lrc_path = r'D:\你一定能看见歌词.lrc'
new_mp3_path = r'D:\你一定能看见歌词版.mp3'

# 读取歌词文件
def read_lrc(lrc_file):
    with open(lrc_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    lyrics = ''.join(lines)
    return lyrics

# 嵌入歌词到MP3
def embed_lyrics(mp3_file, lyrics, output_file):
    try:
        tags = ID3(mp3_file)
    except ID3NoHeaderError:
        tags = ID3()

    # 创建 USLT 帧
    uslt_frame = USLT(
        encoding=3,  # 3 表示 UTF-8
        lang='eng',  # 语言代码，可以根据需要更改
        desc='Lyrics',  # 描述
        text=lyrics
    )

    # 添加或更新 USLT 帧
    tags.add(uslt_frame)

    # 保存到新的MP3文件
    # 首先复制原始MP3文件到新的文件
    with open(mp3_file, 'rb') as src, open(output_file, 'wb') as dst:
        dst.write(src.read())

    # 将标签保存到新的MP3文件
    tags.save(output_file, v2_version=3)
    print(f"歌词已成功嵌入到 {output_file}")

def main():
    # 检查文件是否存在
    if not os.path.isfile(mp3_path):
        print(f"MP3文件未找到: {mp3_path}")
        return
    if not os.path.isfile(lrc_path):
        print(f"LRC文件未找到: {lrc_path}")
        return

    # 读取歌词
    lyrics = read_lrc(lrc_path)
    # 如果希望移除时间戳，可以使用以下代码
    # import re
    # lyrics = re.sub(r'\[\d{2}:\d{2}.\d{2}\]', '', lyrics)

    # 嵌入歌词
    embed_lyrics(mp3_path, lyrics, new_mp3_path)

if __name__ == "__main__":
    main()
