import time
import json
import ffmpeg
import cv2
import numpy as np
import Common


def build_ffmpeg_data(data_rgb_frame, frame_size_width, frame_size_height):
    """ 输入Numpy原始图像数组数据, 返回用于ffmpeg写入的bytes数据 """
    image_raw_frame = cv2.cvtColor(data_rgb_frame, cv2.COLOR_BGR2RGB)
    image_frame = cv2.resize(image_raw_frame, (frame_size_width, frame_size_height), interpolation=cv2.INTER_NEAREST)
    return image_frame.tobytes()

# Encode BinaryColor V2.1 core
def encode_BinaryColor(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, final=False):
    """ 黑白二色编码, 每个裁剪单元能存储1bit数据 """
    frame_raw_size_width = int(frame_size_width / frame_size_cut)
    frame_raw_size_height = int(frame_size_height / frame_size_cut)
    frame_raw_pixel_number = frame_raw_size_width * frame_raw_size_height   # 每帧ゴ像ス　ス量
    frame_raw_bit_number = frame_raw_pixel_number                           # 每帧ゴbit　ス量
    data_binary_array = np.append(data_memory, np.unpackbits(data_space))

    # イヘヘ最后一个文ゲ, 最后一ケ　ス据
    if final:
        frame_last_fill_num = frame_raw_bit_number - (data_binary_array.size % frame_raw_bit_number)
        data_binary_array = np.pad(data_binary_array, (0, frame_last_fill_num), 'constant', constant_values=(0))

    frame_total = int(data_binary_array.size / frame_raw_bit_number)     # スーギ　コーイ　分配ゴ　帧ス量
    size_end = frame_total * frame_raw_bit_number                        # ス据裁剪 完范围, 总帧ス * 每帧ゴbit总ス
    size_max = data_binary_array.size
    data_remaining = data_binary_array[size_end:size_max].copy()        # モーユ　法子填充完一帧ゴ　ス据ブ分
    data_raw_array = np.zeros((size_end, 3), dtype=np.uint8)
    data_raw_array[data_binary_array[:size_end] == 1] = [255, 255, 255]
    data_binary_array = None
    data_raw_array = data_raw_array.flatten()
    position_record = 0
    position_step = frame_raw_bit_number * 3

    # チ理每一帧ゴ　ス据, 传递ドffmpeg写落ド视频对象
    for x in range(frame_total):
        data_raw_frame = data_raw_array[position_record : (position_record + position_step)]
        position_record += position_step
        data_rgb_frame = np.reshape(data_raw_frame, (frame_raw_size_height, frame_raw_size_width, 3))   # 转成RGB图像3维ス组
        data_raw_frame = None
        data_ffmpeg_bytes = build_ffmpeg_data(data_rgb_frame, frame_size_width, frame_size_height)
        data_rgb_frame = None
        fm_process.stdin.write(data_ffmpeg_bytes)
        with shared_encode_run_count.get_lock():
            shared_encode_run_count.value += 1

    data_memory = np.empty(0, dtype=np.uint8)
    data_memory = np.append(data_memory, data_remaining)
    data_remaining = None
    return data_memory

# Encode RGB3bit V2.1 core
def encode_RGB3bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, final=False):
    """ 彩色编码, 每个裁剪单元能存储3bit数据 """
    frame_raw_size_width = int(frame_size_width / frame_size_cut)
    frame_raw_size_height = int(frame_size_height / frame_size_cut)
    frame_raw_pixel_number = frame_raw_size_width * frame_raw_size_height
    frame_raw_bit_number = frame_raw_pixel_number * 3     # The amount of data a single frame can store if one pixel can hold 3 bits.
    data_binary_array = np.append(data_memory, np.unpackbits(data_space))
    
    # Check if it is the last file, the last segment of data.
    if final:
        frame_last_fill_num = frame_raw_bit_number - (data_binary_array.size % frame_raw_bit_number)
        data_binary_array = np.pad(data_binary_array, (0, frame_last_fill_num), 'constant', constant_values=(0))

    frame_total = int(data_binary_array.size / frame_raw_bit_number)     # Number of frames the data can be allocated to.
    size_end = frame_total * frame_raw_bit_number                        # Data trimming end range, total number of frames * total bits per frame.
    size_max = data_binary_array.size
    data_remaining = data_binary_array[size_end:size_max].copy()        # Part of the data that cannot fill a complete frame.
    data_raw_array = data_binary_array * 255            # Convert binary data to decimal RGB values.
    data_binary_array = None
    position_record = 0

    # Process the data of each frame, pass it to ffmpeg to write into the video object.
    for x in range(frame_total):
        data_raw_frame = data_raw_array[position_record : (position_record + frame_raw_bit_number)]
        position_record += frame_raw_bit_number
        data_rgb_frame = np.reshape(data_raw_frame, (frame_raw_size_height, frame_raw_size_width, 3))   # Convert to a 3D array of RGB images.
        data_raw_frame = None
        data_ffmpeg_bytes = build_ffmpeg_data(data_rgb_frame, frame_size_width, frame_size_height)
        data_rgb_frame = None
        fm_process.stdin.write(data_ffmpeg_bytes)
        with shared_encode_run_count.get_lock():
            shared_encode_run_count.value += 1

    data_memory = np.empty(0, dtype=np.uint8)
    data_memory = np.append(data_memory, data_remaining)
    data_remaining = None
    return data_memory

# Encode RGB6bit V2.1 core
def encode_RGB6bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, final=False):
    """ 彩色编码, 每个裁剪单元能存储6bit数据 """
    frame_raw_size_width = int(frame_size_width / frame_size_cut)
    frame_raw_size_height = int(frame_size_height / frame_size_cut)
    frame_raw_pixel_number = frame_raw_size_width * frame_raw_size_height
    frame_rgb_num = frame_raw_pixel_number * 3   # The number of RGB channels for all original pixels in a single frame.
    frame_raw_bit_number = frame_raw_pixel_number * 6      # The amount of data a single frame can store if one pixel can hold 6 bits.
    data_binary_array = np.append(data_memory, np.unpackbits(data_space))
    
    # Check if it is the last file, the last segment of data.
    if final:
        frame_last_fill_num = frame_raw_bit_number - (data_binary_array.size % frame_raw_bit_number)
        data_binary_array = np.pad(data_binary_array, (0, frame_last_fill_num), 'constant', constant_values=(0))

    frame_total = int(data_binary_array.size / frame_raw_bit_number)     # Number of frames the data can be allocated to.
    size_end = frame_total * frame_raw_bit_number                        # Data trimming end range, total number of frames * total bits per frame.
    size_max = data_binary_array.size
    data_remaining = data_binary_array[size_end:size_max].copy()        # Part of the data that cannot fill a complete frame.
    data_raw_array = np.dot(data_binary_array.reshape(-1, 2), np.array([170, 85]))      # Perform matrix transformation using numpy's dot function.
    data_binary_array = None
    frame_num_total = int(len(data_raw_array) / frame_rgb_num)
    position_record = 0

    # Process the data of each frame, pass it to ffmpeg to write into the video object.
    for x in range(frame_num_total):
        data_raw_frame = data_raw_array[position_record : (position_record + frame_rgb_num)]      # Extract the padding data required for a single frame.
        position_record += frame_rgb_num
        data_rgb_frame = np.reshape(data_raw_frame, (frame_raw_size_height, frame_raw_size_width, 3))   # Convert to a 3D array of RGB images.
        data_raw_frame = None
        data_ffmpeg_bytes = build_ffmpeg_data(data_rgb_frame.astype(np.uint8), frame_size_width, frame_size_height)
        data_rgb_frame = None
        fm_process.stdin.write(data_ffmpeg_bytes)
        with shared_encode_run_count.get_lock():
            shared_encode_run_count.value += 1

    data_memory = np.empty(0, dtype=np.uint8)
    data_memory = np.append(data_memory, data_remaining)
    data_remaining = None
    return data_memory

def run(LIST_PATH_INPUT, path_output, mode, frame_size_width, frame_size_height, frame_size_cut, frame_speed_fps, fm_encoder_type, fm_rate, active_cover, frame_cover_number, shared_encode_run_count, shared_encode_frame_total, shared_encode_run_active):
    shared_encode_run_active.value = True
    path_output_media = path_output + f"/DataMedia_{time.strftime("%Y%m%d-%Hh%Mm%Ss", time.localtime())}.mp4"

    # Create the list, adding information from the file structure dictionary to the list.
    LIST_PATH = list()
    LIST_SIZE = list()
    file_structure_path_raw = Common.build_structure_path_from_list(LIST_PATH_INPUT)
    Common.build_info_from_structure_path(file_structure_path_raw, LIST_PATH, LIST_SIZE)          

    # Calculate the total number of frames.
    if mode == 0:
        shared_encode_frame_total.value = int((sum(LIST_SIZE) * 8) // ((frame_size_width * frame_size_height) // frame_size_cut **2) + 1)
    elif mode == 1:
        shared_encode_frame_total.value = int((sum(LIST_SIZE) * 8) // (((frame_size_width * frame_size_height) // frame_size_cut **2) * 3) + 1)
    elif mode == 2:
        shared_encode_frame_total.value = int((sum(LIST_SIZE) * 8) // (((frame_size_width * frame_size_height) // frame_size_cut **2) * 6) + 1)
    else:
        print("Unexpected ERROR: [FTMencode.run]--> Invalid mode value.")

    # Construct the identifier (4 bytes).
    data_identification_bytes = np.frombuffer(("_DM_").encode("utf-8"), dtype=np.uint8)                 # Identifier, used to identify the file.

    # Construct the JSON structure data.
    file_structure_object_raw = Common.build_structure_object_from_list(LIST_PATH_INPUT)                # Get the JSON structure (as a dictionary).
    file_structure_object_json = json.dumps(file_structure_object_raw, indent=4, ensure_ascii=False)    # Convert to a formatted JSON string.
    data_build_json_bytes = np.frombuffer((file_structure_object_json).encode("utf-8"), dtype=np.uint8)

    # Construct the length information of the JSON (4 bytes).
    data_build_json_size = data_build_json_bytes.size                                                   # Get the np.uint8 size dimensions of the JSON.
    data_build_json_size_bytes = np.frombuffer(data_build_json_size.to_bytes(4), dtype=np.uint8)        # Create the np.uint8 size guide for the JSON.

    # Undefined byte area.
    data_empty_4bytes = np.empty(4, dtype=np.uint8)
    data_empty_20bytes = np.empty(20, dtype=np.uint8)

    # Concatenate and merge the data.
    data_merge_array = np.empty(0, dtype=np.uint8)
    data_merge_array = np.append(data_merge_array, data_empty_4bytes)
    data_merge_array = np.append(data_merge_array, data_identification_bytes)
    data_merge_array = np.append(data_merge_array, data_build_json_size_bytes)
    data_merge_array = np.append(data_merge_array, data_empty_20bytes)
    data_merge_array = np.append(data_merge_array, data_build_json_bytes)
    
    # Connect the FFmpeg pipeline.
    fm_process = ( 
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(frame_size_width, frame_size_height), framerate=frame_speed_fps)
        .output(path_output_media, vcodec=fm_encoder_type, pix_fmt='yuv420p', **{'b:v':fm_rate})
        .overwrite_output()
        .run_async(pipe_stdin=True, cmd="./bin/ffmpeg.exe")
    )

    # Write the cover to the temporary directory.
    if active_cover:
        image_cover = cv2.imread("./temp/cover.png")
        data_ffmpeg_bytes_cover = cv2.cvtColor(image_cover, cv2.COLOR_BGR2RGB).tobytes()
        for x in range(frame_cover_number):
            fm_process.stdin.write(data_ffmpeg_bytes_cover)
    
    # Create memory array and space array to store segmented file data. Here, the space array size is defined as 32MB (33554432 bytes).
    data_memory = np.empty(0, dtype=np.uint8)
    data_space = np.empty(0, dtype=np.uint8)
    data_space = np.append(data_space, data_merge_array)
    data_space_used = 0
    data_space_used += data_merge_array.size
    file_count = 0
    file_total = len(LIST_PATH)
    
    if mode == 0:
        for f_path in LIST_PATH:
            file_count += 1
            data_object = np.fromfile(f_path, dtype=np.uint8)
            data_object_size = data_object.size
            index_start = 0
            index_end = 0

            while True:
                size_space_remaining = 33554432 - data_space_used
                size_data_remaining = data_object_size - index_start

                if size_space_remaining > size_data_remaining:
                    index_end = data_object_size
                    data_space = np.append(data_space, data_object[index_start:index_end])

                    # If it is the last file, the last part.
                    if file_count == file_total:
                        data_memory = encode_BinaryColor(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, True)
                        data_space = None
                    data_space_used = size_data_remaining
                    index_start = 0
                    index_end = 0
                    break 

                else:
                    index_end += size_space_remaining
                    data_space =  np.append(data_space, data_object[index_start:index_end])
                    data_memory = encode_BinaryColor(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count)
                    data_space = None
                    data_space = np.empty(0, dtype=np.uint8)
                    data_space_used = 0
                    index_start = index_end

            data_object = None

    elif mode == 1:
        for f_path in LIST_PATH:
            file_count += 1
            data_object = np.fromfile(f_path, dtype=np.uint8)
            data_object_size = data_object.size
            index_start = 0
            index_end = 0

            while True:
                size_space_remaining = 33554432 - data_space_used
                size_data_remaining = data_object_size - index_start

                if size_space_remaining > size_data_remaining:
                    index_end = data_object_size
                    data_space = np.append(data_space, data_object[index_start:index_end])

                    # If it is the last file, the last part.
                    if file_count == file_total:
                        data_memory = encode_RGB3bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, True)
                        data_space = None
                    data_space_used = size_data_remaining
                    index_start = 0
                    index_end = 0
                    break 

                else:
                    index_end += size_space_remaining
                    data_space =  np.append(data_space, data_object[index_start:index_end])
                    data_memory = encode_RGB3bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count)
                    data_space = None
                    data_space = np.empty(0, dtype=np.uint8)
                    data_space_used = 0
                    index_start = index_end
                
            data_object = None
    
    elif mode == 2:
        for f_path in LIST_PATH:
            file_count += 1
            data_object = np.fromfile(f_path, dtype=np.uint8)
            data_object_size = data_object.size
            index_start = 0
            index_end = 0

            while True:
                size_space_remaining = 33554432 - data_space_used
                size_data_remaining = data_object_size - index_start

                if size_space_remaining > size_data_remaining:
                    index_end = data_object_size
                    data_space = np.append(data_space, data_object[index_start:index_end])

                    # If it is the last file, the last part.
                    if file_count == file_total:
                        data_memory = encode_RGB6bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count, True)
                        data_space = None
                    data_space_used = size_data_remaining
                    index_start = 0
                    index_end = 0
                    break 

                else:
                    index_end += size_space_remaining
                    data_space =  np.append(data_space, data_object[index_start:index_end])
                    data_memory = encode_RGB6bit(fm_process, data_memory, data_space, frame_size_width, frame_size_height, frame_size_cut, shared_encode_run_count)
                    data_space = None
                    data_space = np.empty(0, dtype=np.uint8)
                    data_space_used = 0
                    index_start = index_end

            data_object = None

    else:
        print("Unexpected ERROR: [FTMencode.run]--> Invalid mode value.")

    fm_process.stdin.close()
    fm_process.wait()
    shared_encode_run_active.value = False
