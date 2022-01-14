import os
import sys
import json
import sqlite3
from PIL import Image


blocksize = 8   # 切割图块的大小


def db_create(directory):
    # 连接数据库
    # 如果数据库文件不存在，则会创建数据库文件
    conn = sqlite3.connect('video.db')
    cursor = conn.cursor()

    # 创建一个 frames 表
    # 每个数据有 3 个字段
    #   id: number
    #   name: string
    #   image: 文件的二进制数据
    sql = 'create table if not exists frames(id integer, name text, image blob)'
    cursor.execute(sql)
    sql = 'delete from frames'
    cursor.execute(sql)
    conn.commit()

    # 把图片文件读取为二进制数据
    # 并向 frames 表，插入下面格式的数据
    # {id: 1, name: 'bbb0.png', image: 图片文件的二进制数据}
    images = os.listdir(directory)
    for id, name in enumerate(images):
        with open(directory + '/' + name, 'rb') as f:
            image = f.read()

        sql = 'insert into frames (id, name, image) values (?, ?, ?)'
        cursor.execute(sql, (id, name, image))

    conn.commit()

    # 关闭连接
    conn.close()


def encode_img_seq():
    # 连接数据库文件
    conn = sqlite3.connect('video.db')
    cursor = conn.cursor()

    # 从 frames 表拿出所有数据
    sql = 'select * from frames'
    rows = cursor.execute(sql)
    conn.commit()

    for row in rows:
        # 取出来的每个数据，是一个数组

        # 数组第 0 个对应 id
        # 数组第 1 个对应 name
        # 数组第 2 个对应 文件二进制数据
        id = row[0]
        name = row[1]
        image = row[2]

        # 打印出来
        print('id: {}  name: {}'.format(id, name))
        # 把文件写出去
        file_name, file_format = name.split('.', 1)
        path = file_name + '.' + file_format # TODO: fixme
        with open(path, 'wb') as f:
            f.write(image)

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


# 对 img2 进行编码
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

    with open('big_buck_bunny_08361.videoblock', 'w+') as f:
        f.write(json.dumps(blockInfos, indent=2))
    diffImg.save('big_buck_bunny_08361.diff.jpg')


# 图片解码
def decode(img, diffImg, blockInfos):
    # 存储解码得到的图片
    decodeImg = Image.new('L', img.size)
    decodePixels = decodeImg.load()

    # 将 diffImg 切成 8x8 大小的图块
    diff_blocks = cut_image(diffImg, blocksize)
    index = 0
    for c, diff_b in diff_blocks.items():
        x, y = c
        # 对于 diffImg 中的每一图块，利用图块的信息找到 img 中对应的图块
        blockInfo = blockInfos[index]
        index += 1

        if blockInfo['x'] == -1:
            # 没有对应的图块, 说明 diffImg 中直接存储了原图的数据
            # 直接把数据拷贝过来即可
            save_image(decodePixels, x, y, diff_b)
        else:
            # 有对应的图块, 则切出对应位置的方块, 并将数据拷贝过来
            sim_block = get_block(img.load(), blockInfo['x'], blockInfo['y'], blocksize)
            save_image(decodePixels, x, y, sim_block)
    
    decodeImg.save('big_buck_bunny_08361.decode.jpg')


def main():
    mode = sys.argv[1]
    dir = sys.argv[2]
    video_name = sys.argv[3]
    
    db_create(dir)
    encode_img_seq()


if __name__ == '__main__':
    main()
