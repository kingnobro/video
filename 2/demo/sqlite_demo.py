# 这个 demo 演示了
# 怎么把文件存到数据库里


import sqlite3
import os


def db_create():
    # 连接数据库
    # 如果数据库文件不存在，则会创建数据库文件
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 创建一个 frames 表
    # 每个数据有 3 个字段
    #   id: number
    #   name: string
    #   image: 文件的二进制数据
    sql = 'create table frames(id integer, name text, image blob)'
    cursor.execute(sql)
    conn.commit()


    # 把图片文件读取为二进制数据
    id = 0
    name = 'bbb0.png'
    with open(name, 'rb') as f:
        image = f.read()

    # 向 frames 表，插入下面这个数据
    # {id: 1, name: 'bbb0.png', image: 图片文件的二进制数据}
    sql = 'insert into frames (id, name, image) values (?, ?, ?)'
    cursor.execute(sql, (id, name, image))
    conn.commit()


    # 把图片文件读取为二进制数据
    id = 1
    name = 'bbb1.png'
    with open(name, 'rb') as f:
        image = f.read()

    # 向 frames 表，插入下面这个数据
    # {id: 2, name: 'bbb1.png', image: 图片文件的二进制数据}
    sql = 'insert into frames (id, name, image) values (?, ?, ?)'
    cursor.execute(sql, (id, name, image))
    conn.commit()

    # 关闭连接
    conn.close()


def db_query():
    # 连接数据库文件
    conn = sqlite3.connect('test.db')
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
        print('id', id)
        print('name', name)
        # 把文件写出去
        path = '读取例子' + name
        with open(path, 'wb') as f:
            f.write(image)

    # 关闭连接
    conn.close()


def main():
    # 删除数据库文件
    # 这是为了让这个 demo 每次都重新创建数据库文件
    os.system('mv test.db /tmp')

    db_create()
    db_query()


if __name__ == '__main__':
    main()
