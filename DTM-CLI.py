import os
import sys
import time
import threading
import click
import coreFTV
import coreVTF
import Automatic
import Common
from multiprocessing import Process, Manager, Value, freeze_support
from tqdm import tqdm
from Cover import Cover

# -- Version information ----------------------------------------------
version = "25.01-dev"
version_date = "2024/12/29"

if __name__ == '__main__':
    freeze_support()
    print("\033[1;34m--\033[0m \033[1;37;44m Data to Media \033[0m \033[1;34m-----------------------\033[0m")
    print(f"\033[34m Version: {version}    ({version_date})\033[0m")
    print("\033[34m Welcome to the DTM CLI program.\033[0m")
    print("\033[1;34m------------------------------------------\033[0m \n")
    if Common.check_exists_path("./bin/ffmpeg.exe") == False:
        print("\033[31mERROR: Cannot find the ffmpeg program, [FTV command] encoding functionality will be unavailable. \n\tPlease check if ffmpeg exists in the path (./bin/ffmpeg.exe). \n\tIf it does not, please download ffmpeg (Version 6.1.1-full or later) and place it in that directory.\033[0m\n")

@click.group()
def cli():
    pass

@cli.command()
@click.option('-m', '--mode', default='0', type=click.Choice(['0', '1', '2', 'binc', 'rgb3','rgb6']), help="Encoding mode. Parameter \033[32m0\033[0m or \033[32mbinc\033[0m corresponds to BinaryColor mode, which has high fault tolerance and is recommended. Parameter \033[32m1\033[0m or \033[32mrgb3\033[0m corresponds to RGB3bit mode. Parameter \033[32m2\033[0m or \033[32mrgb6\033[0m corresponds to RGB6bit mode, which has low fault tolerance and is not recommended.")
@click.option('-i', '--input', type=click.Path(), help="Path of the input files and directories. Only one path is accepted, but more files and directories can be added using the -a option.")
@click.option('-o', '--output', default="./_workspace/File_to_Video_output/", type=click.Path(), help="Path of the output video media.")
@click.option('-a', '--add', multiple=True, type=click.Path(), help="Path of the input files and directories. This option can add multiple files and directories. Example: -a [PATH 1] -a [PATH 2] ...")
@click.option('-r', '--res', default="720p", help="Resolution of the output video media. The supported resolution parameters are: \033[32m240p\033[0m (\033[32m320x240\033[0m), \033[32m480p\033[0m (\033[32m640x480\033[0m), \033[32m768p\033[0m (\033[32m1024x768\033[0m), \033[32m144p\033[0m (\033[32m256x144\033[0m), \033[32m360p\033[0m (\033[32m640x360\033[0m), \033[32m720p\033[0m (\033[32m1280x720\033[0m), \033[32m1080p\033[0m (\033[32m1920x1080\033[0m), \033[32m2160p\033[0m (\033[32m3840x2160\033[0m)(\033[32m4k\033[0m).")
@click.option('-s', '--size', default=4, type=int, help="Can be used with the -F option. Frame cut size, which must be divisible by the length and width of the resolution. The recommended value range is 4 ~ 12, with smaller values being recommended.")
@click.option('-W', '--width', default=None, type=int, help="Must be used with the -F option. Customizes the width of the video.")
@click.option('-H', '--height', default=None, type=int, help="Must be used with the -F option. Customizes the height of the video.")
@click.option('-F', '--force', is_flag=True, help="This option does not require a parameter. Forces the use of non-DTM program standards for custom settings.")
@click.option('-b', '--bitrate', default="40000k", help="Bitrate of the generated video. Unit is Kbps, recommended setting is 40000k (40Mbps). Example: -b 40000k")
@click.option('-e', '--encoder', default="libx264", help="ffmpeg hardware acceleration. Calls the corresponding graphic processor's encoder. Available parameters under the H.264 protocol: Only CPU: \033[32mlibx264\033[0m, NVIDIA: \033[32mh264_nvenc\033[0m, AMD: \033[32mh264_amf\033[0m, Intel GPU: \033[32mh264_qsv\033[0m, Microsoft: \033[32mh264_mf\033[0m. Available parameters under the HEVC/H.265 protocol: Only CPU: \033[32mlibx265\033[0m, NVIDIA: \033[32mhevc_nvenc\033[0m, AMD: \033[32mhevc_amf\033[0m, Intel GPU: \033[32mhevc_qsv\033[0m, Microsoft: \033[32mhevc_mf\033[0m. If an unsupported encoder parameter is used, the program may not function properly.")
@click.option('-f', '--fps', default=24, type=int, help="Frames per second of the video. Recommended setting is 24.")
@click.option('-c', '--cover', default="", type=click.Path(), help="Path to the cover background of the video. Example: -c [PATH]")
@click.option('-cn', '--covernum', default=2, type=int, help="Can be used with the -F option. Number of frames occupied by the cover background of the video. Available parameters: \033[32m0\033[0m, \033[32m2\033[0m, \033[32m24\033[0m, \033[32m120\033[0m. Set to 0 to turn off the cover, Recommended setting is 2.")
@click.option('-q', '--quick', default=0, type=int, help="Applies quick configuration using the configuration information from the corresponding template. Parameter \033[32m1\033[0m: (BinaryColor: 640x360 @24fps), Parameter \033[32m2\033[0m: (BinaryColor: 1280x720 @24fps), Parameter \033[32m3\033[0m: (BinaryColor: 1920x1080 @30fps), Parameter \033[32m4\033[0m: (BinaryColor: 640x480 @24fps), Parameter \033[32m5\033[0m: (RGB 3bit: 640x360 @24fps), Parameter \033[32m6\033[0m: (RGB 3bit: 1280x720 @24fps), Parameter \033[32m7\033[0m: (RGB 6bit: 640x360 @24fps), Parameter \033[32m8\033[0m: (RGB 6bit: 1280x720 @24fps).")
def ftv(mode, input, output, add, res, size, width, height, force, bitrate, encoder, fps, cover, covernum, quick):
    """Convert files and directories to video."""
    active_exit = False

    # 初始化输入路径
    LIST_PATH_INPUT = list()
    LIST_PATH_INPUT.append(input)
    LIST_PATH_INPUT.extend(list(add))
    LIST_PATH_INPUT = [path for path in LIST_PATH_INPUT if path is not None]
    LIST_PATH_INPUT = [path.replace('\\', '/') for path in LIST_PATH_INPUT]  # 将所有路径中的 \ 替换成 / 反斜杠
    LIST_PATH_INPUT = [path.replace('\u202a', '') for path in LIST_PATH_INPUT]
    path_output = output.replace('\\', '/')
    path_output = output.replace('\u202a', '')
    cover = cover.replace('\\', '/')
    cover = cover.replace('\u202a', '')

    # 判断路径是否有效
    for path in LIST_PATH_INPUT:
        if not Common.check_exists_path(path):
            print(f"ERROR: Invalid input path: {path}")
            active_exit = True
    if active_exit:
        sys.exit()

    # 判断输出路径是否存在
    if not Common.check_exists_path(path_output):
        print(f"ERROR: Invalid output path: {path_output} \n")
        sys.exit()

    # 如果没有使用快速配置, 该语句下, 一个是强制选项, 一个是常规选项.
    if quick == 0:
        if force:
            ftv_used_force(LIST_PATH_INPUT, path_output, mode, res, size, width, height, bitrate, encoder, fps, cover, covernum)
        else:
            ftv_normal(LIST_PATH_INPUT, path_output, mode, res, size, bitrate, encoder, fps, cover, covernum)

    # 如果为其他, 就是启用了快速配置
    else:
        try:
            # 如果是从配置 1~8 中选择
            if (1 <= int(quick) <= 8):
                ftv_used_quick(LIST_PATH_INPUT, path_output, encoder, quick)
            else:
                print(f"ERROR: The argument '{quick}' of option '-q' or '--quick' is an invalid value.")
                print("\tIt should be selected from the number range 1~8. If set to 0, the program will ignore this option and run in normal mode.")
        except ValueError:
            print(f"ERROR: The argument '{quick}' of option '-q' or '--quick' is an invalid value.")
            print("\tIt should be selected from the number range 1~8. If set to 0, the program will ignore this option and run in normal mode.")
            sys.exit()

@cli.command()
@click.option('-i', '--input', type=click.Path(), help="Path of the input video media.")
@click.option('-o', '--output', default="./_workspace/Video_to_File_output/", type=click.Path(), help="Path of the output files and directories.")
@click.option('-t', '--thread', default=os.cpu_count(), help="Number of CPU threads to use. By default, it uses the number of logical processors of the system CPU.")
@click.option('-F', '--force', is_flag=True, help="This option does not require a parameter. It is usually enabled when converting non-DTM standard videos to manually specify conversion parameters and scan the video.")
@click.option('-s', '--size', default=4, help="Must be used with the -F option. Frame cut size, which must be divisible by the length and width of the resolution. If this value is unknown, you can use the -SS option to scan.")
@click.option('-cn', '--covernum', default=2, help="Must be used with the -F option. Number of cover frames of the video, which is also the start position of data frames. If this value is unknown, you can use the -SC option to scan.")
@click.option('-SS', '--scansize', is_flag=True, help="Must be used with the -F option. This option does not require a parameter. Scans all available frame cut sizes. Note: It may take a long time to run when used with the -SC option.")
@click.option('-SC', '--scancover', is_flag=True, help="Must be used with the -F option. This option does not require a parameter. Scans all video frames until the start position of data frames (end of cover frames) is found. Note: It may take a long time to run when used with the -SS option.")
def vtf(input, output, thread, size, covernum, force, scansize, scancover):
    "Convert video to files and directories."
    path_input = input.replace('\\', '/')
    path_input = input.replace('\u202a', '')
    path_output = output.replace('\\', '/')
    path_output = output.replace('\u202a', '')

    # 判断输入路径是否存在
    if not Common.check_exists_path(path_input):
        print(f"ERROR: Invalid input path: {path_input} \n")
        sys.exit()

    # 判断输出路径是否存在
    if not Common.check_exists_path(path_output):
        print(f"ERROR: Invalid output path: {path_output} \n")
        sys.exit()

    # 判断 thread 数值是否合法
    try:
        process_num = int(thread)
    except ValueError:
        print(f"WARNING: The argument '{thread}' of option '-t' or '--thread' is an invalid value.")
        print(f"\tIt should be an integer number. The program will use {os.cpu_count()} CPU threads (system value) to process tasks.")
        process_num = os.cpu_count()

    # 判断是否使用 -F 强制指定参数
    if force:
        vtf_used_force(path_input, path_output, process_num, size, covernum, scansize, scancover)
    else:
        vtf_normal(path_input, path_output, process_num)

def ftv_normal(LIST_PATH_INPUT, path_output, mode, res, size, bitrate, encoder, fps, cover, covernum):
    # 设置模式
    if mode == "0" or mode == "bc":
        mode = 0
    elif mode == "1" or mode == "r3":
        mode = 1
    elif mode == "2" or mode == "r6":
        mode = 2
    else:
        print(f"ERROR: The argument '{mode}' of option '-m' or '--mode' is an invalid value.")
        print("\tIt should be '0' or 'bc' (binary color), '1' or 'r3' (rgb 3bit), '2' or 'r6' (rgb 6bit).")
        sys.exit()

    # 根据配置判断分辨率等于多少
    if res == "240p" or res == "320x240":
        frame_size_width, frame_size_height = 320, 240
    elif res == "480p" or res == "640x480":
        frame_size_width, frame_size_height = 640, 480
    elif res == "768p" or res == "1024x768":
        frame_size_width, frame_size_height = 1024, 768
    elif res == "144p" or res == "256x144":
        frame_size_width, frame_size_height = 256, 144
    elif res == "360p" or res == "640x360":
        frame_size_width, frame_size_height = 640, 360
    elif res == "720p" or res == "1280x720":
        frame_size_width, frame_size_height = 1280,  720
    elif res == "1080p" or res == "1920x1080":
        frame_size_width, frame_size_height = 1920, 1080
    elif res == "2160p" or res == "3840x2160" or  res == "4k":
        frame_size_width, frame_size_height = 3840, 2160
    else:
        print(f"ERROR: The argument '{res}' of option '-r' or '--res' is an invalid value.")
        print("\tFor example, it should be something like '720p' or '1280x720' (you can use the --help command to see all available resolutions). ")
        print("\tIf you need a custom resolution, you can use the -W, -H ​​and -F parameters to specify it.")
        sys.exit()

    # 判断是否能够整除，裁剪尺寸
    try:
        if (frame_size_width % int(size)) == 0 and (frame_size_height % int(size)) == 0:
            frame_size_cut = int(size)
        else:
            print(f"ERROR: Value '{size}' for the '-s' or '--size' option cannot be used with the current resolution. ")
            print(f"\t It must be divisible by both the width and height. Available cut size value are: ")
            for x in range(2, 40):
                if (frame_size_width % x) == 0 and (frame_size_height % x) == 0:
                    print(f"{x}, ", end="")
            sys.exit()
    except ValueError:
        print(f"ERROR: The argument '{size}' of option '-s' or '--size' is an invalid value.")
        print("\tIt should be an integer number.")
        sys.exit()

    # 判断帧数的范围
    try:
        if int(fps) >=1 and int(fps) <=240:
            frame_speed_fps = int(fps)
        else:
            print(f"ERROR: Value '{fps}' for the '-f' or '--fps' option is out of range. The parameter should be between 1 and 240.")
            sys.exit()
    except ValueError:
        print(f"ERROR: The argument '{fps}' of option '-f' or '--fps' is an invalid value.")
        print("\tIt should be an integer number.")
        sys.exit()

    # 设置封面背景
    path_image = ""
    set_description = ""

    if cover == "":
        active_display_background = False
    elif Common.check_exists_path(cover):
        active_display_background = True
        path_image = cover
    else:
        print(f"ERROR: The cover background path '{cover}' specified by the '-c' or '--cover' option is invalid. ")
        print(f"\tThe path does not exist or the image cannot be read.")
        sys.exit()

    create_cover = Cover(version, frame_size_width, frame_size_height, frame_speed_fps, path_image, set_description, active_display_background, \
                        active_display_title=True, active_display_resolution=True, active_display_date=True, active_display_full=False, active_display_description=False)
    create_cover.create_cover()

    # 设置封面数量
    try:
        if int(covernum) == 0:
            active_cover = False
            frame_cover_number = 0
        elif int(covernum) == 2:
            active_cover = True
            frame_cover_number = 2
        elif int(covernum) == 24:
            active_cover = True
            frame_cover_number = 24
        elif int(covernum) == 120:
            active_cover = True
            frame_cover_number = 120
        else:
            print(f"ERROR: The argument '{covernum}' of option '-cn' or '--covernum' is an invalid value.")
            print("\tIt should be one of the cover numbers 0, 2, 24, 120. If you need to turn off the cover, you can set it to 0.")
            sys.exit()
    except ValueError:
        print(f"ERROR: The argument '{covernum}' of option '-cn' or '--covernum' is an invalid value.")
        print("\tIt should be one of the cover numbers 0, 2, 24, 120. If you need to turn off the cover, you can set it to 0.")
        sys.exit()

    # 显示提示信息
    print("\n------------- Setup Complete -------------")
    print("Input path: ")
    for path in LIST_PATH_INPUT:
        print(f"\t{path}")

    print("\nOutput path: ")
    print(f"\t{path_output}")

    print(f"Encode mode: {mode}")
    print(f"Resolution: {frame_size_width}x{frame_size_height}")
    print(f"Frame cut size: {frame_size_cut}")
    print(f"FPS: {frame_speed_fps}")
    print(f"ffmpeg encoder: {encoder}")
    print(f"Video bitrate: {bitrate}")

    if active_cover:
        print("Cover: Enabled")
        print(f"Cover frame number: {frame_cover_number}")
        if active_display_background:
            print(f"Cover background path: {path_image}")
    else:
        print("Cover: Disabled")
    print("------------------------------------------\n")

    shared_encode_run_count = Value('i', 0)
    shared_encode_frame_total = Manager().Value('i', 0)
    shared_encode_run_active = Manager().Value('b', False)

    # 执行程序
    if __name__ == '__main__':
        freeze_support()
        p1 = Process(target=coreFTV.run, args=(LIST_PATH_INPUT, path_output, mode, frame_size_width, frame_size_height, frame_size_cut, frame_speed_fps, encoder, bitrate, active_cover, frame_cover_number, shared_encode_run_count, shared_encode_frame_total, shared_encode_run_active))
        p1.start()
        p1.join()

def ftv_used_quick(LIST_PATH_INPUT, path_output, encoder, quick):
    print('\nNote: When the "-q (--quick)" option is enabled, only the "-i (--input)", "-o (--output)", "-a (--add)", and "-e (--encoder)" options are effective. All other options will be ignored.\n\n')
        
    if int(quick) == 1:
        mode = 0
        frame_size_width = 640
        frame_size_height = 360
        frame_size_cut = 4
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2

    elif int(quick) == 2:
        mode = 0
        frame_size_width = 1280
        frame_size_height = 720
        frame_size_cut = 4
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2
    
    elif int(quick) == 3:
        mode = 0
        frame_size_width = 1920
        frame_size_height = 1080
        frame_size_cut = 4
        frame_speed_fps = 30
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2

    elif int(quick) == 4:
        mode = 0
        frame_size_width = 640
        frame_size_height = 480
        frame_size_cut = 4
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2

    elif int(quick) == 5:
        mode = 1
        frame_size_width = 640
        frame_size_height = 360
        frame_size_cut = 4
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2
        
    elif int(quick) == 6:
        mode = 1
        frame_size_width = 1280
        frame_size_height = 720
        frame_size_cut = 4
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2

    elif int(quick) == 7:
        mode = 2
        frame_size_width = 640
        frame_size_height = 360
        frame_size_cut = 8
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2

    elif int(quick) == 8:
        mode = 2
        frame_size_width = 1280
        frame_size_height = 720
        frame_size_cut = 8
        frame_speed_fps = 24
        bitrate = "30000k"
        active_cover = True
        frame_cover_number = 2
    else:
        print("ERROR: An unexpected error occurred.")

    # 直接生成封面
    create_cover = Cover(version, frame_size_width, frame_size_height, frame_speed_fps, path_image="", set_description="", active_display_background=False, \
                        active_display_title=True, active_display_resolution=True, active_display_date=True, active_display_full=False, active_display_description=False)
    create_cover.create_cover()

    shared_encode_run_count = Value('i', 0)
    shared_encode_frame_total = Manager().Value('i', 0)
    shared_encode_run_active = Manager().Value('b', False)

    # 显示提示信息
    print("\n------------- Setup Complete -------------")
    print("Input path: ")
    for path in LIST_PATH_INPUT:
        print(f"\t{path}")

    print("\nOutput path: ")
    print(f"\t{path_output}")

    print(f"Encode mode: {mode}")
    print(f"Resolution: {frame_size_width}x{frame_size_height}")
    print(f"Frame cut size: {frame_size_cut}")
    print(f"FPS: {frame_speed_fps}")
    print(f"ffmpeg encoder: {encoder}")
    print(f"Video bitrate: {bitrate}")

    if active_cover:
        print("Cover: Enabled")
        print(f"Cover frame number: {frame_cover_number}")
    else:
        print("Cover: Disabled")
    print("------------------------------------------\n")

    # 执行程序
    if __name__ == '__main__':
        freeze_support()
        p1 = Process(target=coreFTV.run, args=(LIST_PATH_INPUT, path_output, mode, frame_size_width, frame_size_height, frame_size_cut, frame_speed_fps, encoder, bitrate, active_cover, frame_cover_number, shared_encode_run_count, shared_encode_frame_total, shared_encode_run_active))
        p1.start()
        p1.join()

def ftv_used_force(LIST_PATH_INPUT, path_output, mode, res, size, width, height, bitrate, encoder, fps, cover, covernum):
    # 设置模式
    if mode == "0" or mode == "bc":
        mode = 0
    elif mode == "1" or mode == "r3":
        mode = 1
    elif mode == "2" or mode == "r6":
        mode = 2
    else:
        print(f"ERROR: The argument '{mode}' of option '-m' or '--mode' is an invalid value.")
        print("\tIt should be '0' or 'bc' (binary color), '1' or 'r3' (rgb 3bit), '2' or 'r6' (rgb 6bit).")
        sys.exit()

    # 设置分辨率
    if width == None and height == None:
        # 根据配置判断分辨率等于多少
        if res == "240p" or res == "320x240":
            frame_size_width, frame_size_height = 320, 240
        elif res == "480p" or res == "640x480":
            frame_size_width, frame_size_height = 640, 480
        elif res == "768p" or res == "1024x768":
            frame_size_width, frame_size_height = 1024, 768
        elif res == "144p" or res == "256x144":
            frame_size_width, frame_size_height = 256, 144
        elif res == "360p" or res == "640x360":
            frame_size_width, frame_size_height = 640, 360
        elif res == "720p" or res == "1280x720":
            frame_size_width, frame_size_height = 1280,  720
        elif res == "1080p" or res == "1920x1080":
            frame_size_width, frame_size_height = 1920, 1080
        elif res == "2160p" or res == "3840x2160" or  res == "4k":
            frame_size_width, frame_size_height = 3840, 2160
        else:
            print(f"ERROR: The argument '{res}' of option '-r' or '--res' is an invalid value.")
            print("\tFor example, it should be something like '720p' or '1280x720' (you can use the --help command to see all available resolutions). ")
            print("\tIf you need a custom resolution, you can use the -W, -H ​​and -F parameters to specify it.")
            sys.exit()
    elif width == None and height != None: 
        print(f"ERROR: The value (video width) for the -W option is not set.")
        print("\tWhen using the -F option to customize the resolution, both -W and -H options need to be set with values.")
        sys.exit()
    elif width != None and height == None: 
        print(f"ERROR: The value (video width) for the -W option is not set.")
        print("\tWhen using the -F option to customize the resolution, both -W and -H options need to be set with values.")
        sys.exit()
    else:
        try:
            if (4 <= int(width) <= 61440):
                frame_size_width = width
            else:
                print(f"ERROR: Value '{width}' for the '-W' or '--width' option is out of range. The parameter should be between 4 and 61440.")
                sys.exit()
        except ValueError:
            print(f"ERROR: The argument '{width}' of option '-W' or '--width' is an invalid value.")
            print("\tIt should be a number in the range 4 to 61440.")
            sys.exit()
        try:
            if (4 <= int(height) <= 61440):
                frame_size_height = height
            else:
                print(f"ERROR: Value '{height}' for the '-H' or '--height' option is out of range. The parameter should be between 4 and 61440.")
                sys.exit()
        except ValueError:
            print(f"ERROR: The argument '{height}' of option '-H' or '--height' is an invalid value.")
            print("\tIt should be a number in the range 4 to 61440.")
            sys.exit()

    # 判断是否能够整除，裁剪尺寸
    try:
        if (frame_size_width % int(size)) == 0 and (frame_size_height % int(size)) == 0:
            frame_size_cut = int(size)
        else:
            print(f"ERROR: Value '{size}' for the '-s' or '--size' option cannot be used with the current resolution. ")
            print(f"\t It must be divisible by both the width and height. Available cut size value are: ", end="")
            for x in range(2, 400):
                if (frame_size_width % x) == 0 and (frame_size_height % x) == 0:
                    print(f"{x}, ", end="")
            sys.exit()
    except ValueError:
        print(f"ERROR: The argument '{size}' of option '-s' or '--size' is an invalid value.")
        print("\tIt should be an integer number.")
        sys.exit()

    # 判断帧数的范围
    try:
        if int(fps) >=1 and int(fps) <=960:
            frame_speed_fps = int(fps)
        else:
            print(f"ERROR: Value '{fps}' for the '-f' or '--fps' option is out of range. The parameter should be between 1 and 960.")
            sys.exit()
    except ValueError:
        print(f"ERROR: The argument '{fps}' of option '-f' or '--fps' is an invalid value.")
        print("\tIt should be an integer number.")
        sys.exit()

    # 设置封面背景
    path_image = ""
    set_description = ""

    if cover == "":
        active_display_background = False
    elif Common.check_exists_path(cover):
        active_display_background = True
        path_image = cover
    else:
        print(f"ERROR: The cover background path '{cover}' specified by the '-c' or '--cover' option is invalid. ")
        print(f"\tThe path does not exist or the image cannot be read.")
        sys.exit()

    create_cover = Cover(version, frame_size_width, frame_size_height, frame_speed_fps, path_image, set_description, active_display_background, \
                        active_display_title=True, active_display_resolution=True, active_display_date=True, active_display_full=False, active_display_description=False)
    create_cover.create_cover()

    # 设置封面数量
    try:
        if int(covernum) == 0:
            active_cover = False
            frame_cover_number = 0
        else:
            active_cover = True
            frame_cover_number = int(covernum)
    except ValueError:
        print(f"ERROR: The argument '{covernum}' of option '-cn' or '--covernum' is an invalid value.")
        print("\tIt should be an integer number.")
        sys.exit()

    # 显示设置信息
    print("\n------------- Setup Complete -------------")
    print("Input path: ")
    for path in LIST_PATH_INPUT:
        print(f"\t{path}")

    print("\nOutput path: ")
    print(f"\t{path_output}")

    print(f"Encode mode: {mode}")
    print(f"Resolution: {frame_size_width}x{frame_size_height}")
    print(f"Frame cut size: {frame_size_cut}")
    print(f"FPS: {frame_speed_fps}")
    print(f"ffmpeg encoder: {encoder}")
    print(f"Video bitrate: {bitrate}")

    if active_cover:
        print("Cover: Enabled")
        print(f"Cover frame number: {frame_cover_number}")
        if active_display_background:
            print(f"Cover background path: {path_image}")
    else:
        print("Cover: Disabled")
    print("-----------------------------------------")

    shared_encode_run_count = Value('i', 0)
    shared_encode_frame_total = Manager().Value('i', 0)
    shared_encode_run_active = Manager().Value('b', False)

    # 执行程序
    if __name__ == '__main__':
        freeze_support()
        p1 = Process(target=coreFTV.run, args=(LIST_PATH_INPUT, path_output, mode, frame_size_width, frame_size_height, frame_size_cut, frame_speed_fps, encoder, bitrate, active_cover, frame_cover_number, shared_encode_run_count, shared_encode_frame_total, shared_encode_run_active))
        p1.start()
        p1.join()

def vtf_normal(path_input, path_output, process_num):
    "常规模式"
    error_type, mode, frame_size_cut, json_size, frame_start = Automatic.scan_media(path_input)     # 扫描输入的媒体文件, 如果成功则返回 裁剪尺寸和json大小, 失败则返回 False 和 None标记
    shared_decode_run_count = Value('i', 0)
    shared_decode_run_active = Manager().Value('b', True)

    if error_type == False:
        # 尝试获取文件信息: 视频宽度, 视频高度, 总帧数, 每秒帧数fps, 时长
        frame_size_width, frame_size_height, frame_num_total, object_fps, object_time_total = Automatic.read_media_info(path_input)

        if __name__ == '__main__':
            freeze_support()
            process_decode = Process(target=coreVTF.run, \
                                     args=(path_input, path_output, mode, frame_size_cut, frame_start, process_num, json_size, shared_decode_run_count, shared_decode_run_active))
            process_decode.start()
            threading.Thread(target=vtf_normal_update, \
                             args=(path_input, path_output, mode, process_num, frame_size_width, frame_size_height, frame_size_cut, frame_num_total, frame_start, shared_decode_run_active, shared_decode_run_count)).start()
            process_decode.join()

    else:
        if error_type == 1:
            print("ERROR: Verification identifier not found in the video object, unable to determine if the data is usable.")
            sys.exit()
        elif error_type == 2:
            print("ERROR: The current program does not support reading video at this resolution.")
            print("\nNote: You can try using the -F option with the -SS and -SC options to scan and read this video.")
            sys.exit()
        elif error_type == 3:
            print("ERROR: JSON data validation failed, unable to decode correctly. Possible reasons: \n1.Frame loss in the video \n2.Color distortion in the video frames \n3.Pixel area contamination or corruption in the video frames.")
            sys.exit()
        elif error_type == 4:
            print("ERROR: Unable to read the video object, data is invalid. Possible reasons: \n1.The video object is corrupted or the format type is not supported \n2.Incorrect path, the video object does not exist, or read permission is denied")
            sys.exit()
        elif error_type == 10:
            print("The video resolution is not available. There is no available crop size at this resolution. The current supported crop size range is 0~400, which cannot be divided by the length and width of the resolution.")
        else:
            print("Unexpected ERROR: error_type value error!")
            sys.exit()

def vtf_normal_update(path_input, path_output, mode, process_num, frame_size_width, frame_size_height, frame_size_cut, frame_num_total, frame_start, shared_decode_run_active, shared_decode_run_count): 
    if mode == 0:
        frame_bytes_size = int((frame_size_width * frame_size_height) / (frame_size_cut ** 2) / 8)
    elif mode == 1:
        frame_bytes_size = int((frame_size_width * frame_size_height) / (frame_size_cut ** 2) * 3 / 8)
    elif mode == 2:
        frame_bytes_size = int((frame_size_width * frame_size_height) / (frame_size_cut ** 2) * 6 / 8)
    else:
        print("Unexpected ERROR: [vtf_normal_update]---> mode value invalid.")
        sys.exit()

    progress_total = frame_num_total - frame_start

    print("\n-------------------- Start --------------------")
    print(f"Video input path: {path_input}")
    print(f"Resolution: {frame_size_width}x{frame_size_height}")
    print(f"Frame cut size: {frame_size_cut}")
    print(f"Total Frames: {frame_num_total}    (Cover frames:{frame_start}, Data frames:{progress_total})")
    print(f"Data Size: {round((frame_bytes_size * progress_total / 1048576), 2)} MB    ({frame_bytes_size * progress_total} Bytes)")
    print(f"CPU Usage: {process_num} threads")

    if mode == 0:
        print(f"Mode: Binary color\n")
    elif mode == 1:
        print(f"Mode: RGB 3bit\n")
    elif mode == 2:
        print(f"Mode: RGB 6bit\n")
    else:
        print("Unexpected ERROR: [vtf_normal_update]---> mode value invalid.")
        sys.exit()

    # 初始化进度条
    time.sleep(2)
    progress_bar = tqdm(total=progress_total, desc="Processing")
    time_start = time.time()

    while shared_decode_run_active.value:
        time.sleep(0.5)
        progress_bar.n = shared_decode_run_count.value      # 更新进度条
        progress_bar.refresh()
    progress_bar.close()        # 完成进度条

    time_end = time.time()
    time_used = round((time_end - time_start), 1)
    print("\n------------------- Complete -------------------")
    print(f"File output path: {path_output}")
    print(f"Duration: {time_used} second")
    print(f"Average processing frame speed: {round(progress_total/time_used , 2)} FPS/s")
    print(f"Average reading speed: {round( (round((frame_bytes_size * progress_total / 1048576), 2) / time_used) , 2)} MB/s")
    print("-------------------------------------------------")

    Common.sys_clear_directory("./temp/")       # 清空temp目录

def vtf_used_force(path_input, path_output, process_num, size, covernum, scansize, scancover):
    # 变量转换
    frame_size_cut = size
    frame_start = covernum

    shared_decode_run_count = Value('i', 0)
    shared_decode_run_active = Manager().Value('b', True)
    error_type, mode, json_size, frame_size_cut, frame_start = Automatic.scan_media_manual(path_input, size, covernum, scansize, scancover)

    if error_type == False:
        # 尝试获取文件信息: 视频宽度, 视频高度, 总帧数, 每秒帧数fps, 时长
        frame_size_width, frame_size_height, frame_num_total, object_fps, object_time_total = Automatic.read_media_info(path_input)

        if __name__ == '__main__':
            freeze_support()
            process_decode = Process(target=coreVTF.run, \
                                     args=(path_input, path_output, mode, frame_size_cut, frame_start, process_num, json_size, shared_decode_run_count, shared_decode_run_active))
            process_decode.start()
            threading.Thread(target=vtf_normal_update, \
                             args=(path_input, path_output, mode, process_num, frame_size_width, frame_size_height, frame_size_cut, frame_num_total, frame_start, shared_decode_run_active, shared_decode_run_count)).start()
            process_decode.join()

    else:
        if error_type == 1:
            print("ERROR: Verification identifier not found in the video object, unable to determine if the data is usable.")
            sys.exit()
        elif error_type == 2:
            print("ERROR: The current program does not support reading videos at this resolution.")
            print("\nNote: You can try using the -F option with the -SS and -SC options to scan and read this video.")
            sys.exit()
        elif error_type == 3:
            print("ERROR: JSON data validation failed, unable to decode correctly. Possible reasons: \n1.Frame loss in the video \n2.Color distortion in the video frames \n3.Pixel area contamination or corruption in the video frames.")
            sys.exit()
        elif error_type == 4:
            print("ERROR: Unable to read the video object, data is invalid. Possible reasons: \n1.The video object is corrupted or the format type is not supported \n2.Incorrect path, the video object does not exist, or read permission is denied")
            sys.exit()
        else:
            print("ERROR: error_type value error!")
            sys.exit()

if __name__ == '__main__':
    freeze_support()
    cli()
