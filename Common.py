import os
import json
import configparser


def execute_file(path_file, mode=0, data_object=None, code="utf-8"):
    """ 接收参数: <str>文件路径, <int>运行模式, <object>数据对象, <str>文件编码类型.
        实现功能: mode 0 读取文件路径的对象, 并以JSON数据形式返回. 
                  mode 1 将数据对象写入到文件路径中. """
    if mode == 0:
        with open(path_file, "r+", encoding=code) as f_Object:
            return json.load(f_Object)
    elif mode == 1:
        with open(path_file, "w+", encoding=code) as f_Object:
            f_Object.write(data_object)
    else:
        print("ERROR [Common.execute_file]--> Invalid mode value.")

def execute_directory_create(LIST_PATH):
    """ 接收参数: <list>路径列表. 
        实现功能: 传入一个文件路径列表, 判断列表中的文件目录是否存在, 如不存在将创建该目录. """
    for file_path in LIST_PATH:
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

def execute_config_read(section, key, path="./config.ini"):
    """ 接收参数: <str>配置文件的节名(section), <str>配置文件的键名(key), <str>配置文件的路径.
        实现功能: 选择指定路径的配置文件, 根据节名和键名获取键值, 并返回. """
    config = configparser.ConfigParser()
    config.read(path, encoding="utf-8-sig")
    return config[str(section)][str(key)]

def execute_config_write(section, key, value, path="./config.ini"):
    """ 接收参数: <str>配置文件的节名(section), <str>配置文件的键名(key), <str>要写入的键值(value), <str>配置文件的路径.
        实现功能: 选择指定路径的配置文件, 将值写入到配置文件的节名和键名所对应的键值中. """
    config = configparser.ConfigParser()
    config.read(path, encoding="utf-8-sig")
    config.set(str(section), str(key), str(value))
    with open(path, 'w+', encoding='utf-8') as f_Obj:
        config.write(f_Obj)

def execute_config_create(path="./config.ini"):
    """ 接收参数: <str>配置文件的路径.
        实现功能: 将默认配置写入到指定的路径中. """
    config = configparser.ConfigParser()    #实例化一个对象
    config["Encode"] = {
        "encode_mode": "0",
        "encode_path_input": "./_workspace/File_to_Video_input/",
        "encode_path_output": "./_workspace/File_to_Video_output/",
        "encode_frame_size_width": "1280",
        "encode_frame_size_height": "720",
        "encode_frame_size_cut": "4",
        "encode_frame_speed_fps": "24",
        "encode_frame_cover_number": "2",
        "fm_encoder_type": "libx264",
        "fm_rate": "40000k",
    }
    config["Decode"] = {
        "decode_mode": "0",
        "decode_path_input": "./_workspace/Video_to_File_input/demo.mp4",
        "decode_path_output": "./_workspace/Video_to_File_output/",
        "decode_frame_size_cut": "4",
        "decode_process_num": "4",
        "decode_frame_start": "3",
    }

    with open(path, 'w') as f_Obj:
        config.write(f_Obj)

def build_structure_object(path_input):
    """ 接收参数: <str>路径, 
        实现功能: 遍历路径, 构建文件对象的结构, 并以字典形式返回. """
    files_structure = {"F": {}, "D": {}}        # 存储文件和目录信息的字典
    for entry in os.scandir(path_input):        # 遍历路径下的目录
        if entry.is_file():
            files_structure["F"][entry.name] = {"S": entry.stat().st_size}          # 添加文件信息
        elif entry.is_dir():
            files_structure['D'][entry.name] = build_structure_object(entry.path)   # 递归调用以获取子目录的内容
    return files_structure

def build_structure_object_from_list(LIST_PATH_INPUT):
    """ 接收参数: <list>路径列表.
        实现功能: 根据路径列表, 遍历列表中的路径, 构建文件对象的结构, 并以字典形式返回. """
    final_structure = {"F": {}, "D": {}}
    for path_current in LIST_PATH_INPUT:
        if os.path.isdir(path_current):
            dir_name = os.path.basename(path_current)
            final_structure["D"][dir_name] = build_structure_object(path_current)
        elif os.path.isfile(path_current):
            file_name = os.path.basename(path_current)
            file_size = os.stat(path_current).st_size
            final_structure["F"][file_name] = {"S": file_size}
    return final_structure

def build_structure_path(path_input):
    """ 接收参数: <str>路径, 
        实现功能: 遍历路径, 构建文件路径的结构, 并以字典形式返回. """
    files_structure = {"F": {}, "D": {}}        # 存储文件和目录信息的字典
    for entry in os.scandir(path_input):        # 遍历路径下的目录
        if entry.is_file():
            files_structure["F"][entry.path] = {"S": entry.stat().st_size}          # 添加文件路径和信息
        elif entry.is_dir():
            files_structure['D'][entry.name] = build_structure_path(entry.path)     # 递归调用以获取子目录的内容
    return files_structure

def build_structure_path_from_list(LIST_PATH_INPUT):
    """ 接收参数: <list>路径列表.
        实现功能: 根据路径列表, 遍历列表中的路径, 构建文件路径的结构, 并以字典形式返回. """
    final_structure = {"F": {}, "D": {}}
    for path_current in LIST_PATH_INPUT:
        if os.path.isdir(path_current):
            dir_name = os.path.basename(path_current)
            final_structure["D"][dir_name] = build_structure_path(path_current)
        elif os.path.isfile(path_current):
            file_size = os.stat(path_current).st_size
            final_structure["F"][path_current] = {"S": file_size}  # 添加文件路径和信息
    return final_structure

def build_info_from_structure_path(structure, LIST_PATH, LIST_SIZE):
    """ 接收参数: <dict>文件结构字典, <list>空路径列表, <list>空尺寸列表.
        实现功能: 递归遍历文件路径结构字典, 将所有文件路径和尺寸分别添加到 LIST_PATH 和 LIST_SIZE 列表中. """
    for file_path, file_info in structure.get("F", {}).items():
        LIST_PATH.append(file_path)
        LIST_SIZE.append(file_info["S"])
    for dir_name, dir_structure in structure.get("D", {}).items():
        build_info_from_structure_path(dir_structure, LIST_PATH, LIST_SIZE)

def build_info_from_structure_object(base_path, structure):
    """ 接收参数: <str>基本路径, <dict>文件结构字典.
        实现功能: 递归遍历文件对象结构字典, 使用基本路径构建为完整路径, 并将完整路径和尺寸信息分别添加到列表中返回 """
    LIST_PATH = list()
    LIST_SIZE = list()
    def traverse(current_path, current_structure):
        for key, value in current_structure.items():
            if key == 'F':
                for file_name, file_info in value.items():
                    LIST_PATH.append(f"{current_path}/{file_name}")
                    LIST_SIZE.append(file_info['S'])
            elif key == 'D':
                for dir_name, dir_structure in value.items():
                    traverse(f"{current_path}/{dir_name}", dir_structure)
    traverse(base_path, structure)
    return LIST_PATH, LIST_SIZE

def build_info_from_list(LIST_PATH_INPUT):
    """ 接收参数: <list>路径列表.
        实现功能: 根据路径列表, 遍历列表中的所有文件, 并将文件路径和文件尺寸, 分别添加到两个列表中。文件信息(路径和尺寸)在这两个列表中的索引是相同的。 """
    LIST_PATH = list()
    LIST_SIZE = list()
    # 遍历初始列表中的每个路径
    for current_path in LIST_PATH_INPUT:
        # 如果是文件，直接获取文件大小
        if os.path.isfile(current_path):
            LIST_PATH.append(current_path)
            LIST_SIZE.append(os.path.getsize(current_path))
        # 如果是文件夹，递归遍历文件夹中的所有文件
        elif os.path.isdir(current_path):
            for root, dirs, files in os.walk(current_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    LIST_PATH.append(file_path)
                    LIST_SIZE.append(os.path.getsize(file_path))
    return LIST_PATH, LIST_SIZE

def check_exists_path(path_input):
    """ 接收参数: <str>路径, 
        实现功能: 判断路径(文件对象或者文件夹)是否存在, 存在返回True, 否则为False """
    return os.path.exists(path_input)

def compute_integer_split(m, n):
    """ 接收参数: <int>总数, <int>份数. 
        实现功能: 输入总数和份数, 将总数相对的平分为指定份数, 并以列表的形式返回. """
    # 计算每一份的基本值(quotient), 再根据余数(remainder)调整部分份额, 使得总和仍然等于原始数值1。 
    quotient, remainder = divmod(m, n)
    return [quotient + 1] * remainder + [quotient] * (n - remainder)

def sys_clear_directory(path_directory):
    """ 接收参数: <str>路径. 
    实现功能: 输入一个目录的路径, 将该目录下的所有文件清除. """
    try:
        for filename in os.listdir(path_directory):
            file_path = os.path.join(path_directory, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        print(f"INFO: The [{path_directory}] directory has been cleared.")
    except FileNotFoundError:
        print(f"ERROR: Unable to clear directory [{path_directory}]")


# ----------------------------------------------------------------

# def get_directory_path(path_input):
#     """ 传入一个路径对象, 如果是目录就直接返回, 如果是文件就返回文件所在目录 """
#     if os.path.isdir(path_input):
#         return path_input
#     elif os.path.isfile(path_input):
#         return os.path.dirname(path_input) + "/"
#     else:
#         raise ValueError("The provided path is neither a file nor a directory")

# def create_json_structure(path_input):
#     """ 接收输入的路径, 判断该路径是目录还是文件, 如果是目录就返回目录的结构和True标识, 反之直接返回单个文件的结构和False标识 """
#     if os.path.isdir(path_input):               # 如果是目录, 那就 以字典形式返回目录下的结构
#         structure = build_structure_object(path_input)
#         return structure, True
#     elif os.path.isfile(path_input):            # 如果是文件, 那就 构建文件的信息, 并返回
#         f_name = os.path.basename(path_input)
#         f_size = os.stat(path_input).st_size
#         structure = {"files": {f_name: {"size": f_size}}}
#         return structure, False
#     else:
#         raise ValueError("The provided path is neither a file nor a directory")
