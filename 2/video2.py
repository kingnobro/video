# python3 video2.py

import os
import sys
import json
import sqlite3
from PIL import Image


blocksize = 8   # 切割图块的大小


# 从 tmp/ 目录下读取 videoblock 和 diff.jpg
# 并将二进制格式存入数据库
def video_db(dir):
    # 连接数据库
    # 如果数据库文件不存在，则会创建数据库文件
    conn = sqlite3.connect('video.db')
    cursor = conn.cursor()

    # 创建一个 frames 表
    # 每个数据有 4 个字段
    #   id: number
    #   name: string
    #   videoblock: 文件的二进制数据
    #   diff: 文件的二进制数据
    sql = 'create table if not exists frames(id integer, name text, videoblock blob, diff blob)'
    cursor.execute(sql)
    # 清空数据库
    sql = 'delete from frames'
    cursor.execute(sql)
    conn.commit()

    # 把 videoblock 和 差值图 读取为二进制数据
    # 并向 frames 表，插入下面格式的数据
    # {id: 1, name: 'bbb0.png', videoblock: 二进制数据, diff: 二进制数据}
    # 这个数据库就表示压缩后的视频
    videoblocks = sorted(v for v in os.listdir(dir) if v.endswith('videoblock'))
    diffs = sorted(d for d in os.listdir(dir) if d.endswith('diff.jpg'))

    for id, pair in enumerate(zip(videoblocks, diffs)):
        vb_path = dir + pair[0]
        diff_path = dir + pair[1]
        with open(vb_path, 'rb') as f:
            vb = f.read()
        with open(diff_path, 'rb') as f:
            diff = f.read()
        name = pair[0].split('.', 1)[0]

        sql = 'insert into frames (id, name, videoblock, diff) values (?, ?, ?, ?)'
        cursor.execute(sql, (id, name, vb, diff))

    conn.commit()

    # 关闭连接
    conn.close()


def grayimage(path):
    # convert('L') 转为灰度图
    # 这样每个像素点就只有一个灰度数据
    img = Image.open(path).convert('L')
    return img


# 以 [x, y] 为左上角, 切割出长和宽为 width 的方块
def get_block(pixels, x, y, width):
    block = []
    for dy in range(width):
        for dx in range(width):
            block.append(pixels[x + dx, y + dy])
    return block


# 将 image 划分为 width x width 的图块
# 返回数据的格式为 {(x1, y1): block, (x2, y2): block, ...}
def cut_image(image, width):
    w, h = image.size
    pixels = image.load()
    blocks = {}
    for y in range(0, h, width):
        for x in range(0, w, width):
            blocks[(x, y)] = get_block(pixels, x, y, width)
    
    assert(len(blocks) == w // blocksize * h // blocksize)
    return blocks


# 把图块 block 存储到 pixels[x, y] 处
def save_image(pixels, x, y, block):
    for i in range(len(block)):
        pixels[x + i % blocksize, y + i // blocksize] = block[i]


# 图块相似度比较算法
# 求出 [图块中 [每个像素的差的绝对值] 的和]
def SAD(block1, block2):
    assert(len(block1) == len(block2))

    similarity = 0
    for i in range(len(block1)):
        diff = abs(block1[i] - block2[i])
        similarity += diff
    return similarity


# 在 image 中查找与 block 最相似的图块
def find_similar_block(image, x, y, block, radius, threshold):
    w, h = image.size
    # 存储最相似的图块数据
    blockInfo = {
        'x': -1,
        'y': -1,
    }

    r = radius
    # 获取方圆 radius 个像素的方块
    # 比较图块之间的相似度
    for ny in range(y - r, y + r + 1):
        for nx in range(x - r, x + r + 1):
            if 0 <= nx < w - blocksize and 0 <= ny < h - blocksize:
                curr_block = get_block(image.load(), nx, ny, blocksize)
                if SAD(block, curr_block) < threshold:
                    blockInfo['x'] = nx
                    blockInfo['y'] = ny
    
    return blockInfo


# 以 img1 为关键帧, 对 img2 进行编码
def encode(img1, img2):

    # 将 img2 划分为 8x8 大小的图块
    blocks = cut_image(img2, blocksize)

    # blockInfos 用于存储图像 b 的图块信息
    # 数组中的每个元素是一个如下的字典, 表示一个图块的信息
    # {
    #   'x': 图块在 a 中的坐标 x，如果为 -1 说明没找到合适的相似图块
    #   'y': 图块在 a 中的坐标 y，如果为 -1 说明没找到合适的相似图块
    # }
    blockInfos = []
    
    # 差值图
    diffImg = Image.new('L', img1.size)
    diffPixels = diffImg.load()
    
    # 对于每一个图块, 在 img1 中查找最相似的图块的坐标
    for c, b in blocks.items():
        x, y = c
        # 方圆搜索
        blockInfo = find_similar_block(img1, x, y, b, radius=4, threshold=90)
        blockInfos.append(blockInfo)

        # 如果没有找到相似的图块, 则直接把 b 这个图块存下来
        if blockInfo['x'] == -1:
            save_image(diffPixels, x, y, b)

    return blockInfos, diffImg


# 对一组图片进行编码
# 以第一张图为关键帧, 计算并保存后续每一张图片的 videoblock 和 差值图
# 结果存在 tmpdir 目录下
def video_encode(dir, tmpdir):
    images = sorted(os.listdir(dir))
    keyframe_path = dir + images[0]
    keyframe = grayimage(keyframe_path)

    for i in range(1, len(images)):
        print('encoding image {}'.format(i))

        path = dir + images[i]
        img = grayimage(path)
        blockInfos, diffImg = encode(keyframe, img)

        # 编码结果写入文件
        prefix = images[i].split('.', 1)[0]
        name1 = tmpdir + prefix + '.videoblock'
        name2 = tmpdir + prefix + '.diff.jpg'
        with open(name1, 'w+') as f:
            f.write(json.dumps(blockInfos, indent=2))
        diffImg.save(name2)


def main():
    dir = 'images/'
    tmpdir = 'tmp/'

    video_encode(dir, tmpdir)
    video_db(tmpdir)


if __name__ == '__main__':
    main()
