import os
import sys
import time
import threading
import configparser
import coreFTV
import coreVTF
import Automatic
import Common
import QTUI.QTResources
from multiprocessing import Process, Manager, Value, freeze_support
from PyQt6.QtWidgets import QApplication, QMessageBox, QMainWindow, QFileDialog,  QTreeWidgetItem, QHeaderView
from PyQt6.QtGui import QIcon, QIntValidator, QPixmap
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from QTUI.QTGuiMain import Ui_MainWindow
from Cover import Cover, QTWindowCover


class QTSignal(QObject):
    "PyQt Signal class."
    # 名字定义: refresh 是多次触发的, update 是单次触发的, event 是某一特定情况下触发的。
    refresh_signal_progress_ftv = pyqtSignal(int, int, int, float, float, float, bool)
    refresh_signal_progress_vtf = pyqtSignal(int, int, int, float, float, float, float, bool)
    event_signal_finish_ftv = pyqtSignal(int)
    event_signal_finish_vtf = pyqtSignal(int)

class QTWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.initProgram()
        self.initUI()

        # -- Version information ----------------------------------------------
        self.version = "25.01-dev"
        self.version_date = "2024/12/29"

        # -- 多进程共享变量 ----------------------------------------------
        self.shared_encode_run_active = Manager().Value('b', False)
        self.shared_encode_frame_total = Manager().Value('i', 0)
        self.shared_decode_run_active = Manager().Value('b', False)

        # self.shared_decode_run_count = Manager().Value('i', 0)
        # 使用 Manager() 创建的变量会出现报错 AttributeError: 'ValueProxy' object has no attribute 'get_lock'
        # 因此要使用 multiprocessing.Value() 对象, 来创建共享变量. https://github.com/python/cpython/issues/79967
        self.shared_encode_run_count = Value('i', 0)

        # -- 接收信号的槽 ------------------------------------------------
        self.signal = QTSignal()
        self.signal.refresh_signal_progress_ftv.connect(self.thread_ftv_refresh_gui)
        self.signal.refresh_signal_progress_vtf.connect(self.thread_vtf_refresh_gui)
        self.signal.event_signal_finish_ftv.connect(self.thread_ftv_finish)
        self.signal.event_signal_finish_vtf.connect(self.thread_vtf_finish)

        # -- 按钮的状态信息 ----------------------------------------------
        self.state_pushButton_encode_conversion = 0
        self.state_pushButton_decode_conversion = 0
        self.CONFIG_UPDATE_LOCK = True      # 防止初始化时触发页面选项的更新
        self.config_init()
        self.config_init_encode_gui()
        self.config_init_decode_gui()
        self.CONFIG_UPDATE_LOCK = False
        self.gui_encode_init_status()
        self.gui_decode_init_status(display_status_path_input=False)

    def initProgram(self):
        """ Initializes the program, checking if the required files exist. """
        if Common.check_exists_path("./config.ini") == False:
            print("INFO: Configuration not found, regenerating...")
            Common.execute_config_create()
            self.show_message_error_encode_type_02()
        if Common.check_exists_path("./bin/ffmpeg.exe") == False:
            self.show_message_error_encode_type_04()

        Common.sys_clear_directory("./temp/")       # 清空temp目录

    def initUI(self):
        """ Initialize QT window binding events. """
        # -- 状态栏 ----------------------------------------------
        self.pushButton_widget1.clicked.connect(self.gui_switch_widget_0)
        self.pushButton_widget2.clicked.connect(self.gui_switch_widget_1)
        self.actionAbout.triggered.connect(self.show_message_info_public_type_01)

        # -- 编码部分 ---------------------------------------------
        self.pushButton_encode_convert.clicked.connect(self.thread_ftv)        # 连接按钮的点击事件和打印 编码 的槽函数
        self.pushButton_encode_input_file.clicked.connect(self.gui_encode_set_path_file)
        self.pushButton_encode_input_directory.clicked.connect(self.gui_encode_set_path_directory)
        self.pushButton_encode_output_directory.clicked.connect(self.gui_encode_set_path_output)
        self.radioButton_encode_mode_0.clicked.connect(self.config_update_encode_mode_00)
        self.radioButton_encode_mode_1.clicked.connect(self.config_update_encode_mode_01)
        self.radioButton_encode_mode_2.clicked.connect(self.config_update_encode_mode_02)
        self.comboBox_encode_encoder.currentIndexChanged.connect(self.config_update_encode_encoder)
        self.horizontalSlider_encode_frame_size_cut.valueChanged.connect(self.config_update_encode_frame_size_cut)
        self.comboBox_encode_frame_size_cut.currentIndexChanged.connect(self.config_update_encode_frame_size_cut_select)
        self.horizontalSlider_encode_fps.valueChanged.connect(self.config_update_encode_fps)
        self.comboBox_encode_fps.currentIndexChanged.connect(self.config_update_encode_fps_select)
        self.horizontalSlider_encode_rate.valueChanged.connect(self.config_update_encode_rate)
        self.comboBox_encode_rate.currentIndexChanged.connect(self.config_update_encode_rate_select)
        self.comboBox_encode_resolution.currentIndexChanged.connect(self.config_update_encode_resolution)
        self.comboBox_encode_frame_cover_number.currentIndexChanged.connect(self.config_update_encode_frame_cover_number)
        self.pushButton_encode_lineEdit_input_directory.clicked.connect(self.config_update_encode_lineEdit_input_directory)
        self.pushButton_encode_lineEdit_output_directory.clicked.connect(self.config_update_encode_lineEdit_output_directory)
        self.pushButton_encode_clear.clicked.connect(self.gui_encode_clear)
        self.pushButton_encode_path_default.clicked.connect(self.gui_encode_set_path_default)
        self.label_encode_treewidget_cover.dragEnterEvent = self.gui_encode_label_treewidget_cover_dragEnter
        self.label_encode_treewidget_cover.dropEvent = lambda object_data :self.gui_encode_label_treewidget_cover_drop(object_data)
        self.treeWidget_encode.setHeaderLabels(['Name', 'Type', 'Size'])
        self.treeWidget_encode.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.pushButton_encode_cover.clicked.connect(self.window_cover_open)
        self.checkBox_encode_cover.clicked.connect(self.config_update_encode_cover)
        self.pushButton_encode_open_output_directory.clicked.connect(self.gui_encode_open_path_output)
        self.pushButton_encode_reset.clicked.connect(self.config_update_encode_rest_default_path)
        self.pushButton_encode_quick_config_01.clicked.connect(self.config_update_encode_quick_config_01)
        self.pushButton_encode_quick_config_02.clicked.connect(self.config_update_encode_quick_config_02)
        self.pushButton_encode_quick_config_03.clicked.connect(self.config_update_encode_quick_config_03)
        self.pushButton_encode_quick_config_04.clicked.connect(self.config_update_encode_quick_config_04)
        self.pushButton_encode_quick_config_05.clicked.connect(self.config_update_encode_quick_config_05)
        self.pushButton_encode_quick_config_06.clicked.connect(self.config_update_encode_quick_config_06)
        self.pushButton_encode_quick_config_07.clicked.connect(self.config_update_encode_quick_config_07)
        self.pushButton_encode_quick_config_08.clicked.connect(self.config_update_encode_quick_config_08)
        self.label_encode_image_title.setPixmap(QPixmap(":/images/title_show.png"))

        # -- 解码部分 ---------------------------------------------
        self.pushButton_decode_convert.clicked.connect(self.thread_vtf)
        self.pushButton_decode_input_file.clicked.connect(self.gui_decode_set_path_file)
        self.comboBox_decode_CPU_num.currentIndexChanged.connect(self.config_update_decode_CPU_num)
        self.lineEdit_decode_CPU_num.textChanged.connect(self.config_update_decode_CPU_num_select)
        self.pushButton_decode_path_default.clicked.connect(self.gui_decode_set_path_default)
        self.pushButton_decode_scan.clicked.connect(self.gui_decode_init)
        self.comboBox_decode_resolution.currentIndexChanged.connect(self.config_update_decode_resolution)
        self.horizontalSlider_decode_frame_size_cut.valueChanged.connect(self.config_update_decode_frame_size_cut)
        self.comboBox_decode_frame_size_cut.currentIndexChanged.connect(self.config_update_decode_frame_size_cut_select)
        self.comboBox_decode_frame_start.currentIndexChanged.connect(self.config_update_decode_frame_start)
        self.pushButton_decode_lineEdit_input_file.clicked.connect(self.config_update_decode_lineEdit_input_file)
        self.pushButton_decode_lineEdit_output_directory.clicked.connect(self.config_update_decode_lineEdit_output_directory)
        self.pushButton_decode_clear.clicked.connect(self.gui_decode_clear)
        self.label_decode_treewidget_cover.dragEnterEvent = self.gui_decode_label_treewidget_cover_dragEnter
        self.label_decode_treewidget_cover.dropEvent = lambda object_data :self.gui_decode_label_treewidget_cover_drop(object_data)
        self.treeWidget_decode.setHeaderLabels(['Name', 'Type', 'Size'])
        self.treeWidget_decode.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.radioButton_decode_mode_0.clicked.connect(self.config_update_decode_mode_00)
        self.radioButton_decode_mode_1.clicked.connect(self.config_update_decode_mode_01)
        self.radioButton_decode_mode_2.clicked.connect(self.config_update_decode_mode_02)
        self.pushButton_decode_open_output_directory.clicked.connect(self.gui_decode_open_path_output)
        self.pushButton_decode_output_directory.clicked.connect(self.gui_decode_set_path_output)
        self.pushButton_decode_reset.clicked.connect(self.config_update_decode_rest_default_path)
        self.label_decode_image_title.setPixmap(QPixmap(":/images/title_show.png"))

        # -- 其他 ---------------------------------------------
        self.icon_file = QIcon(":/icon/file_v1.png")
        self.icon_folder = QIcon(":/icon/folder_v1.png")
        self.PUBLIC_LIST_RESOLUTION_INT = [[320, 240], [640, 480], [1024, 768], [256, 144], [640, 360], [1280, 720], [1920, 1080], [3840, 2160]]
        self.PUBLIC_LIST_RESOLUTION_STR = ["320 x 240", "640 x 480", "1024 x 768", "256 x 144", "640 x 360", "1280 x 720", "1920 x 1080", "3840 x 2160"]
        self.PUBLIC_LIST_SIZE_CUT = [[4,5,8,10], [4,5,8,10], [4,8], [2,4,8], [4,5,8,10], [4,5,8,10], [4,5,8,10], [4,5,8,10]]
        self.PUBLIC_LIST_FRAME_COVER_NUMBER_INT = [2, 24, 120]
        self.PUBLIC_LIST_FRAME_COVER_NUMBER_STR = ["2", "24", "120"]
        self.PUBLIC_LIST_FRAME_START_INT = [1, 3, 25, 121]
        self.PUBLIC_LIST_FRAME_START_STR = ["1", "3", "25", "121"]
        self.PUBLIC_LIST_ENCODER_GUI = ["H264 -CPU", "H264 -AMD AMF", "H264 -NVIDIA NVENC", "H264 -Intel Quick Sync Video", "HEVC -CPU", "HEVC -AMD AMF", "HEVC -NVIDIA NVENC", "HEVC -Intel Quick Sync Video"]
        self.PUBLIC_LIST_ENCODER_FFMPEG = ["libx264", "h264_amf", "h264_nvenc", "h264_qsv", "libx265", "hevc_amf", "hevc_nvenc", "hevc_qsv"]
        self.PUBLIC_LIST_FPS = ["6", "12", "24", "30", "60"]
        self.PUBLIC_LIST_RATE = ["1000k","2000k","3000k","4000k","5000k","6000k","7000k","8000k","9000k","10000k","15000k","20000k","25000k","30000k","35000k","40000k","60000k","120000k","200000k"]
        self.PUBLIC_LIST_CPU_NUM_INT = [1, 2, 4, 8, 12, 16, 24]
        self.PUBLIC_LIST_CPU_NUM_STR = ["1", "2", "4", "8", "12", "16", "24", "custom"]

    # -- ↓配置: 初始化和更新↓ ---------------------------------------------------------------------
    def config_init(self):
        config = configparser.ConfigParser()
        try:
            config.read('./config.ini', encoding="utf-8-sig")
            self.encode_mode = config.getint('Encode', 'encode_mode')
            self.encode_path_input_default = config['Encode']['encode_path_input']
            self.encode_path_output = config['Encode']['encode_path_output']
            self.encode_frame_size_width = config.getint('Encode', 'encode_frame_size_width')
            self.encode_frame_size_height = config.getint('Encode', 'encode_frame_size_height')
            self.encode_frame_size_cut = config.getint('Encode', 'encode_frame_size_cut')
            self.encode_frame_speed_fps = config.getint('Encode', 'encode_frame_speed_fps')
            self.encode_frame_cover_number = config.getint('Encode', 'encode_frame_cover_number')
            self.fm_encoder_type = config['Encode']['fm_encoder_type']
            self.fm_rate = config['Encode']['fm_rate']

            self.decode_path_input = config['Decode']['decode_path_input']
            self.decode_path_output = config['Decode']['decode_path_output']
        except (configparser.NoSectionError, configparser.MissingSectionHeaderError) as e:
            Common.execute_config_create()
            self.show_message_error_encode_type_03()
    
        self.encode_PATH_INPUT_OBJECT_LIST = list()
        self.encode_active_cover = True     # 封面设置 标识

        self.decode_process_num = os.cpu_count()
        self.decode_mode = 0
        self.decode_frame_size_cut = 4
        self.decode_frame_size_width = 320
        self.decode_frame_size_height = 240
        self.decode_frame_start = int()             # 这里的帧数是从0开始的, 所以值应该是 0或2或24, 而 PUBLIC_LIST_FRAME_START_INT 和 PUBLIC_LIST_FRAME_START_STR 是显示在页面上的, 值从1开始, 应该是 1或3或25
        self.decode_frame_num_total = int()
        self.decode_object_fps = int()
        self.decode_object_time_total = float()
        self.decode_json_size = int()
        self.decode_run_active_stop = True
        
        self.cover_path_image = str()
        self.cover_set_description = str()
        self.cover_active_display_background = False
        self.cover_active_display_title = True
        self.cover_active_display_resolution = True
        self.cover_active_display_date = True
        self.cover_active_display_full = False
        self.cover_active_display_description = False

    def config_init_encode_gui(self):
        # 初始化分辨率列表
        self.comboBox_encode_resolution.addItems(self.PUBLIC_LIST_RESOLUTION_STR)
        for x in range(len(self.PUBLIC_LIST_RESOLUTION_STR)):
            str_list = self.PUBLIC_LIST_RESOLUTION_STR[x].split(" ")
            if (str(self.encode_frame_size_width) == str_list[0] and str(self.encode_frame_size_height) == str_list[2]) or \
            (str(self.encode_frame_size_width) == str_list[2] and str(self.encode_frame_size_height) == str_list[0]):
                self.comboBox_encode_resolution.setCurrentIndex(x)
                break
            else:
                continue

        # 初始化cover封面占的帧的数量
        self.comboBox_encode_frame_cover_number.addItems(self.PUBLIC_LIST_FRAME_COVER_NUMBER_STR)
        for x in range(len(self.PUBLIC_LIST_FRAME_COVER_NUMBER_STR)):
            if str(self.encode_frame_cover_number) == self.PUBLIC_LIST_FRAME_COVER_NUMBER_STR[x]:
                self.comboBox_encode_frame_cover_number.setCurrentIndex(x)
                break
            else:
                continue
        
        # 初始化默认输入和输出路径
        self.lineEdit_encode_path_input.setText(self.encode_path_input_default)
        self.lineEdit_encode_path_output.setText(self.encode_path_output)

        # 初始化模块选项
        if self.encode_mode == 0:
            self.radioButton_encode_mode_0.setChecked(True)
        elif self.encode_mode == 1:
            self.radioButton_encode_mode_1.setChecked(True)
        elif self.encode_mode == 2:
            self.radioButton_encode_mode_2.setChecked(True)
        else:
            print("Unexpected ERROR: encode_mode SET ERROR!!")

        # 初始化编码器选项
        self.comboBox_encode_encoder.addItems(self.PUBLIC_LIST_ENCODER_GUI)
        for x in range(len(self.PUBLIC_LIST_ENCODER_FFMPEG)):
            if self.fm_encoder_type == self.PUBLIC_LIST_ENCODER_FFMPEG[x]:
                self.comboBox_encode_encoder.setCurrentIndex(x)

        # 初始化裁剪选项
        for x in range(len(self.PUBLIC_LIST_RESOLUTION_INT)):
            if (self.encode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][0] and self.encode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][1]) or \
            (self.encode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][1] and self.encode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][0]):
                self.horizontalSlider_encode_frame_size_cut.setMaximum(len(self.PUBLIC_LIST_SIZE_CUT[x]) - 1)       # 因为horizontalSlider是从0开始, 如果总数直接设置成某个值, 会多出一个选项，所以要减去1。下面的滑条也是如此。
                self.comboBox_encode_frame_size_cut.addItems([str(size) for size in self.PUBLIC_LIST_SIZE_CUT[x]])
                for y in range(len(self.PUBLIC_LIST_SIZE_CUT[x])):
                    if self.encode_frame_size_cut == self.PUBLIC_LIST_SIZE_CUT[x][y]:
                        self.horizontalSlider_encode_frame_size_cut.setValue(y)
                        self.comboBox_encode_frame_size_cut.setCurrentIndex(y)
                        break
                    else:
                        continue

        # 初始化帧率选项
        self.horizontalSlider_encode_fps.setMaximum(len(self.PUBLIC_LIST_FPS) - 1)
        self.comboBox_encode_fps.addItems(self.PUBLIC_LIST_FPS)
        for x in range(len(self.PUBLIC_LIST_FPS)):
            if str(self.encode_frame_speed_fps) == self.PUBLIC_LIST_FPS[x]:
                self.horizontalSlider_encode_fps.setValue(x)
                self.comboBox_encode_fps.setCurrentIndex(x)
                break
            else:
                continue

        # 初始化码率选项
        self.horizontalSlider_encode_rate.setMaximum(len(self.PUBLIC_LIST_RATE) - 1)
        self.comboBox_encode_rate.addItems(self.PUBLIC_LIST_RATE)
        for x in range(len(self.PUBLIC_LIST_RATE)):
            if self.fm_rate == self.PUBLIC_LIST_RATE[x]:
                self.horizontalSlider_encode_rate.setValue(x)
                self.comboBox_encode_rate.setCurrentIndex(x)
                break
            else:
                continue

        # 初始化快速配置
        self.pixmap_correct = QPixmap(":/icon/correct.png")
        self.label_encode_quick_config_icon_01.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_01.setScaledContents(True)
        self.label_encode_quick_config_icon_01.setVisible(False)

        self.label_encode_quick_config_icon_02.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_02.setScaledContents(True)
        self.label_encode_quick_config_icon_02.setVisible(False)

        self.label_encode_quick_config_icon_03.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_03.setScaledContents(True)
        self.label_encode_quick_config_icon_03.setVisible(False)
        
        self.label_encode_quick_config_icon_04.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_04.setScaledContents(True)
        self.label_encode_quick_config_icon_04.setVisible(False)
        
        self.label_encode_quick_config_icon_05.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_05.setScaledContents(True)
        self.label_encode_quick_config_icon_05.setVisible(False)
        
        self.label_encode_quick_config_icon_06.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_06.setScaledContents(True)
        self.label_encode_quick_config_icon_06.setVisible(False)
        
        self.label_encode_quick_config_icon_07.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_07.setScaledContents(True)
        self.label_encode_quick_config_icon_07.setVisible(False)
        
        self.label_encode_quick_config_icon_08.setPixmap(self.pixmap_correct)
        self.label_encode_quick_config_icon_08.setScaledContents(True)
        self.label_encode_quick_config_icon_08.setVisible(False)

    def config_clear_encode_gui(self):
        self.comboBox_encode_resolution.clear()
        self.comboBox_encode_frame_cover_number.clear()
        self.comboBox_encode_encoder.clear()
        self.comboBox_encode_frame_size_cut.clear()
        self.comboBox_encode_fps.clear()
        self.comboBox_encode_rate.clear()

    def config_update_encode_mode_00(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.encode_mode = 0
            Common.execute_config_write("Encode", "encode_mode", "0")

    def config_update_encode_mode_01(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.encode_mode = 1
            Common.execute_config_write("Encode", "encode_mode", "1")

    def config_update_encode_mode_02(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.encode_mode = 2
            Common.execute_config_write("Encode", "encode_mode", "2")

    def config_update_encode_encoder(self):
        if self.CONFIG_UPDATE_LOCK == False:
            index = self.comboBox_encode_encoder.currentIndex()
            self.fm_encoder_type = self.PUBLIC_LIST_ENCODER_FFMPEG[index]
            Common.execute_config_write("Encode", "fm_encoder_type", self.PUBLIC_LIST_ENCODER_FFMPEG[index])

    def config_update_encode_frame_size_cut(self):
        if self.CONFIG_UPDATE_LOCK == False:
            for x in range(len(self.PUBLIC_LIST_RESOLUTION_INT)):
                if (self.encode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][0] and self.encode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][1]) or \
                (self.encode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][1] and self.encode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][0]):
                    index = self.horizontalSlider_encode_frame_size_cut.value()   # 获取当前滑条的索引
                    self.encode_frame_size_cut = self.PUBLIC_LIST_SIZE_CUT[x][index]        # 设置裁剪尺寸
                    Common.execute_config_write("Encode", "encode_frame_size_cut", self.encode_frame_size_cut)
                    self.CONFIG_UPDATE_LOCK = True
                    self.comboBox_encode_frame_size_cut.setCurrentIndex(index)  # 设置下拉选项
                    self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_frame_size_cut_select(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = int(self.comboBox_encode_frame_size_cut.currentText())
            index = self.comboBox_encode_frame_size_cut.currentIndex()
            self.encode_frame_size_cut = value
            Common.execute_config_write("Encode", "encode_frame_size_cut", self.encode_frame_size_cut)
            self.CONFIG_UPDATE_LOCK = True
            self.horizontalSlider_encode_frame_size_cut.setValue(index)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_fps(self):
        if self.CONFIG_UPDATE_LOCK == False:
            index = self.horizontalSlider_encode_fps.value()
            self.encode_frame_speed_fps = int(self.PUBLIC_LIST_FPS[index])
            Common.execute_config_write("Encode", "encode_frame_speed_fps", self.encode_frame_speed_fps)
            self.CONFIG_UPDATE_LOCK = True
            self.comboBox_encode_fps.setCurrentIndex(index)  # 设置下拉选项
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_fps_select(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = int(self.comboBox_encode_fps.currentText())
            index = self.comboBox_encode_fps.currentIndex()
            self.encode_frame_speed_fps = value
            Common.execute_config_write("Encode", "encode_frame_speed_fps", self.encode_frame_speed_fps)
            self.CONFIG_UPDATE_LOCK = True
            self.horizontalSlider_encode_fps.setValue(index)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_rate(self):
        if self.CONFIG_UPDATE_LOCK == False:
            index = self.horizontalSlider_encode_rate.value()
            self.fm_rate = self.PUBLIC_LIST_RATE[index]
            Common.execute_config_write("Encode", "fm_rate", self.fm_rate)
            self.CONFIG_UPDATE_LOCK = True
            self.comboBox_encode_rate.setCurrentIndex(index)  # 设置下拉选项
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_rate_select(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = self.comboBox_encode_rate.currentText()
            index = self.comboBox_encode_rate.currentIndex()
            self.fm_rate = value
            Common.execute_config_write("Encode", "fm_rate", self.fm_rate)
            self.CONFIG_UPDATE_LOCK = True
            self.horizontalSlider_encode_rate.setValue(index)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_resolution(self):
        if self.CONFIG_UPDATE_LOCK == False:
            index = self.comboBox_encode_resolution.currentIndex()
            self.encode_frame_size_width = self.PUBLIC_LIST_RESOLUTION_INT[index][0]
            self.encode_frame_size_height = self.PUBLIC_LIST_RESOLUTION_INT[index][1]
            self.encode_frame_size_cut = self.PUBLIC_LIST_SIZE_CUT[index][0]            # 设置裁剪尺寸为当前分辨率对应的裁剪尺寸列表中的最小值, 如果不设置可能会造成输出视频时的裁剪尺寸与设置部分(比如更小)
            Common.execute_config_write("Encode", "encode_frame_size_width", self.encode_frame_size_width)
            Common.execute_config_write("Encode", "encode_frame_size_height", self.encode_frame_size_height)
            Common.execute_config_write("Encode", "encode_frame_size_cut", self.encode_frame_size_cut)
            self.CONFIG_UPDATE_LOCK = True
            self.config_clear_encode_gui()         # 先清除GUI的设置, 不然会重复添加
            self.config_init_encode_gui()
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_frame_cover_number(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = self.comboBox_encode_frame_cover_number.currentText()
            for x in range(len(self.PUBLIC_LIST_FRAME_COVER_NUMBER_INT)):
                if str(self.PUBLIC_LIST_FRAME_COVER_NUMBER_INT[x]) == value:
                    self.encode_frame_cover_number = self.PUBLIC_LIST_FRAME_COVER_NUMBER_INT[x]
                    Common.execute_config_write("Encode", "encode_frame_cover_number", self.encode_frame_cover_number)

    def config_update_encode_lineEdit_input_directory(self):
        path_input = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path_input != "":
            self.encode_path_input_default = path_input + "/"
            Common.execute_config_write("Encode", "encode_path_input", self.encode_path_input_default)
            self.CONFIG_UPDATE_LOCK = True
            self.lineEdit_encode_path_input.setText(self.encode_path_input_default)
            self.CONFIG_UPDATE_LOCK = False
    
    def config_update_encode_lineEdit_output_directory(self):
        path_input = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path_input != "":
            self.encode_path_output = path_input + "/"
            Common.execute_config_write("Encode", "encode_path_output", self.encode_path_output)
            self.CONFIG_UPDATE_LOCK = True
            self.lineEdit_encode_path_output.setText(self.encode_path_output)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_rest_default_path(self):
        """ 使用缺省路径 """
        Common.execute_directory_create(["./_workspace/File_to_Video_input/", "./_workspace/File_to_Video_output/"])
        Common.execute_config_write("Encode", "encode_path_input", "./_workspace/File_to_Video_input/")
        Common.execute_config_write("Encode", "encode_path_output", "./_workspace/File_to_Video_output/")
        self.CONFIG_UPDATE_LOCK = True
        self.lineEdit_encode_path_input.setText("./_workspace/File_to_Video_input/")
        self.lineEdit_encode_path_output.setText("./_workspace/File_to_Video_output/")
        self.CONFIG_UPDATE_LOCK = False

    def config_update_encode_cover(self):
        if self.checkBox_encode_cover.isChecked():
            self.encode_active_cover = True
            self.pushButton_encode_cover.setEnabled(True)
        else:
            self.encode_active_cover = False
            self.pushButton_encode_cover.setEnabled(False)

    def config_update_encode_quick_config_01(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 0                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "0")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 640                                      # 设置分辨率
            self.encode_frame_size_height = 360
            Common.execute_config_write("Encode", "encode_frame_size_width", 640)
            Common.execute_config_write("Encode", "encode_frame_size_height", 360)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_0.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(4)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_01.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_01.setVisible(False))

    def config_update_encode_quick_config_02(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 0                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "0")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 1280                                     # 设置分辨率
            self.encode_frame_size_height = 720
            Common.execute_config_write("Encode", "encode_frame_size_width", 1280)
            Common.execute_config_write("Encode", "encode_frame_size_height", 720)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_0.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(5)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_02.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_02.setVisible(False))

    def config_update_encode_quick_config_03(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 0                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "0")
            self.encode_frame_speed_fps = 30                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 30)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 1920                                     # 设置分辨率
            self.encode_frame_size_height = 1080
            Common.execute_config_write("Encode", "encode_frame_size_width", 1920)
            Common.execute_config_write("Encode", "encode_frame_size_height", 1080)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_0.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(3)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(3)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(6)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_03.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_03.setVisible(False))

    def config_update_encode_quick_config_04(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 0                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "0")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 640                                     # 设置分辨率
            self.encode_frame_size_height = 480
            Common.execute_config_write("Encode", "encode_frame_size_width", 640)
            Common.execute_config_write("Encode", "encode_frame_size_height", 480)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_0.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(6)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_04.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_04.setVisible(False))

    def config_update_encode_quick_config_05(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 1                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "1")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 640                                     # 设置分辨率
            self.encode_frame_size_height = 360
            Common.execute_config_write("Encode", "encode_frame_size_width", 640)
            Common.execute_config_write("Encode", "encode_frame_size_height", 360)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_1.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(4)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_05.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_05.setVisible(False))

    def config_update_encode_quick_config_06(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 1                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "1")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 1280                                     # 设置分辨率
            self.encode_frame_size_height = 720
            Common.execute_config_write("Encode", "encode_frame_size_width", 1280)
            Common.execute_config_write("Encode", "encode_frame_size_height", 720)
            self.encode_frame_size_cut = 4                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 4)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_1.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(5)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(0)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(0)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_06.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_06.setVisible(False))

    def config_update_encode_quick_config_07(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 2                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "2")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 640                                     # 设置分辨率
            self.encode_frame_size_height = 360
            Common.execute_config_write("Encode", "encode_frame_size_width", 640)
            Common.execute_config_write("Encode", "encode_frame_size_height", 360)
            self.encode_frame_size_cut = 8                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 8)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_2.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(4)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(2)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(2)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_07.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_07.setVisible(False))

    def config_update_encode_quick_config_08(self):
        if self.CONFIG_UPDATE_LOCK == False:
            #  ----------------------- 配置更新 ------------------------------
            self.encode_mode = 2                                                    # 设置模式
            Common.execute_config_write("Encode", "encode_mode", "2")
            self.encode_frame_speed_fps = 24                                        # 设置FPS帧率
            Common.execute_config_write("Encode", "encode_frame_speed_fps", 24)
            self.fm_rate = "40000k"                                                 # 设置码率
            Common.execute_config_write("Encode", "fm_rate", "40000k")
            self.encode_frame_size_width = 1280                                     # 设置分辨率
            self.encode_frame_size_height = 720
            Common.execute_config_write("Encode", "encode_frame_size_width", 1280)
            Common.execute_config_write("Encode", "encode_frame_size_height", 720)
            self.encode_frame_size_cut = 8                                          # 设置裁剪尺寸
            Common.execute_config_write("Encode", "encode_frame_size_cut", 8)

            #  ----------------------- 页面更新 ------------------------------
            self.CONFIG_UPDATE_LOCK = True
            self.radioButton_encode_mode_2.setChecked(True)         # 设置模式
            self.horizontalSlider_encode_fps.setValue(2)            # 设置FPS帧率
            self.comboBox_encode_fps.setCurrentIndex(2)
            self.horizontalSlider_encode_rate.setValue(13)          # 设置码率
            self.comboBox_encode_rate.setCurrentIndex(13)
            self.comboBox_encode_resolution.setCurrentIndex(5)      # 设置分辨率
            self.config_clear_encode_gui()
            self.config_init_encode_gui()
            self.comboBox_encode_frame_size_cut.setCurrentIndex(2)  # 设置裁剪尺寸
            self.horizontalSlider_encode_frame_size_cut.setValue(2)
            self.CONFIG_UPDATE_LOCK = False

            # 先显示label图标, 再设置定时器，3秒后隐藏label
            self.label_encode_quick_config_icon_08.setVisible(True)
            QTimer.singleShot(3000, lambda: self.label_encode_quick_config_icon_08.setVisible(False))

    def config_init_decode_gui(self):
        """ 在启动程序时自动执行, 解码部分的页面设置参数更新 """
        # 隐藏 重新扫描按钮
        self.pushButton_decode_scan.setHidden(True)        

        # 分辨率设置
        self.comboBox_decode_resolution.addItems(self.PUBLIC_LIST_RESOLUTION_STR)
        for x in range(len( self.PUBLIC_LIST_RESOLUTION_STR)):
            str_list =  self.PUBLIC_LIST_RESOLUTION_STR[x].split(" ")
            if (str(self.decode_frame_size_width) == str_list[0] and str(self.decode_frame_size_height) == str_list[2]) or \
            (str(self.decode_frame_size_width) == str_list[2] and str(self.decode_frame_size_height) == str_list[0]):
                self.comboBox_decode_resolution.setCurrentIndex(x)
                break
            else:
                continue

        # 裁剪尺寸设置
        for x in range(len(self.PUBLIC_LIST_RESOLUTION_INT)):
            if (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][0] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][1]) or \
            (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][1] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][0]):
                self.horizontalSlider_decode_frame_size_cut.setMaximum(len(self.PUBLIC_LIST_SIZE_CUT[x]) - 1)       # 因为horizontalSlider是从0开始, 如果总数直接设置成某个值, 会多出一个选项，所以要减去1。下面的滑条也是如此。
                self.comboBox_decode_frame_size_cut.addItems([str(size) for size in self.PUBLIC_LIST_SIZE_CUT[x]])
                for y in range(len(self.PUBLIC_LIST_SIZE_CUT[x])):
                    if self.decode_frame_size_cut == self.PUBLIC_LIST_SIZE_CUT[x][y]:
                        self.horizontalSlider_decode_frame_size_cut.setValue(y)
                        self.comboBox_decode_frame_size_cut.setCurrentIndex(y)
                        break
                    else:
                        continue

        # 起始帧设置
        self.comboBox_decode_frame_start.addItems(self.PUBLIC_LIST_FRAME_START_STR)
        for x in range(len(self.PUBLIC_LIST_FRAME_START_STR)):
            if str(self.decode_frame_start + 1) == self.PUBLIC_LIST_FRAME_START_STR[x]:
                self.comboBox_decode_frame_start.setCurrentIndex(x)
                break
            else:
                continue

        # 设置CPU利用数量
        self.comboBox_decode_CPU_num.addItems(self.PUBLIC_LIST_CPU_NUM_STR)
        for x in range(len(self.PUBLIC_LIST_CPU_NUM_STR)):
            if str(self.decode_process_num) == self.PUBLIC_LIST_CPU_NUM_STR[x]:
                self.comboBox_decode_CPU_num.setCurrentIndex(x)
                self.lineEdit_decode_CPU_num.setPlaceholderText(str(self.decode_process_num))
                break
            else:
                continue
        self.lineEdit_decode_CPU_num.setValidator(QIntValidator())      # 限制 输入栏只能输入 int 数值

        # 初始化默认输入和输出路径
        self.lineEdit_decode_path_input.setText(self.decode_path_input)
        self.lineEdit_decode_path_output.setText(self.decode_path_output)

    def config_init_decode_gui_automatic(self):
        """ 解码部分的页面设置参数更新, 应在自动识别媒体文件成功后触发执行 """
        # 分辨率设置
        for x in range(len(self.PUBLIC_LIST_RESOLUTION_STR)):
            str_list = self.PUBLIC_LIST_RESOLUTION_STR[x].split(" ")
            if (str(self.decode_frame_size_width) == str_list[0] and str(self.decode_frame_size_height) == str_list[2]) or \
            (str(self.decode_frame_size_width) == str_list[2] and str(self.decode_frame_size_height) == str_list[0]):
                self.comboBox_decode_resolution.setCurrentIndex(x)
                break
            else:
                continue

        # 初始化裁剪尺寸
        for x in range(len(self.PUBLIC_LIST_RESOLUTION_INT)):
            if (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][0] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][1]) or \
            (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][1] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][0]):
                # self.horizontalSlider_decode_frame_size_cut.setMaximum(len(self.PUBLIC_LIST_SIZE_CUT[x]) - 1)       # 因为horizontalSlider是从0开始, 如果总数直接设置成某个值, 会多出一个选项，所以要减去1。下面的滑条也是如此。
                for y in range(len(self.PUBLIC_LIST_SIZE_CUT[x])):
                    if self.decode_frame_size_cut == self.PUBLIC_LIST_SIZE_CUT[x][y]:
                        self.horizontalSlider_decode_frame_size_cut.setValue(y)
                        self.comboBox_decode_frame_size_cut.setCurrentIndex(y)
                        break
                    else:
                        continue

        # 初始化起始帧
        for x in range(len(self.PUBLIC_LIST_FRAME_START_STR)):
            if str(self.decode_frame_start + 1) == self.PUBLIC_LIST_FRAME_START_STR[x]:
                self.comboBox_decode_frame_start.setCurrentIndex(x)
                break
            else:
                continue

    def config_clear_decode_gui(self):
        """ 这里是清除GUI上的下拉选项的内容 """
        self.comboBox_decode_CPU_num.clear()
        self.comboBox_decode_resolution.clear()
        self.comboBox_decode_frame_size_cut.clear()
        self.comboBox_decode_frame_start.clear()

    def config_update_decode_CPU_num(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = self.comboBox_decode_CPU_num.currentText()
            if value == "custom":
                self.decode_process_num = 1         # 如果选项为 custom 则将其设置为1
                Common.execute_config_write("Decode", "decode_process_num", 1)
                self.CONFIG_UPDATE_LOCK = True
                self.lineEdit_decode_CPU_num.setPlaceholderText(str(self.decode_process_num))
                self.CONFIG_UPDATE_LOCK = False
            else:
                for x in range(len(self.PUBLIC_LIST_CPU_NUM_INT)):
                    if str(self.PUBLIC_LIST_CPU_NUM_INT[x]) == value:
                        self.decode_process_num = self.PUBLIC_LIST_CPU_NUM_INT[x]
                        Common.execute_config_write("Decode", "decode_process_num", self.decode_process_num)
                        self.CONFIG_UPDATE_LOCK = True
                        self.lineEdit_decode_CPU_num.clear()
                        self.lineEdit_decode_CPU_num.setPlaceholderText(str(self.decode_process_num))
                        self.CONFIG_UPDATE_LOCK = False

    def config_update_decode_CPU_num_select(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = self.lineEdit_decode_CPU_num.text()
            if self.comboBox_decode_CPU_num.currentText() != "custom":
                self.CONFIG_UPDATE_LOCK = True
                self.comboBox_decode_CPU_num.setCurrentText("custom")    # 将下拉列表设置为 "custom"
                self.CONFIG_UPDATE_LOCK = False
            if value == "":         # 如果输入栏删掉了内容
                self.CONFIG_UPDATE_LOCK = True
                self.comboBox_decode_CPU_num.setCurrentIndex(0)     # 将下拉列表设置为 "1"# 可能要修改
                self.CONFIG_UPDATE_LOCK = False
            else:
                self.decode_process_num = int(value)
                Common.execute_config_write("Decode", "decode_process_num", value)

    def config_update_decode_resolution(self):
        if self.CONFIG_UPDATE_LOCK == False:
            index = self.comboBox_decode_resolution.currentIndex()
            self.decode_frame_size_width = self.PUBLIC_LIST_RESOLUTION_INT[index][0]
            self.decode_frame_size_height = self.PUBLIC_LIST_RESOLUTION_INT[index][1]
            self.CONFIG_UPDATE_LOCK = True
            self.config_clear_decode_gui()         # 先清除GUI的设置, 不然会重复添加
            self.config_init_decode_gui()
            self.CONFIG_UPDATE_LOCK = False

            self.pushButton_decode_scan.setHidden(False)         # 显示重新扫描按钮
            self.pushButton_decode_convert.setEnabled(False)

    def config_update_decode_frame_size_cut(self):
        if self.CONFIG_UPDATE_LOCK == False:
            for x in range(len(self.PUBLIC_LIST_RESOLUTION_INT)):
                if (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][0] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][1]) or \
                (self.decode_frame_size_width == self.PUBLIC_LIST_RESOLUTION_INT[x][1] and self.decode_frame_size_height == self.PUBLIC_LIST_RESOLUTION_INT[x][0]):
                    index = self.horizontalSlider_decode_frame_size_cut.value()         # 获取当前滑条的索引
                    self.decode_frame_size_cut = self.PUBLIC_LIST_SIZE_CUT[x][index]    # 设置裁剪尺寸
                    self.CONFIG_UPDATE_LOCK = True
                    self.comboBox_decode_frame_size_cut.setCurrentIndex(index)          # 设置下拉选项
                    self.CONFIG_UPDATE_LOCK = False

    def config_update_decode_frame_size_cut_select(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = int(self.comboBox_decode_frame_size_cut.currentText())
            index = self.comboBox_decode_frame_size_cut.currentIndex()
            self.decode_frame_size_cut = value
            self.CONFIG_UPDATE_LOCK = True
            self.horizontalSlider_decode_frame_size_cut.setValue(index)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_decode_frame_start(self):
        if self.CONFIG_UPDATE_LOCK == False:
            value = self.comboBox_decode_frame_start.currentText()
            for x in range(len(self.PUBLIC_LIST_FRAME_START_INT)):
                if str(self.PUBLIC_LIST_FRAME_START_INT[x]) == value:
                    self.decode_frame_start = self.PUBLIC_LIST_FRAME_START_INT[x] - 1

    def config_update_decode_lineEdit_input_file(self):
        path_input, obj_type = QFileDialog.getOpenFileName(self, "Select File", "", "Video Media (*.mp4 *.mkv *.mov *.avi *.mpeg *.wmv *.flv *.webm *.ts)")
        if path_input != "":
            self.decode_path_input = path_input
            Common.execute_config_write("Decode", "decode_path_input", self.decode_path_input)
            self.CONFIG_UPDATE_LOCK = True
            self.lineEdit_decode_path_input.setText(self.decode_path_input)
            self.CONFIG_UPDATE_LOCK = False
    
    def config_update_decode_lineEdit_output_directory(self):
        path_input = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path_input != "":
            self.decode_path_output = path_input + "/"
            Common.execute_config_write("Decode", "decode_path_output", self.decode_path_output)
            self.CONFIG_UPDATE_LOCK = True
            self.lineEdit_decode_path_output.setText(self.decode_path_output)
            self.CONFIG_UPDATE_LOCK = False

    def config_update_decode_rest_default_path(self):
        """ 将缺省路径恢复为默认初始状态 """
        Common.execute_directory_create(["./_workspace/Video_to_File_input/demo.mp4", "./_workspace/Video_to_File_output/"])
        Common.execute_config_write("Decode", "decode_path_input", "./_workspace/Video_to_File_input/demo.mp4")
        Common.execute_config_write("Decode", "decode_path_output", "./_workspace/Video_to_File_output/")
        self.CONFIG_UPDATE_LOCK = True
        self.lineEdit_decode_path_input.setText("./_workspace/Video_to_File_input/demo.mp4")
        self.lineEdit_decode_path_output.setText("./_workspace/Video_to_File_output/")
        self.CONFIG_UPDATE_LOCK = False

    def config_update_decode_mode_00(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.decode_mode = 0

    def config_update_decode_mode_01(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.decode_mode = 1
    
    def config_update_decode_mode_02(self):
        if self.CONFIG_UPDATE_LOCK == False:
            self.decode_mode = 2

    # -- ↓页面: 公共交互↓ ---------------------------------------------------------------------
    def gui_switch_widget_0(self):
        self.stackedWidget.setCurrentIndex(0)
        
    def gui_switch_widget_1(self):
        self.stackedWidget.setCurrentIndex(1)

    def gui_build_tree(self, data, parent):
        """ 在目录中生成文件的树型结构 """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "F":
                    for file_name, file_info in value.items():
                        size_mb =  float(file_info.get('S', '') / 1048576)
                        size_mb_str = str(format(size_mb, '.3f')) + " MB"
                        item = QTreeWidgetItem([file_name, 'File', size_mb_str])
                        item.setIcon(0, self.icon_file)
                        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
                        parent.addChild(item)
                elif key == "D":
                    for dir_name, dir_info in value.items():
                        item = QTreeWidgetItem([dir_name, 'Directory', ''])
                        item.setIcon(0, self.icon_folder)
                        parent.addChild(item)
                        self.gui_build_tree(dir_info, item)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                item = QTreeWidgetItem([f'[{index}]', 'Array'])
                parent.addChild(item)
                self.gui_build_tree(value, item)
        else:
            item = QTreeWidgetItem([str(data), 'Value'])
            parent.addChild(item)


# -- ↓页面: 提示窗↓ ---------------------------------------------------------------------
    def show_message_info_public_type_01(self):
        display_text = f"Data to Media Program\n\nVersion: {self.version}   ({self.version_date})"
        QMessageBox.information(self, f"INFO Type 01", display_text, QMessageBox.StandardButton.Ok)

    def show_message_info_public_type_02(self):
        QMessageBox.information(self, "INFO Type 02", "The task has been aborted.", QMessageBox.StandardButton.Ok)

    def show_message_info_encode_type_01(self):
        display_text = f"Conversion complete, file has been saved to: \n {self.encode_path_output}"
        QMessageBox.information(self, f"INFO Type 01", display_text, QMessageBox.StandardButton.Ok)

    def show_message_error_encode_type_01(self):
        QMessageBox.warning(self, "Error Type 01", "The selected path does not exist or is not readable. Please check or reset the path.", QMessageBox.StandardButton.Ok)

    def show_message_error_encode_type_02(self):
        QMessageBox.warning(self, "Error Type 02", "Cannot find the configuration file for the program. It has been regenerated. \nPath: ./config.ini", QMessageBox.StandardButton.Ok)

    def show_message_error_encode_type_03(self):
        QMessageBox.warning(self, "Error Type 03", "There is an error in the program’s configuration file, making it unreadable. The program has rebuilt the configuration file.", QMessageBox.StandardButton.Ok)

    def show_message_error_encode_type_04(self):
        QMessageBox.critical(self, "Error Type 04", "Cannot find the ffmpeg program, encoding functionality will be unavailable. \nPlease check if ffmpeg exists in the path (./bin/ffmpeg.exe). \nIf it does not, please download ffmpeg (Version 6.1.1-full or later) and place it in that directory.", QMessageBox.StandardButton.Ok)

    def show_message_error_encode_type_05(self):
        QMessageBox.warning(self, "Error Type 05", "Unable to open the output path, please check whether the configuration is correct.", QMessageBox.StandardButton.Ok)

    def show_message_info_decode_type_01(self):
        display_text = f"Conversion complete, file has been saved to: \n {self.decode_path_output}"
        QMessageBox.information(self, f"INFO Type 01", display_text, QMessageBox.StandardButton.Ok)

    # def show_message_info_decode_type_02(self):
    #     QMessageBox.information(self, "INFO Type 02", "The task has been aborted.", QMessageBox.StandardButton.Ok)

    def show_message_error_decode_type_01(self):
        QMessageBox.warning(self, "Error Type 01", "Verification identifier not found in the video object, unable to determine if the data is usable.", QMessageBox.StandardButton.Ok)

    def show_message_error_decode_type_02(self):
        QMessageBox.warning(self, "Error Type 02", "The current program does not support reading videos at this resolution.", QMessageBox.StandardButton.Ok)

    def show_message_error_decode_type_03(self):
        QMessageBox.critical(self, "Error Type 03", "JSON data validation failed, unable to decode correctly. Possible reasons: \n1.Frame loss in the video \n2.Color distortion in the video frames \n3.Pixel area contamination or corruption in the video frames", QMessageBox.StandardButton.Ok)

    def show_message_error_decode_type_04(self):
        QMessageBox.critical(self, "Error Type 04", "Unable to read the video object, data is invalid. Possible reasons: \n1.The video object is corrupted or the format type is not supported \n2.Incorrect path, the video object does not exist, or read permission is denied", QMessageBox.StandardButton.Ok)

    def show_message_error_decode_type_05(self):
        QMessageBox.warning(self, "Error Type 05", "Unable to open the output path, please check whether the configuration is correct.", QMessageBox.StandardButton.Ok)

    # -- ↓页面: 编码部分交互↓ ---------------------------------------------------------------------
    def gui_encode_init_status(self):
        """ 初始化显示信息, 输入路径, 输出路径之类的 """
        F_PATH_LIST, F_SIZE_LIST = Common.build_info_from_list(self.encode_PATH_INPUT_OBJECT_LIST)

        display_text = "Initialization complete."
        if len(F_PATH_LIST) != 0 and len(F_SIZE_LIST) != 0:
            display_text = f"Files: {len(F_PATH_LIST)}        Size: {round((sum(F_SIZE_LIST) / 1048576), 2)} MB"

        self.label_encode_status_info.setText(display_text)
        self.label_encode_status_path_output.setText(self.encode_path_output)

    def gui_encode_init_treewidget(self):
        self.treeWidget_encode.clear()
        directory_structure = Common.build_structure_object_from_list(self.encode_PATH_INPUT_OBJECT_LIST)
        self.gui_build_tree(directory_structure, self.treeWidget_encode.invisibleRootItem())  # 将json结构显示在 GUI中

    def gui_encode_clear(self):
        """ 清除配置 """
        self.treeWidget_encode.clear()
        self.encode_PATH_INPUT_OBJECT_LIST.clear()
        self.pushButton_encode_convert.setEnabled(False)
        self.label_encode_treewidget_cover.setVisible(True)                # 设置遮盖标签的可见性

    def gui_encode_set_path_file(self):
        """ 点击'添加文件'时触发, 可选择多个文件以列表形式添加到输入列表中, 同时初始化Tree结构显示和状态信息 """
        path_get_list, obj_type = QFileDialog.getOpenFileNames(self, "Select files", "", "All Files (*)")
        if len(path_get_list) != 0:
            self.encode_PATH_INPUT_OBJECT_LIST.extend(path_get_list)
            self.gui_encode_init_treewidget()                       # 初始化GUI树型显示
            self.pushButton_encode_convert.setEnabled(True)
            self.label_encode_treewidget_cover.setVisible(False)    # 设置遮盖标签的可见性
            self.stackedWidget_encode_status.setCurrentIndex(0)
            self.gui_encode_init_status()

    def gui_encode_set_path_directory(self):
        """ 点击'添加目录'时触发, 可选择多个文件以列表形式添加到输入列表中, 同时初始化Tree结构显示和状态信息 """
        path_input = QFileDialog.getExistingDirectory(self, "Select directory")
        if path_input != "":
            self.encode_PATH_INPUT_OBJECT_LIST.append(path_input)
            self.gui_encode_init_treewidget()                       # 初始化GUI树型显示
            self.pushButton_encode_convert.setEnabled(True)
            self.label_encode_treewidget_cover.setVisible(False)    # 设置遮盖标签的可见性
            self.stackedWidget_encode_status.setCurrentIndex(0)
            self.gui_encode_init_status()

    def gui_encode_set_path_output(self):
        path_input = QFileDialog.getExistingDirectory(self, "Select directory")
        if path_input != "":
            self.encode_path_output = path_input
            self.stackedWidget_encode_status.setCurrentIndex(0)
            self.gui_encode_init_status()

    def gui_encode_set_path_default(self):
        """ 使用缺省路径 """
        config = configparser.ConfigParser()
        config.read('./config.ini', encoding="utf-8-sig")

        path_input_get = config['Encode']['encode_path_input']
        path_output_get = config['Encode']['encode_path_output']
        path_input_exists = Common.check_exists_path(path_input_get)
        path_output_exists = Common.check_exists_path(path_output_get)

        if path_input_exists and path_output_exists:
            if path_input_get.endswith("/"):
                path_input_get = path_input_get[:-1]
            self.encode_PATH_INPUT_OBJECT_LIST.clear()
            self.encode_PATH_INPUT_OBJECT_LIST.append(path_input_get)
            self.encode_path_output = path_output_get
            self.gui_encode_init_treewidget()                       # 初始化GUI树型显示
            self.pushButton_encode_convert.setEnabled(True)
            self.label_encode_treewidget_cover.setVisible(False)    # 设置遮盖标签的可见性
            self.stackedWidget_encode_status.setCurrentIndex(0)
            self.gui_encode_init_status()
        else:
            self.show_message_error_encode_type_01()

    def gui_encode_label_treewidget_cover_dragEnter(self, object_data):
        """ 当执行一个拖曳控件操作，并且鼠标指针进入该控件时，这个事件将会被触发 """
        if object_data.mimeData().hasText():
            object_data.accept()
        else:
            object_data.ignore()

    def gui_encode_label_treewidget_cover_drop(self, object_data):
        """ 当拖曳操作在其目标控件上被释放时，这个事件将被触发 """
        path_sys_object = object_data.mimeData().text()
        self.encode_PATH_INPUT_OBJECT_LIST = path_sys_object.replace("file:///", "").split('\n')
        
        if self.encode_PATH_INPUT_OBJECT_LIST[-1] == "":
            self.encode_PATH_INPUT_OBJECT_LIST.pop()
        self.label_encode_treewidget_cover.setVisible(False)                # 设置遮盖标签的可见性
        self.stackedWidget_encode_status.setCurrentIndex(0)
        self.gui_encode_init_treewidget()                                   # 初始化GUI树型显示
        self.pushButton_encode_convert.setEnabled(True)

    def gui_encode_open_path_output(self):
        # 检查路径是否存在
        if os.path.exists(self.encode_path_output):
            # 使用 os.startfile 打开文件夹
            os.startfile(os.path.abspath(self.encode_path_output))
        else:
            self.show_message_error_encode_type_05()
            print(f"ERROR: Path not found: {self.encode_path_output}")

    # -- ↓页面: 解码部分交互↓ ---------------------------------------------------------------------
    def gui_decode_init(self):
        error_type, mode, frame_size_cut, size_json, frame_start = Automatic.scan_media(self.decode_path_input)   # 扫描输入的媒体文件, 如果成功则返回 裁剪尺寸和json大小, 失败则返回 False 和 None标记
        if error_type == False:
            # 尝试获取文件信息: 视频宽度, 视频高度, 总帧数, 每秒帧数fps, 时长
            self.decode_frame_size_width, self.decode_frame_size_height, self.decode_frame_num_total, \
                self.decode_object_fps, self.decode_object_time_total = Automatic.read_media_info(self.decode_path_input)
            self.decode_mode = mode
            self.decode_frame_size_cut = frame_size_cut
            self.decode_json_size = size_json           # 不能少了这个, 否则输出文件时，裁剪的开始位置会有问题，导致输出的文件故障
            self.decode_frame_start = frame_start
            self.config_init_decode_gui_automatic()     # 更新页面参数设置显示
            self.gui_decode_init_treewidget()           # 更新目录树显示
            self.gui_decode_init_status()               # 更新状态信息

            # 设置遮盖标签的可见性, 以及关闭设置选项等
            self.pushButton_decode_scan.setHidden(True)         # 关闭重新扫描按钮
            self.pushButton_decode_convert.setEnabled(True)
            self.label_decode_treewidget_cover.setVisible(False)
            self.tab_decode_config_1.setEnabled(True)           # 这里设置为开启, 是为了开启 设置CPU核心数选项
            self.tab_decode_config_2.setEnabled(False)
            self.label_decode_mode_text.setEnabled(False)

            if self.decode_mode == 0:
                self.radioButton_decode_mode_0.setCheckable(True)
                self.radioButton_decode_mode_0.setChecked(True)
                self.radioButton_decode_mode_1.setCheckable(False)
                self.radioButton_decode_mode_2.setCheckable(False)
            elif self.decode_mode == 1:
                self.radioButton_decode_mode_1.setCheckable(True)
                self.radioButton_decode_mode_1.setChecked(True)
                self.radioButton_decode_mode_0.setCheckable(False)
                self.radioButton_decode_mode_2.setCheckable(False)
            elif self.decode_mode == 2:
                self.radioButton_decode_mode_2.setCheckable(True)
                self.radioButton_decode_mode_2.setChecked(True)
                self.radioButton_decode_mode_0.setCheckable(False)
                self.radioButton_decode_mode_1.setCheckable(False)
            else:
                print("Unexpected ERROR: [gui_decode_init]--> self.decode_mode value error!")

        else:
            if error_type == 1:
                self.show_message_error_decode_type_01()
            elif error_type == 2:
                self.show_message_error_decode_type_02()
            elif error_type == 3:
                self.show_message_error_decode_type_03()
            elif error_type == 4:
                self.show_message_error_decode_type_04()
            else:
                print("Unexpected ERROR: [gui_decode_init]--> error_type value error!")

            self.config_init_decode_gui_automatic()
            self.pushButton_decode_scan.setHidden(False)        # 显示重新扫描按钮
            self.pushButton_decode_convert.setEnabled(False)
            self.tab_decode_config_1.setEnabled(True)
            self.tab_decode_config_2.setEnabled(True)
            self.label_decode_mode_text.setEnabled(True)
            self.radioButton_decode_mode_0.setEnabled(True)
            self.radioButton_decode_mode_1.setEnabled(True)
            self.radioButton_decode_mode_2.setEnabled(True)

            if self.decode_mode == 0:
                self.radioButton_decode_mode_0.setChecked(True)
            elif self.decode_mode == 1:
                self.radioButton_decode_mode_1.setChecked(True)
            elif self.decode_mode == 2:
                self.radioButton_decode_mode_2.setChecked(True)
            else:
                print("Unexpected ERROR: [gui_decode_init]--> self.decode_mode value error!")

    def gui_decode_init_status(self, display_status_path_input=True):
        """ 初始化显示信息, 输入路径, 输出路径之类的 """
        self.label_decode_status_text1.setVisible(False)
        self.label_decode_status_path_input.setVisible(False)
        if display_status_path_input:
            self.label_decode_status_path_input.setText(self.decode_path_input)
            self.label_decode_status_text1.setVisible(True)
            self.label_decode_status_path_input.setVisible(True)
        self.label_decode_status_path_output.setText(self.decode_path_output)

    def gui_decode_init_treewidget(self):
        """ 初始化GUI上树型组件的信息显示 """
        self.treeWidget_decode.clear()
        json_structure_get = Common.execute_file("./temp/structure_read.json", 0)

        self.gui_build_tree(json_structure_get, self.treeWidget_decode.invisibleRootItem())  # 将json结构显示在 GUI中
    
    def gui_decode_clear(self):
        """ 清除配置 """
        self.treeWidget_decode.clear()
        self.pushButton_decode_convert.setEnabled(False)
        self.label_decode_treewidget_cover.setVisible(True)                # 设置遮盖标签的可见性
        self.label_decode_status_text1.setVisible(False)
        self.label_decode_status_path_input.setVisible(False)
        self.tab_decode_config_1.setEnabled(False)
        self.tab_decode_config_2.setEnabled(False)
            
    def gui_decode_set_path_file(self):
        """ 点击'选择文件'触发, 判断路径是否有效, 如果有效就进行初始化 """
        path_input, obj_type = QFileDialog.getOpenFileName(self, "Select File", "", "Video Media (*.mp4 *.mkv *.mov *.avi *.mpeg *.wmv *.flv *.webm *.ts)")
        if path_input != "":
            self.decode_path_input = path_input
            self.stackedWidget_decode_status.setCurrentIndex(0)     # 切换到进度显示区域
            # 这里使用配置更新锁, 防止识别视频的时候, 页面分辨率更新时自动触发页面刷新, 导致lineEdit_decode_path_input 的显示内容也更新。 这个是输入的默认路径。
            self.CONFIG_UPDATE_LOCK = True
            self.gui_decode_init()      # 这里单独用一个函数来实现初始化\
            self.CONFIG_UPDATE_LOCK = False

    def gui_decode_set_path_output(self):
        path_input = QFileDialog.getExistingDirectory(self, "Select directory")
        if path_input != "":
            self.decode_path_output = path_input
            self.gui_decode_init_status()           # 更新输出路径在GUI上的显示

    def gui_decode_set_path_default(self):
        """ 使用缺省路径 """
        config = configparser.ConfigParser()
        config.read('./config.ini', encoding="utf-8-sig")
        self.decode_path_input = config['Decode']['decode_path_input']
        self.decode_path_output = config['Decode']['decode_path_output']
        self.gui_decode_init()      # 这里单独用一个函数来实现初始化

    def gui_decode_label_treewidget_cover_dragEnter(self, object_data):
        """ 当执行一个拖曳控件操作，并且鼠标指针进入该控件时，这个事件将会被触发 """
        if object_data.mimeData().hasText():
            object_data.accept()
        else:
            object_data.ignore()

    def gui_decode_label_treewidget_cover_drop(self, object_data):
        """ 当拖曳操作在其目标控件上被释放时，这个事件将被触发 """
        path_sys_object = object_data.mimeData().text()
        self.decode_path_input = path_sys_object.replace("file:///", "")    # 去除系统路径中的 file:/// 字符
        self.label_decode_treewidget_cover.setVisible(False)                # 设置遮盖标签的可见性
        self.stackedWidget_decode_status.setCurrentIndex(0)
        self.gui_decode_init()      # 这里单独用一个函数来实现初始化

    def gui_decode_open_path_output(self):
        # 检查路径是否存在
        if os.path.exists(self.decode_path_output):
            # 使用 os.startfile 打开文件夹
            os.startfile(os.path.abspath(self.decode_path_output))
        else:
            self.show_message_error_decode_type_05()
            print(f"ERROR: Path not found: {self.decode_path_output}")

    # -- ↓功能执行↓ ---------------------------------------------------------------------
    def thread_ftv(self):
        """ Start or terminate the FTV module process, and create a thread to update progress information on the GUI. """
        create_cover = Cover(self.version, self.encode_frame_size_width, self.encode_frame_size_height, self.encode_frame_speed_fps, \
                             self.cover_path_image, self.cover_set_description, self.cover_active_display_background, self.cover_active_display_title, \
                             self.cover_active_display_resolution, self.cover_active_display_date, self.cover_active_display_full, self.cover_active_display_description)
        create_cover.create_cover()
        self.stackedWidget_encode_status.setCurrentIndex(1) # 切换到进度显示区域
        self.progressBar_encode.setValue(0)
        self.progressBar_encode.reset()                     # 对进度条进行重置, 不然第二次运行时会闪退报错 QPaintDevice: Cannot destroy paint device that is being painted

        if self.state_pushButton_encode_conversion == 0:
            self.p1 = Process(target=coreFTV.run, 
                         args=(self.encode_PATH_INPUT_OBJECT_LIST, self.encode_path_output, self.encode_mode, self.encode_frame_size_width, self.encode_frame_size_height, \
                               self.encode_frame_size_cut, self.encode_frame_speed_fps, self.fm_encoder_type, self.fm_rate, self.encode_active_cover, self.encode_frame_cover_number, \
                               self.shared_encode_run_count, self.shared_encode_frame_total, self.shared_encode_run_active))
            self.p1.start()
            threading.Thread(target=self.thread_ftv_update).start()
            self.state_pushButton_encode_conversion = 1
            self.pushButton_encode_convert.setText("Stop")
        elif self.state_pushButton_encode_conversion == 1:
            self.p1.terminate()
            self.shared_encode_run_active.value = False
            self.shared_encode_frame_total.value = 0
            self.shared_encode_run_count.value = 0
            self.state_pushButton_encode_conversion = 0
            self.pushButton_encode_convert.setText("Start Conversion")
            self.show_message_info_public_type_02()
        else:
            print("Unexpected Error: [thread_ftv] function has invalid value.")

    def thread_ftv_update(self):
        """ Check the running status of the FTV module every 0.5 seconds and pass the module's running information to the GUI through the QT slot for display. """ 
        time_start = time.time()
        progress_total = self.shared_encode_frame_total.value
        progress_value_record = 0

        while progress_total == 0:
            time.sleep(0.5)
            progress_total = self.shared_encode_frame_total.value

        while self.shared_encode_run_active.value:
            time.sleep(0.5)
            run_count = self.shared_encode_run_count.value
            progress_value = int(run_count / progress_total * 100)
            time_elapsed = round(time.time() - time_start , 1)      # 计算已用时间(秒)
            current_fps = round(run_count / time_elapsed, 2)        # 计算当前FPS速度(秒)

            # 计算剩余时间(秒)
            if progress_value != 0:
                time_remaining = round(time_elapsed * (100 - progress_value) / progress_value, 1)
            else:
                time_remaining = 0

            # 避免频繁因为更新PYQT的进度条, 导致的 QPaintDevice: Cannot destroy paint device that is being painted
            active_refresh_progress_bar = False
            if progress_value != progress_value_record:
                progress_value_record = progress_value
                active_refresh_progress_bar = True

            self.signal.refresh_signal_progress_ftv.emit(progress_total, run_count, progress_value, time_elapsed, time_remaining, current_fps, active_refresh_progress_bar)   # int, int, int, float, float, float, bool

        # 正常的结束传递信号0, 中断的结束传递信号1
        if self.state_pushButton_encode_conversion == 1:
            self.signal.event_signal_finish_ftv.emit(0)
        else:
            self.signal.event_signal_finish_ftv.emit(1)
        self.shared_encode_run_count.value = 0
        self.shared_encode_frame_total.value = 0
        self.state_pushButton_encode_conversion = 0

    def thread_ftv_refresh_gui(self, progress_total, run_count, progress_value, time_elapsed, time_remaining, current_fps, active_refresh_progress_bar):
        """ Refresh the main window progress information. triggered by QT signal."""
        if active_refresh_progress_bar:
            self.progressBar_encode.setValue(progress_value)
            self.progressBar_encode.destroy(progress_value)

        if time_remaining == 0:
            self.label_encode_progress_time_remaining.setText(f"∞ Second")
        else:
            self.label_encode_progress_time_remaining.setText(f"{time_remaining} Second")

        self.label_encode_progress_time_elapsed.setText(f"{time_elapsed} Second")
        self.label_encode_progress_value.setText(f"{run_count} / {progress_total}")
        self.label_encode_progress_speed.setText(f"{current_fps} FPS")

    def thread_ftv_finish(self, status_value):
        """ VTF module finish event. triggered by QT signal."""
        Common.sys_clear_directory("./temp/")       # 清空temp目录

        # status_value 的值, 0代表正常结束, 1代表中断结束
        if status_value == 0:
            self.show_message_info_encode_type_01()
            self.pushButton_encode_convert.setText("Start Conversion")
        elif status_value == 1:
            self.pushButton_encode_convert.setText("Start Conversion")
        else:
            print("Unexpected Error: [thread_ftv_finish] function has invalid value.")

    def thread_vtf(self):
        """ Start or terminate the VTF module process, and create a thread to update progress information on the GUI. """
        self.shared_decode_run_count = Value('i', 0)    # 解码的运行计数的初始化。因为在 __init__中好像不执行, 所以放在这里
        self.shared_decode_run_count.value = 0
        self.shared_decode_run_active.value = True
        self.progressBar_decode.setValue(0)
        self.progressBar_decode.reset()                 # 对进度条进行重置, 不然第二次运行时会闪退报错 QPaintDevice: Cannot destroy paint device that is being painted

        if self.state_pushButton_decode_conversion == 0:
            self.stackedWidget_decode_status.setCurrentIndex(1)
            self.process_decode = Process(target=coreVTF.run, \
                                          args=(self.decode_path_input, self.decode_path_output, self.decode_mode, self.decode_frame_size_cut, self.decode_frame_start, \
                                                self.decode_process_num, self.decode_json_size, self.shared_decode_run_count, self.shared_decode_run_active))
            self.process_decode.start()
            threading.Thread(target=self.thread_vtf_update).start()
            self.state_pushButton_decode_conversion = 1
            self.pushButton_decode_convert.setText("Stop")
        elif self.state_pushButton_decode_conversion == 1:
            # self.process_decode.terminate()
            self.shared_decode_run_active.value = False
            self.shared_decode_run_count.value = 0
            self.state_pushButton_decode_conversion = 0
            self.pushButton_decode_convert.setText("Start Conversion")
            self.show_message_info_public_type_02()
        else:
            print("Unexpected Error: [thread_vtf] function has invalid value.")

    def thread_vtf_update(self):
        """ Check the running status of the VTF module every 0.5 seconds and pass the module's running information to the GUI through the QT slot for display. """
        if self.decode_mode == 0:
            frame_bytes_size = int((self.decode_frame_size_width * self.decode_frame_size_height) / (self.decode_frame_size_cut ** 2))
        elif self.decode_mode == 1:
            frame_bytes_size = int((self.decode_frame_size_width * self.decode_frame_size_height) / (self.decode_frame_size_cut ** 2) * 3)
        elif self.decode_mode == 2:
            frame_bytes_size = int((self.decode_frame_size_width * self.decode_frame_size_height) / (self.decode_frame_size_cut ** 2) * 6)
        else:
            print("Unexpected Error: [thread_vtf_update] function has invalid value.")
        time_start = time.time()
        progress_total = self.decode_frame_num_total - self.decode_frame_start
        progress_value_record = 0

        while self.shared_decode_run_active.value:
            time.sleep(0.5)
            run_count = self.shared_decode_run_count.value
            progress_value = int(run_count / progress_total * 100)  # 计算当前进度值(百分比)
            time_elapsed = round(time.time() - time_start , 1)      # 计算已用时间(秒)
            current_fps = round(run_count / time_elapsed, 2)                            # 计算当前FPS速度(秒)
            current_rate = round(run_count * frame_bytes_size / 8192 / time_elapsed, 2) # 计算当前数据速率(KB/s)

            # 计算剩余时间(秒)
            if progress_value != 0:
                time_remaining = round(time_elapsed * (100 - progress_value) / progress_value, 1)
            else:
                time_remaining = 0

            # 避免频繁因为更新PYQT的进度条, 导致的 QPaintDevice: Cannot destroy paint device that is being painted
            active_refresh_progress_bar = False
            if progress_value != progress_value_record:
                progress_value_record = progress_value
                active_refresh_progress_bar = True

            self.signal.refresh_signal_progress_vtf.emit(progress_total, run_count, progress_value, time_elapsed, time_remaining, current_fps, current_rate, active_refresh_progress_bar)   # int, int, int, float, float, float, float, bool

        # 正常的结束传递信号0, 中断的结束传递信号1
        if self.state_pushButton_decode_conversion == 1:
            self.signal.event_signal_finish_vtf.emit(0)
        else:
            self.signal.event_signal_finish_vtf.emit(1)
        self.shared_decode_run_count.value = 0
        self.shared_decode_run_active.value = False
        self.state_pushButton_decode_conversion = 0

    def thread_vtf_refresh_gui(self, progress_total, run_count, progress_value, time_elapsed, time_remaining, current_fps, current_rate, active_refresh_progress_bar):
        """ Refresh the main window progress information. triggered by QT signal."""
        if active_refresh_progress_bar:
            self.progressBar_decode.setValue(progress_value)
            self.progressBar_decode.destroy(progress_value)

        if time_remaining == 0:
            self.label_decode_progress_time_remaining.setText(f"∞ Second")
        else:
            self.label_decode_progress_time_remaining.setText(f"{time_remaining} Second")

        self.label_decode_progress_time_elapsed.setText(f"{time_elapsed} Second")
        self.label_decode_progress_value.setText(f"{run_count} / {progress_total}")
        self.label_decode_progress_speed.setText(f"{current_fps} FPS   {current_rate} KB/s")   

    def thread_vtf_finish(self, status_value):
        """ VTF module finish event. triggered by QT signal."""
        Common.sys_clear_directory("./temp/")       # 清空temp目录
        
        # status_value 的值, 0代表正常结束, 1代表中断结束
        if status_value == 0:
            self.show_message_info_decode_type_01()
            self.pushButton_decode_convert.setText("Start Conversion")
        elif status_value == 1:
            self.pushButton_decode_convert.setText("Start Conversion")
        else:
            print("Unexpected Error: [thread_vtf_finish] function has invalid value.")

    def window_cover_open(self):
        """ 打开Cover子窗口. """
        self.window_cover = QTWindowCover(self.version, self.encode_frame_size_width, self.encode_frame_size_height, self.encode_frame_speed_fps, \
                             self.cover_path_image, self.cover_set_description, self.cover_active_display_background, self.cover_active_display_title, \
                             self.cover_active_display_resolution, self.cover_active_display_date, self.cover_active_display_full, self.cover_active_display_description)
        self.window_cover.show()
        self.window_cover.data_signal.connect(self.window_cover_get_data)       # 接收子窗口信号的槽

    def window_cover_get_data(self, path_image, set_description, active_display_background, active_display_title, active_display_resolution, active_display_date, active_display_full, active_display_description):
        """ 接收Cover子窗口的回传数据. """
        self.cover_path_image = path_image
        self.cover_set_description = set_description
        self.cover_active_display_background = active_display_background
        self.cover_active_display_title = active_display_title
        self.cover_active_display_resolution = active_display_resolution
        self.cover_active_display_date = active_display_date
        self.cover_active_display_full = active_display_full
        self.cover_active_display_description = active_display_description


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    window = QTWindow()
    window.show()
    sys.exit(app.exec())
