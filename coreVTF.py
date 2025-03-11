import sys
import cv2
import time 
import numpy as np
import Common
from multiprocessing import Process, shared_memory
from numpy import memmap, packbits, zeros, uint8


def pack(shm_name, path_output, size_json, bit_total, isMemmap):
    file_structure_path_raw = Common.execute_file("./temp/structure_read.json", 0)     # 读取JSON 文ゲン, 返回一个ス典
    LIST_PATH, LIST_SIZE = Common.build_info_from_structure_object(path_output, file_structure_path_raw)
    Common.execute_directory_create(LIST_PATH)      # 创建目录ゲ构

    if isMemmap:
        DATA_RAW_ARRAY = memmap("./temp/MEMMAP_DECODE_DATA_RAW.dat", dtype=uint8, mode="r", shape=(bit_total,))
        memmap("./temp/MEMMAP_DECODE_DATA_RESULT.dat", dtype=uint8, mode='w+', shape=(int(bit_total / 8),))     # 创建ヌイ存ヤン射对象
        with open("./temp/MEMMAP_DECODE_DATA_RESULT.dat", "r+b") as f_Obj:
            DATA_RESULT_ARRAY = memmap(f_Obj, dtype=uint8, mode='r+', shape=(int(bit_total / 8),))
            DATA_RESULT_ARRAY = packbits(DATA_RAW_ARRAY)
            DATA_RAW_ARRAY = None
    else:
        SHM_OBJECT = shared_memory.SharedMemory(name=shm_name)                          # 连接ド共用ヌイ存块
        DATA_RAW_ARRAY = np.ndarray((bit_total,), dtype=uint8, buffer=SHM_OBJECT.buf)   # 创建一个 NumPy ス组，用共用ヌイ存　作成缓冲キ
        DATA_RESULT_ARRAY = packbits(DATA_RAW_ARRAY)
        DATA_RAW_ARRAY = None
        SHM_OBJECT.close()
        SHM_OBJECT.unlink()

    position_start = size_json + 32                          # 截取开チ位置，偏移量+32 (スゼ)
    position_end = int()
    for f_path, f_size in zip(LIST_PATH, LIST_SIZE):
        position_end = position_start + f_size
        DATA_RESULT_ARRAY[position_start:position_end].tofile(f_path)
        position_start = position_end

# Decode BinaryColor V3.4 core
def decode_BinaryColor(shm_name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap):
    capture = cv2.VideoCapture(path_input)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)
    frame_raw_bit_number = int(frame_raw_size_width * frame_raw_size_height)     # 每帧　コーイ存储ゴbitス量
    frame_start -= frame_cover_number
    frame_end -= frame_cover_number

    if isMemmap:
        with open("./temp/MEMMAP_DECODE_DATA_RAW.dat", "r+b") as f_Obj:
            DATA_RAW_ARRAY = memmap(f_Obj, dtype=uint8, mode='r+', shape=(bit_total,))
            for frame_index in range(frame_start, frame_end):
                ret, frame = capture.read()
                data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3, 4)) # uint8 --> float64
                DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = (data_frame_average > 127).flatten().astype(uint8) # bool--> bool--> uint8
                with shared_decode_run_count.get_lock():
                    shared_decode_run_count.value += 1
            capture.release()
    else:
        SHM_OBJECT = shared_memory.SharedMemory(name=shm_name)                          # 连接ド共用ヌイ存块
        DATA_RAW_ARRAY = np.ndarray((bit_total,), dtype=uint8, buffer=SHM_OBJECT.buf)   # 创建一个 NumPy ス组，用共用ヌイ存作成缓冲キ
        for frame_index in range(frame_start, frame_end):
            ret, frame = capture.read()
            data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3, 4)) # uint8 --> float64
            DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = (data_frame_average > 127).flatten().astype(uint8) # bool--> bool--> uint8
            with shared_decode_run_count.get_lock():
                shared_decode_run_count.value += 1
        capture.release()
        SHM_OBJECT.close()      # ガン闭共用ヌイ存块

# Decode RGB3bit V3.4 core
def decode_RGB3bit(shm_name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap):
    capture = cv2.VideoCapture(path_input)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)
    frame_raw_bit_number = int(frame_raw_size_width * frame_raw_size_height * 3)     # 每帧　コーイ存储ゴbitス量
    frame_start -= frame_cover_number
    frame_end -= frame_cover_number

    if isMemmap:
        with open("./temp/MEMMAP_DECODE_DATA_RAW.dat", "r+b") as f_Obj:
            DATA_RAW_ARRAY = memmap(f_Obj, dtype=uint8, mode='r+', shape=(bit_total,))
            for frame_index in range(frame_start, frame_end):
                ret, frame = capture.read()
                data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3))    # uint8 --> float64
                DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = (data_frame_average > 127).flatten().astype(uint8) # bool--> bool--> uint8
                with shared_decode_run_count.get_lock():
                    shared_decode_run_count.value += 1
            capture.release()
    else:
        SHM_OBJECT = shared_memory.SharedMemory(name=shm_name)                          # 连接ド共用ヌイ存块
        DATA_RAW_ARRAY = np.ndarray((bit_total,), dtype=uint8, buffer=SHM_OBJECT.buf)   # 创建一个 NumPy ス组，用共用ヌイ存作成缓冲キ
        for frame_index in range(frame_start, frame_end):
            ret, frame = capture.read()
            data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3)) # uint8 --> float64
            DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = (data_frame_average > 127).flatten().astype(uint8) # bool--> bool--> uint8
            with shared_decode_run_count.get_lock():
                shared_decode_run_count.value += 1
        capture.release()
        SHM_OBJECT.close()      # ガン闭共用ヌイ存块

# Decode RGB6bit V3.4 core
def decode_RGB6bit(shm_name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap):
    capture = cv2.VideoCapture(path_input)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)
    frame_raw_bit_number = int(frame_raw_size_width * frame_raw_size_height * 6)    # 每帧　コーイ存储ゴbitス量
    frame_start -= frame_cover_number
    frame_end -= frame_cover_number

    if isMemmap:
        with open("./temp/MEMMAP_DECODE_DATA_RAW.dat", "r+b") as f_Obj:
            DATA_RAW_ARRAY = memmap(f_Obj, dtype=uint8, mode='r+', shape=(bit_total,))
            for frame_index in range(frame_start, frame_end):
                ret, frame = capture.read()
                data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3))    # uint8 --> float64
                data_result = zeros((frame_raw_size_height, frame_raw_size_width, 3, 2), dtype=uint8)   # uint8
                mask_0_85 = (data_frame_average <= 85)  # bool
                data_result[mask_0_85] = [0, 0]
                data_result[mask_0_85 & (data_frame_average > 42)] = [0, 1]
                mask_85_170 = (data_frame_average > 85) & (data_frame_average <= 170)
                data_result[mask_85_170] = [0, 1]
                data_result[mask_85_170 & (data_frame_average > 127)] = [1, 0]
                mask_170_255 = (data_frame_average > 170)
                data_result[mask_170_255] = [1, 0]
                data_result[mask_170_255 & (data_frame_average > 212)] = [1, 1]
                DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = data_result.reshape(-1)
                with shared_decode_run_count.get_lock():
                    shared_decode_run_count.value += 1
            capture.release()
    else:
        SHM_OBJECT = shared_memory.SharedMemory(name=shm_name)                          # 连接ド共用ヌイ存块
        DATA_RAW_ARRAY = np.ndarray((bit_total,), dtype=uint8, buffer=SHM_OBJECT.buf)   # 创建一个 NumPy ス组，用共用ヌイ存作成缓冲キ
        for frame_index in range(frame_start, frame_end):
            ret, frame = capture.read()
            data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3))    # uint8 --> float64
            data_result = zeros((frame_raw_size_height, frame_raw_size_width, 3, 2), dtype=uint8)   # uint8
            mask_0_85 = (data_frame_average <= 85)  # bool
            data_result[mask_0_85] = [0, 0]
            data_result[mask_0_85 & (data_frame_average > 42)] = [0, 1]
            mask_85_170 = (data_frame_average > 85) & (data_frame_average <= 170)
            data_result[mask_85_170] = [0, 1]
            data_result[mask_85_170 & (data_frame_average > 127)] = [1, 0]
            mask_170_255 = (data_frame_average > 170)
            data_result[mask_170_255] = [1, 0]
            data_result[mask_170_255 & (data_frame_average > 212)] = [1, 1]
            DATA_RAW_ARRAY[frame_index * frame_raw_bit_number : (frame_index + 1) * frame_raw_bit_number] = data_result.reshape(-1)
            with shared_decode_run_count.get_lock():
                shared_decode_run_count.value += 1
        capture.release()
        SHM_OBJECT.close()      # ガン闭共用ヌイ存块    

def run(path_input, path_output, mode, frame_size_cut, frame_start , process_num, size_json, shared_decode_run_count, shared_decode_run_active):
    capture = cv2.VideoCapture(path_input)
    frame_raw_size_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) / frame_size_cut)
    frame_raw_size_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) / frame_size_cut)
    frame_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) - frame_start                  # ユ用总帧ス = 视频总帧ス - cover封面ゴ帧ス量,   (起始帧 正ホ　等イ　封面ゴ帧ス量)
    list_frame_num_split = Common.compute_integer_split(frame_total, process_num)           # ビ如输入(35, 8) 得ド[5, 5, 5, 4, 4, 4, 4, 4]

    if mode == 0:
        bit_total = int(frame_total * frame_raw_size_width * frame_raw_size_height)
    elif mode == 1:
        bit_total = int(frame_total * frame_raw_size_width * frame_raw_size_height * 3)
    elif mode == 2:
        bit_total = int(frame_total * frame_raw_size_width * frame_raw_size_height * 6)
    else:
        print("Unexpected ERROR: [coreFTV]---> mode, Beyond the selection range. ")

    isMemmap = False
    try:
        # 创建共用ヌイ存块
        SHM = shared_memory.SharedMemory(create=True, size=bit_total)
        print("INFO: Using RAM memory to store temporary data.")

    except (np.core._exceptions._ArrayMemoryError, OSError, MemoryError) as e:
        # イヘ内存モ够、　ジユ用 内存映サ ゴ 方シ、　バ　帧读取ゴ bit スーギ ボ存ド　チ盘　ソンーゴ
        try:
            memmap("./temp/MEMMAP_DECODE_DATA_RAW.dat", dtype=uint8, mode='w+', shape=(bit_total,))  # 创建内存ヤン射对象
            isMemmap = True
            SHM = shared_memory.SharedMemory(create=True, size=10)
            print("WARNING: [coreFTV]--> Out of memory, try using disk space to store temporary data.")
        except OSError:
            shared_decode_run_active.value = False
            print("ERROR: [coreFTV]--> Unable to execute memory mapping. ")
            print("ERROR: 1. The file is too large. 2. there is not enough disk space. 3. directory permissions are denied for read and write.")
            sys.exit("ERROR: System IO error. Program exiting...")
    
    except ValueError:
        shared_decode_run_active.value = False
        print("ERROR: [coreFTV]--> Maximum allowed dimension exceeded. ")
        print("ERROR: 1. The maximum value range of the numpy array is exceeded. 2. Invalid value.")
        sys.exit("ERROR: numpy Value error. Program exiting...")
    # else:
    #     print("Unexpected Error: [coreVTF--> run] function has unexpected unknown error.")
    #     sys.exit()

    # frame_start = 0
    frame_end = int()
    frame_cover_number = frame_start        # cover封面　ゴ帧ス　正ホ等イ　帧开チゴ ベンーホ
    PROCESS_CREATE = list()

    for x in range(process_num):
        frame_end = frame_start + list_frame_num_split[x]
        if mode == 0:
            process_object = Process(target=decode_BinaryColor, \
                                     args=(SHM.name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap))
            
            PROCESS_CREATE.append(process_object)
        elif mode == 1:
            process_object = Process(target=decode_RGB3bit, \
                                     args=(SHM.name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap))
            PROCESS_CREATE.append(process_object)
        elif mode == 2:
            process_object = Process(target=decode_RGB6bit, \
                                     args=(SHM.name, path_input, frame_start, frame_end, frame_cover_number, frame_raw_size_width, frame_raw_size_height, frame_size_cut, bit_total, shared_decode_run_count, isMemmap))
            PROCESS_CREATE.append(process_object)
        else:
            print("Unexpected Error: [coreFTV--> run] function has value error. mode, Beyond the selection range. ")
            sys.exit()

        # process_object.daemon = True
        process_object.start()
        frame_start = frame_end

    # for process_object in PROCESS_CREATE:
    #     process_object.join()

    while True:
        dead_state = 0
        for process_object in PROCESS_CREATE:
            if not process_object.is_alive():
                dead_state += 1
        if dead_state== process_num:
            print("INFO: All child threads have finished running.")
            break
        if shared_decode_run_active.value == False:
            for process_object in PROCESS_CREATE:
                process_object.terminate()
            sys.exit()
        time.sleep(1)

    pack(SHM.name, path_output, size_json, bit_total, isMemmap)
    SHM.close()
    SHM.unlink()
    shared_decode_run_active.value = False
