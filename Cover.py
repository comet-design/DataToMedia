import cv2
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import pyqtSignal
from QTUI.QTGuiCover import Ui_Form

class Cover:
    """Cover Class: This class receives the parameters for creating a cover image. By calling the 'create_cover' function within this class, a cover image is created and written to the cache directory for use during video regeneration."""
    def __init__(self, program_version, target_width, target_height, fps, path_image, set_description, active_display_background, active_display_title, active_display_resolution, active_display_date, active_display_full, active_display_description):
        self.set_width = target_width
        self.set_height = target_height
        self.set_fps = fps
        self.set_description = set_description
        self.set_version = program_version
        self.set_text_size = round(self.set_width / 480, 1)
        self.set_text_thickness_type1 = int(self.set_width / 80)
        self.set_text_thickness_type2 = int(self.set_width / 320)
        self.path_image = path_image
        self.active_display_background = active_display_background
        self.active_display_title = active_display_title
        self.active_display_resolution = active_display_resolution
        self.active_display_date = active_display_date
        self.active_display_full = active_display_full
        self.active_display_description = active_display_description

    def create_cover(self):
        """Generate a cover image in the directory location './temp/cover.png'"""
        # 生成シ间
        current_time = datetime.now()
        formatted_time = current_time.strftime('%Y/%m/%d %H:%M')

        # イヘ　设ゼ了背景
        if self.active_display_background:
            data = np.fromfile(self.path_image, dtype=np.uint8)
            image_raw = cv2.imdecode(data, cv2.IMREAD_COLOR)
            img_width, img_height = image_raw.shape[1], image_raw.shape[0]
            width, height = self.set_width, self.set_height

            # イヘモ　拉伸背景
            if self.active_display_full == False:

                # イヘ　输入ゴ图片ゴ宽ガア高，都　タイ于　ドン前チ寸ゴ　情况
                if img_width >= width and img_height >= height:
                    scale = img_height / height                     # アゴ　随便用一条短ゴ边，ホチ　用width应该也　コ以
                    resize_width = int(img_width / scale)
                    resize_height = height
                    # イヘ　重设ゴ图片ゴ宽，タイ于　ドン前チ寸
                    if resize_width > width:
                        scale = resize_width / width
                        resize_width = int(resize_width / scale)
                        resize_height = int(resize_height / scale)

                # イヘ　只有输入ゴ图片ゴ宽，タイ于　ドン前チ寸ゴ　情况
                elif img_width >= width and img_height < height:
                    scale = img_width / width
                    resize_width = width
                    resize_height = int(img_height / scale)

                # イヘ　输入ゴ图片ゴ宽ガア高，都小于当前チ寸ゴ情况
                elif img_width < width and img_height >= height:
                    scale = img_height / height
                    resize_width = int(img_width / scale)
                    resize_height = height

                elif img_width < width and img_height < height:
                    scale = img_height / height
                    resize_width = int(img_width / scale)
                    resize_height = height
                    # イヘ　重设ゴ图片ゴ宽，タイ于当前チ寸
                    if resize_width > width:
                        scale = resize_width / width
                        resize_width = int(resize_width / scale)
                        resize_height = int(resize_height / scale)

                else:
                    print("Unexpected ERROR: [Cover]--> Invalid value")

                image_raw_resize = cv2.resize(image_raw, (resize_width, resize_height), interpolation=cv2.INTER_LINEAR)
                image = np.zeros((height, width, 3), dtype=np.uint8)        # 创ゲン　一个 1280x720 ゴ　黑色背影图像
                start_y = (height - resize_height) // 2                     # ギ算图像粘贴位ジゴ　起始点
                start_x = (width - resize_width) // 2
                image[start_y:start_y + resize_height, start_x:start_x + resize_width] = image_raw_resize       # バ　缩放后ゴ　图像粘贴ド　背影图像ゴ　中ガン
            
            else:
                image = cv2.resize(image_raw, (width, height), interpolation=cv2.INTER_LINEAR)      # 直接　ライ伸　图片

        else:
            image = np.zeros((self.set_height, self.set_width, 3), dtype=np.uint8)    # 创建一个空白图像

            # 生成　ラア白渐变背景ゴ　ス值
            for i in range(self.set_height):
                color = (150, 255 * i // self.set_height, 255 * i // self.set_height)
                image[i, :] = color

        if self.active_display_title:
            # cv2.putText() Parameters: image, text, position, font, font_scale, font_color, thickness
            cv2.putText(image, "Data Media", (0, int(self.set_width * 0.07)), cv2.FONT_HERSHEY_SIMPLEX, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, "Data Media", (0, int(self.set_width * 0.07)), cv2.FONT_HERSHEY_SIMPLEX, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

            cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.80), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.80), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)
            # cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.85), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            # cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.85), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_resolution:
            cv2.putText(image, f"{self.set_width} x {self.set_height} @{self.set_fps}fps", (0, int(self.set_width * 0.13)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_width} x {self.set_height} @{self.set_fps}fps", (0, int(self.set_width * 0.13)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_date:
            cv2.putText(image, f"{formatted_time}", (0, int(self.set_width * 0.18)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{formatted_time}", (0, int(self.set_width * 0.18)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_description:
            cv2.putText(image, "description:", (0, int(self.set_height * 0.92)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, "description:", (0, int(self.set_height * 0.92)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)
            cv2.putText(image, f"{self.set_description}", (0, int(self.set_height * 0.98)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_description}", (0, int(self.set_height * 0.98)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        cv2.imwrite('./temp/cover.png', image)


class QTWindowCover(QMainWindow, Ui_Form):
    """QT Window Class: This class displays a sub-window for previewing cover images, setting and adjusting image parameters, and passing the configured parameters to the main window."""
    data_signal = pyqtSignal(str, str, bool, bool, bool, bool, bool, bool)

    def __init__(self, program_version, target_width, target_height, fps, path_image, set_description, active_display_background, active_display_title, active_display_resolution, active_display_date, active_display_full, active_display_description):
        super().__init__()
        Ui_Form.__init__(self)
        self.setupUi(self)
        self.set_width = target_width
        self.set_height = target_height
        self.set_fps = fps
        self.set_description = set_description
        self.set_version = program_version
        self.set_text_size = round(self.set_width / 480, 1)
        self.set_text_thickness_type1 = int(self.set_width / 80)
        self.set_text_thickness_type2 = int(self.set_width / 320)
        self.path_image = path_image
        self.active_display_background = active_display_background
        self.active_display_title = active_display_title
        self.active_display_resolution = active_display_resolution
        self.active_display_date = active_display_date
        self.active_display_full = active_display_full
        self.active_display_description = active_display_description
        self.initUI()

    def initUI(self):
        self.pushButton_set_image.clicked.connect(self.get_path_image)
        self.pushButton_clear.clicked.connect(self.clear_display_background)
        self.pushButton_cancel.clicked.connect(self.close)
        self.pushButton_ok.clicked.connect(self.window_send_data)
        self.checkBox_display_title.clicked.connect(self.update_display_title)
        self.checkBox_display_resolution.clicked.connect(self.update_display_resolution)
        self.checkBox_display_date.clicked.connect(self.update_display_date)
        self.checkBox_display_full.clicked.connect(self.update_display_full)
        self.lineEdit_display_description.textChanged.connect(self.update_display_description)

        if self.active_display_title:
            self.checkBox_display_title.setChecked(True)
        else:
            self.checkBox_display_title.setChecked(False)

        if self.active_display_resolution:
            self.checkBox_display_resolution.setChecked(True)
        else:
            self.checkBox_display_resolution.setChecked(False)

        if self.active_display_date:
            self.checkBox_display_date.setChecked(True)
        else:
            self.checkBox_display_date.setChecked(False)

        if self.active_display_full:
            self.checkBox_display_full.setChecked(True)
        else:
            self.checkBox_display_full.setChecked(False)

        self.create_cover()

    def get_path_image(self):
        """ Triggered by 'Select File', it checks whether the path is valid. If valid, it proceeds with initialization. """
        path_input, obj_type = QFileDialog.getOpenFileName(self, "Select File", "", "PNG Image (*.png);;JPG Image (*.jpg);;JPGE Image (*.jpge)")
        if path_input != "":
            self.path_image = path_input
            self.active_display_background = True
            self.create_cover()
      
    def create_cover(self):
        """ Generate a preview of the cover image and display it. """
        # 生成シ间
        current_time = datetime.now()
        formatted_time = current_time.strftime('%Y/%m/%d %H:%M')

        # イヘ　设ゼ了背景
        if self.active_display_background:
            data = np.fromfile(self.path_image, dtype=np.uint8)
            image_raw = cv2.imdecode(data, cv2.IMREAD_COLOR)
            img_width, img_height = image_raw.shape[1], image_raw.shape[0]
            width, height = self.set_width, self.set_height

            # イヘモ　拉伸背景
            if self.active_display_full == False:

                # イヘ　输入ゴ图片ゴ宽ガア高，都　タイ于　ドン前チ寸ゴ　情况
                if img_width >= width and img_height >= height:
                    scale = img_height / height                     # アゴ　随便用一条短ゴ边，ホチ　用width应该也　コ以
                    resize_width = int(img_width / scale)
                    resize_height = height
                    # イヘ　重设ゴ图片ゴ宽，タイ于　ドン前チ寸
                    if resize_width > width:
                        scale = resize_width / width
                        resize_width = int(resize_width / scale)
                        resize_height = int(resize_height / scale)

                # イヘ　只有输入ゴ图片ゴ宽，タイ于　ドン前チ寸ゴ　情况
                elif img_width >= width and img_height < height:
                    scale = img_width / width
                    resize_width = width
                    resize_height = int(img_height / scale)

                # イヘ　输入ゴ图片ゴ宽ガア高，都小于当前チ寸ゴ情况
                elif img_width < width and img_height >= height:
                    scale = img_height / height
                    resize_width = int(img_width / scale)
                    resize_height = height

                elif img_width < width and img_height < height:
                    scale = img_height / height
                    resize_width = int(img_width / scale)
                    resize_height = height
                    # イヘ　重设ゴ图片ゴ宽，タイ于当前チ寸
                    if resize_width > width:
                        scale = resize_width / width
                        resize_width = int(resize_width / scale)
                        resize_height = int(resize_height / scale)

                else:
                    print("Unexpected ERROR: [Cover]--> Invalid value")

                image_raw_resize = cv2.resize(image_raw, (resize_width, resize_height), interpolation=cv2.INTER_LINEAR)
                image = np.zeros((height, width, 3), dtype=np.uint8)        # 创ゲン　一个 1280x720 ゴ　黑色背影图像
                start_y = (height - resize_height) // 2                     # ギ算图像粘贴位ジゴ　起始点
                start_x = (width - resize_width) // 2
                image[start_y:start_y + resize_height, start_x:start_x + resize_width] = image_raw_resize       # バ　缩放后ゴ　图像粘贴ド　背影图像ゴ　中ガン
            
            else:
                image = cv2.resize(image_raw, (width, height), interpolation=cv2.INTER_LINEAR)      # 直接　ライ伸　图片

        else:
            image = np.zeros((self.set_height, self.set_width, 3), dtype=np.uint8)    # 创建一个空白图像

            # 生成　ラア白渐变背景ゴ　ス值
            for i in range(self.set_height):
                color = (150, 255 * i // self.set_height, 255 * i // self.set_height)
                image[i, :] = color

        if self.active_display_title:
            # cv2.putText() Parameters: image, text, position, font, font_scale, font_color, thickness
            cv2.putText(image, "Data Media", (0, int(self.set_width * 0.07)), cv2.FONT_HERSHEY_SIMPLEX, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, "Data Media", (0, int(self.set_width * 0.07)), cv2.FONT_HERSHEY_SIMPLEX, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

            cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.80), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.80), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)
            # cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.85), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            # cv2.putText(image, f"{self.set_version}", (int(self.set_width * 0.85), int(self.set_width * 0.07)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_resolution:
            cv2.putText(image, f"{self.set_width} x {self.set_height} @{self.set_fps}fps", (0, int(self.set_width * 0.13)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_width} x {self.set_height} @{self.set_fps}fps", (0, int(self.set_width * 0.13)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_date:
            cv2.putText(image, f"{formatted_time}", (0, int(self.set_width * 0.18)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{formatted_time}", (0, int(self.set_width * 0.18)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        if self.active_display_description:
            cv2.putText(image, "description:", (0, int(self.set_height * 0.92)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, "description:", (0, int(self.set_height * 0.92)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)
            cv2.putText(image, f"{self.set_description}", (0, int(self.set_height * 0.98)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (0, 0, 0), self.set_text_thickness_type1, cv2.LINE_AA) 
            cv2.putText(image, f"{self.set_description}", (0, int(self.set_height * 0.98)), cv2.FONT_HERSHEY_PLAIN, self.set_text_size, (255, 255, 255), self.set_text_thickness_type2, cv2.LINE_AA)

        q_image = QImage(image.data, image.shape[1], image.shape[0], QImage.Format.Format_BGR888)
        self.label_image.setPixmap(QPixmap.fromImage(q_image))
        self.label_image.setScaledContents(True)

    def clear_display_background(self):
        self.active_set_background = False
        self.create_cover()

    def update_display_title(self):
        if self.checkBox_display_title.isChecked():
            self.active_display_title = True
        else:
            self.active_display_title = False
        self.create_cover()

    def update_display_resolution(self):
        if self.checkBox_display_resolution.isChecked():
            self.active_display_resolution = True
        else:
            self.active_display_resolution = False
        self.create_cover()

    def update_display_date(self):
        if self.checkBox_display_date.isChecked():
            self.active_display_date = True
        else:
            self.active_display_date = False
        self.create_cover()

    def update_display_full(self):
        if self.checkBox_display_full.isChecked():
            self.active_display_full = True
        else:
            self.active_display_full = False
        self.create_cover()

    def update_display_description(self):
        if self.lineEdit_display_description.text() != "":
            self.active_display_description = True
            self.set_description = self.lineEdit_display_description.text()
        else:
            self.active_display_description = False
            self.set_description = ""
        self.create_cover()

    def window_send_data(self):
        self.data_signal.emit(self.path_image, self.set_description, self.active_display_background, self.active_display_title, self.active_display_resolution, \
                              self.active_display_date, self.active_display_full, self.active_display_description)
        self.close()
