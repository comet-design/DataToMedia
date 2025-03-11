import json
import cv2
import numpy as np


def simple_BinaryColor(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut):
    data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3, 4))
    return (data_frame_average > 127).flatten().astype(np.uint8)

def simple_RGB3bit(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut):
    data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3))
    return (data_frame_average > 127).flatten().astype(np.uint8)

def simple_RGB6bit(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut):
    data_frame_average = frame.reshape(frame_raw_size_height, frame_size_cut, frame_raw_size_width, frame_size_cut, 3).mean(axis=(1, 3))
    data_result = np.zeros((frame_raw_size_height, frame_raw_size_width, 3, 2), dtype=np.uint8)
    mask_0_85 = (data_frame_average <= 85)
    data_result[mask_0_85] = [0, 0]
    data_result[mask_0_85 & (data_frame_average > 42)] = [0, 1]
    mask_85_170 = (data_frame_average > 85) & (data_frame_average <= 170)
    data_result[mask_85_170] = [0, 1]
    data_result[mask_85_170 & (data_frame_average > 127)] = [1, 0]
    mask_170_255 = (data_frame_average > 170)
    data_result[mask_170_255] = [1, 0]
    data_result[mask_170_255 & (data_frame_average > 212)] = [1, 1]
    return data_result.reshape(-1)

def execute_json(path_input, frame_size_cut, mode, size_json, frame_start):
    """ Read the JSON data from the video in the specified path and attempt to save the file to the cache directory.
        Then determine if the JSON is valid; if valid, return True, otherwise return False."""
    path_output_json = "./temp/structure_read.json"    # 设ゼ　JSON　ボ存位ジ
    capture = cv2.VideoCapture(path_input)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)   #　设ゼ　オイ　得ドゴ　帧号　
    frame_raw_size_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) / frame_size_cut)
    frame_raw_size_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) / frame_size_cut)
    frame_pixel_total = frame_raw_size_width * frame_raw_size_height

    if mode == 0:
        frame_bit_total = frame_pixel_total
    elif mode == 1:
        frame_bit_total = frame_pixel_total * 3
    elif mode == 2:
        frame_bit_total = frame_pixel_total * 6
    else:
        print("Unexpected ERROR: Unknown mode error!")

    frame_num_used = int(size_json / (frame_bit_total / 8)) + 1    # JSON　占ユゴ　帧ス量
    data_json_build = np.empty(0, dtype=np.uint8)

    ret, frame = capture.read()
    if mode == 0:
        for x in range(frame_num_used):
            data = simple_BinaryColor(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut)
            data_json_build = np.append(data_json_build, data)
            ret, frame = capture.read()
    elif mode == 1:
        for x in range(frame_num_used):
            data = simple_RGB3bit(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut)
            data_json_build = np.append(data_json_build, data)
            ret, frame = capture.read()
    elif mode == 2:
        for x in range(frame_num_used):
            data = simple_RGB6bit(frame, frame_raw_size_width, frame_raw_size_height, frame_size_cut)
            data_json_build = np.append(data_json_build, data)
            ret, frame = capture.read()
    else:
        print("Unexpected ERROR: Unknown mode error!")
    capture.release()                                       # シ放视频　捕ホ对象, イヘモ　シ放ゴワ，ハデゴ　循环就　モ会从头开チ

    data_json_bytes = np.packbits(data_json_build)
    data_json = data_json_bytes[32 : size_json + 32 ]       # 从切ペ　得ド　JSONス据，因为偏イ了　32个スゼ ，所イ　オイ　ガ32
    data_json.tofile(path_output_json)                      # バ　JSONス据　ボ存成 文ゲ
    with open(path_output_json, "r+", encoding="utf-8") as f_Object:
        try:
            json.load(f_Object)
            print("INFO: Successful, JSON data validation passed, data saved.")
            return True
        except json.JSONDecodeError:
            print("ERROR: Failed, JSON data validation failed, unable to decode correctly. Possible reasons: \n1.Frame loss in the video. \n2.Inaccurate frame color in the video. \n3.Corrupted or contaminated raw pixels in the video frames.")
            return False
        except UnicodeDecodeError:
            print("Error: Failed, JSON data validation failed, data corrupted. Possible reasons: \n1.Frame loss or color distortion in the video.\n2.The 'cut size' value of the video is too small, usually occurs in RGB 6-bit mode.\n3.Corrupted or contaminated raw pixels in the video frames.")
            return False

def try_func(frame, frame_size_width, frame_size_height, size_cut):
    "Attempt to read the identification, and if successful, return True along with the relevant parameters."
    frame_raw_size_width = int(frame_size_width / size_cut)
    frame_raw_size_height = int(frame_size_height / size_cut)
    status, mode, size_json = False, None, None

    for x in range(3):
        if x == 0:
            try:
                data_binary = simple_BinaryColor(frame, frame_raw_size_width, frame_raw_size_height, size_cut)
            except ValueError:
                continue
            else:
                data = np.packbits(data_binary)
        if x == 1:
            try:
                data_binary = simple_RGB3bit(frame, frame_raw_size_width, frame_raw_size_height, size_cut)
            except ValueError:
                continue
            else:
                data = np.packbits(data_binary)
        if x == 2:
            try:
                data_binary = simple_RGB6bit(frame, frame_raw_size_width, frame_raw_size_height, size_cut)
            except ValueError:
                continue
            else:
                data = np.packbits(data_binary)
        try:
            identification = data[4:8].tobytes().decode("utf-8")        # 识别标シゴ　范围ヘ　文件头ブゴ タイ　4~8スゼ 
        except UnicodeDecodeError:
            print(f"INFO: Try, mode {x} Invalid identifier: ???")
        else:
            if identification == "_DM_":
                print(f"INFO: Successful, mode {x} Found Valid identifier.")
                status = True
                mode = x
                size_json = int.from_bytes(data[8:12], byteorder="big")  # JSON长度信息ゴ　范围ヘ　文件头ブゴ タイ　8~12スゼ 
                break
            else:
                status = False
                print(f"INFO: Try, mode {x} Invalid identifier: {identification}")

    return status, mode, size_json      # イヘモ　识别成功ジョ　ファ转默认ゴ赋チ False, None, None

def scan_media(path_input):
    """ Automatic function. Scan the video in the specified path to determine if it is a readable object and conforms to DTM standards. 
        If it does, create a JSON file in the cache directory and return the relevant parameters. Otherwise, return the error type."""
    # 全ブゴ　分辨率　ガア　剪切チ寸
    PUBLIC_LIST_RESOLUTION_INT = [[320, 240], [640, 480], [1024, 768], [256, 144], [640, 360], [1280, 720], [1920, 1080], [3840, 2160]]
    PUBLIC_LIST_SIZE_CUT = [[4,5,8,10], [4,5,8,10], [4,8], [2,4,8], [4,5,8,10], [4,5,8,10], [4,5,8,10], [4,5,8,10]]
    error_type = False
    get_mode = int()
    get_frame_size_cut = int()
    get_size_json = int()
    get_frame_start = int()
    status_execute_json = False

    capture = cv2.VideoCapture(path_input)
    frame_size_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_size_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    FRAME_START_LIST = [0, 2, 24, 120]           # 起始帧表，也就ヘ　在cover帧　后尾ゴ　タイ１帧ゴ　帧ス编ホ, 还ユopencvへ从0帧开チ，所イ会少1
    for x in range(len(FRAME_START_LIST)):
        capture.set(cv2.CAP_PROP_POS_FRAMES, FRAME_START_LIST[x])  #设ゼ　オイ　得ゴ　帧ホ

        ret, frame = capture.read()
        if ret:
            for y in range(len(PUBLIC_LIST_RESOLUTION_INT)):
                # イヘ合　已ユゴ　分辨率
                if (frame_size_width == PUBLIC_LIST_RESOLUTION_INT[y][0] and frame_size_height == PUBLIC_LIST_RESOLUTION_INT[y][1]) or \
                    (frame_size_width == PUBLIC_LIST_RESOLUTION_INT[y][1] and frame_size_height == PUBLIC_LIST_RESOLUTION_INT[y][0]):
                    # 循环出　对应分辨率ゴ　所ユ　裁剪チ寸
                    for size_cut in PUBLIC_LIST_SIZE_CUT[y]:
                        get_status, get_mode, get_size_json = try_func(frame, frame_size_width, frame_size_height, size_cut)
                        if get_status:
                            capture.release()
                            status_execute_json = execute_json(path_input, size_cut, get_mode, get_size_json, FRAME_START_LIST[x])
                            get_frame_size_cut = size_cut
                            error_type = False
                            if status_execute_json == False:
                                error_type = 3
                            break
                        else:
                            error_type = 1
                            print(f"INFO: Scanned frame {x} at {size_cut} cut size, no identification found.")
                    break
                else:
                    error_type = 2
                    print(f"INFO: Failed, {PUBLIC_LIST_RESOLUTION_INT[y][0]}x{PUBLIC_LIST_RESOLUTION_INT[y][1]} resolution does not match, cannot be recognized.")
        else:
            error_type = 4
            print("ERROR: Unable to read the video (OpenCV: ret --> false), possible reasons: \n1.Invalid video format. \n2.Corrupted video file. \n3.Read permission for the video is denied.")

        if error_type == False:
            get_frame_start = FRAME_START_LIST[x]
            break

    capture.release()

    if error_type == False:
        print("INFO: Successful, Video media contains data, ready to start converting.")
        return False, get_mode, get_frame_size_cut, get_size_json, get_frame_start
    else:
        print("ERROR: Failed, Unable to identify whether the video media contains data.")
        return error_type, None, None, None, None

def scan_media_manual(path_input, size, covernum, scansize, scancover):
    """ Semi-automatic function. manually specify the input parameters and scan the video in the specified path to determine if it is a readable object and conforms to DTM standards. 
        If it does, create a JSON file in the cache directory and return the relevant parameters. Otherwise, return the error type. Currently used by [CLI] --> vtf_used_force function. """
    # ベ量名转换
    frame_size_cut = size
    frame_start = covernum

    # ベ量初シーファ
    error_type = False
    get_mode = int()
    get_size_json = int()
    status_execute_json = False

    capture = cv2.VideoCapture(path_input)
    frame_size_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_size_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    # 参ス选项: 扫描チ寸　ガア　封面
    if scansize and scancover:
        flag_find = False
        LIST_SIZE_CUT = list()      # Used to store all available cut sizes for the current video resolution.

        for x in range(2, 400):
            if (frame_size_width % x) == 0 and (frame_size_height % x) == 0:
                LIST_SIZE_CUT.append(x)
        if len(LIST_SIZE_CUT) <= 0:
            return 10

        # Loop through all frames.
        for current_frame in range(frame_total):
            if flag_find:
                break
            else:
                # Loop through all cut sizes.
                ret, frame = capture.read()
                for x in range(len(LIST_SIZE_CUT)):
                    current_size_cut = LIST_SIZE_CUT[x]
                    get_status, get_mode, get_size_json = try_func(frame, frame_size_width, frame_size_height, current_size_cut)

                    # Check if the status has been successfully parsed.
                    if get_status:
                        status_execute_json = execute_json(path_input, current_size_cut, get_mode, get_size_json, current_frame)
                        error_type = False
                        flag_find = True
                        frame_size_cut = current_size_cut       # Store the scanned parameters into variables.
                        frame_start = current_frame

                        # If the JSON cannot be parsed.
                        if status_execute_json == False:
                            error_type = 3
                        break
                    else:
                        error_type = 1
                        print(f"INFO: Scanned frame {current_frame} at {current_size_cut} cut size, no identification found.")

        capture.release()

        if error_type == False:
            print("INFO: Successful, Video media contains data, ready to start converting.")
            return False, get_mode, get_size_json, frame_size_cut, frame_start
        else:
            print("ERROR: Failed, Unable to identify whether the video media contains data.")
            return error_type, None, None, None, None

    # 参ス选项: 仅扫描チ寸
    elif scansize and scancover == False:
        LIST_SIZE_CUT = list()      # Used to store all available cut sizes for the current video resolution.

        for x in range(2, 400):
            if (frame_size_width % x) == 0 and (frame_size_height % x) == 0:
                LIST_SIZE_CUT.append(x)
        if len(LIST_SIZE_CUT) <= 0:
            return 10

        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)       # Set the start frame (this value exactly equals the number of cover frames).
        ret, frame = capture.read()

        # Loop through all cut sizes.
        for x in range(len(LIST_SIZE_CUT)):
            current_size_cut = LIST_SIZE_CUT[x]
            get_status, get_mode, get_size_json = try_func(frame, frame_size_width, frame_size_height, current_size_cut)

            # Check if the status has been successfully parsed.
            if get_status:
                status_execute_json = execute_json(path_input, current_size_cut, get_mode, get_size_json, frame_start)
                error_type = False

                # Store the scanned parameters into variables.
                frame_size_cut = current_size_cut

                # If the JSON cannot be parsed.
                if status_execute_json == False:
                    error_type = 3
                break
            else:
                error_type = 1
                print(f"INFO: Scanned frame {frame_start} at {current_size_cut} cut size, no identification found.")

        capture.release()

        if error_type == False:
            print("INFO: Successful, Video media contains data, ready to start converting.")
            return False, get_mode, get_size_json, frame_size_cut, frame_start
        else:
            print("ERROR: Failed, Unable to identify whether the video media contains data.")
            return error_type, None, None, None, None

    # 参ス选项: 仅扫描封面
    elif scansize == False and scancover:
        # Loop through all frames.
        for current_frame in range(frame_total):
            ret, frame = capture.read()
            get_status, get_mode, get_size_json = try_func(frame, frame_size_width, frame_size_height, frame_size_cut)

            # Check if the status has been successfully parsed.
            if get_status:
                status_execute_json = execute_json(path_input, frame_size_cut, get_mode, get_size_json, current_frame)
                error_type = False
                frame_start = current_frame     # Store the scanned parameters into variables.

                # If the JSON cannot be parsed.
                if status_execute_json == False:
                        error_type = 3
                break
            else:
                error_type = 1
                print(f"INFO: Scanned frame {current_frame} at {frame_size_cut} cut size, no identification found.")

        capture.release()

        if error_type == False:
            print("INFO: Successful, Video media contains data, starting to convert.")
            return False, get_mode, get_size_json, frame_size_cut, frame_start
        else:
            print("ERROR: Failed, Unable to identify whether the video media contains data.")
            return error_type, None, None, None, None

    # モユ参ス: 默认
    else:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_start)       # Set frame start location.
        ret, frame = capture.read()
        get_status, get_mode, get_size_json = try_func(frame, frame_size_width, frame_size_height, frame_size_cut)
        capture.release()

        if get_status:
            status_execute_json = execute_json(path_input, frame_size_cut, get_mode, get_size_json, frame_start)
            error_type = False
            if status_execute_json == False:
                error_type = 3
        else:
            error_type = 1
            print(f"INFO: Scanned frame {frame_start} at {frame_size_cut} cut size, no identification found.")

        if error_type == False:
            print("INFO: Successful, Video media contains data, ready to start converting.")
            return False, get_mode, get_size_json, frame_size_cut, frame_start
        else:
            print("ERROR: Failed, Unable to identify whether the video media contains data.")
            return error_type, None, None, None, None

def read_media_info(path_input):
    "Read the video in the path parameter, get basic information and return it."
    capture = cv2.VideoCapture(path_input)
    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(capture.get(cv2.CAP_PROP_FPS))
    time_total = frame_total / fps          # 视频ゴ　シ长　(second)
    capture.release()
    return frame_width, frame_height, frame_total, fps, time_total

