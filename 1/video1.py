import sys
import json
from PIL import Image


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
    
    assert(len(blocks) == w // 8 * h // 8)
    return blocks


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
def find_similar_block(image, x, y, block):
    w, h = image.size
    width = 4   # 搜索范围
    similarity = 1000000
    sim_xm, sim_y = x, y
    sim_block = None

    # 获取方圆 width 个像素的方块
    # 比较图块之间的相似度
    for ny in range(y - width, y + width + 1):
        for nx in range(x - width, x + width + 1):
            if 0 <= nx < w - 8 and 0 <= ny < h - 8:
                curr_block = get_block(image.load(), nx, ny, 8)
                sim = SAD(block, curr_block)
                if sim < similarity:
                    similarity = sim
                    sim_x, sim_y = nx, ny
                    sim_block = curr_block
    
    assert(sim_block is not None)
    
    # 获取最相似的图块数据
    blockInfo = {
        'x': sim_x,
        'y': sim_y,
    }
    return blockInfo, sim_block


# 对 img2 进行编码
def encode(img1, img2):

    # 将 img2 划分为 8x8 大小的图块
    blocks = cut_image(img2, 8)

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
        blockInfo, sim_block = find_similar_block(img1, x, y, b)
        blockInfos.append(blockInfo)

        # 计算差值图, diffImg = sim_block - block
        for i in range(len(b)):
            diff_x = x + i % 8
            diff_y = y + i // 8
            diffPixels[diff_x, diff_y] = sim_block[i] - b[i]

    with open('big_buck_bunny_08361.videoblock', 'w+') as f:
        f.write(json.dumps(blockInfos, indent=2))
    diffImg.save('big_buck_bunny_08361.diff.jpg')


# 图片解码
def decode(img, diffImg, blockInfos):
    # 存储解码得到的图片
    decodeImg = Image.new('L', img.size)
    decodePixels = decodeImg.load()

    # 将 diffImg 切成 8x8 大小的图块
    blocks = cut_image(diffImg, 8)
    index = 0
    for c, b in blocks.items():
        x, y = c
        # 对于 diffImg 中的每一图块，利用图块的信息找到 img 中对应的图块
        blockInfo = blockInfos[index]
        index += 1
        sim_block = get_block(img.load(), blockInfo['x'], blockInfo['y'], 8)

        # 图像还原, block = sim_block - diffImg
        for i in range(len(b)):
            decode_x = x + i % 8
            decode_y = y + i // 8
            decodePixels[decode_x, decode_y] = sim_block[i] - b[i]
    
    # 存储还原后的图片
    decodeImg.save('big_buck_bunny_08361.decode.jpg')


def main():
    mode = sys.argv[1]
    if mode == 'encode':
        print('encode')
        path1 = 'big_buck_bunny_08360.png'
        path2 = 'big_buck_bunny_08361.png'
        img1 = grayimage(path1)
        img2 = grayimage(path2)
        encode(img1, img2)
    else:
        print('decode')
        path1 = 'big_buck_bunny_08360.png'
        path2 = 'big_buck_bunny_08361.diff.jpg'
        path3 = 'big_buck_bunny_08361.videoblock'
        img = grayimage(path1)
        diffImg = grayimage(path2)
        with open(path3, 'r') as f:
            blockInfos = json.load(f)
        decode(img, diffImg, blockInfos)


if __name__ == '__main__':
    main()
