AppStyle = """
            QMainWindow, QWidget {
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 14px;
                color: #ffffff;
                background-color: #000000;
            }            
            QLabel#MainTitle {
                color: #dc2626;
                font-size: 32px;
                font-weight: 800;
                letter-spacing: -0.5px;
                text-align: center;
                background: transparent;
            }            
            QLabel#CompanyName {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                text-align: center;
                background: transparent;
            }            
            QLabel#ProductName {
                color: #dc2626;
                font-size: 20px;
                font-weight: 600;
                text-align: center;
                background: transparent;
            }            
            QLabel#ProductDesc {
                color: #cccccc;
                font-size: 14px;
                font-weight: 400;
                text-align: center;
                background: transparent;
            }            
            QLabel#SubTitleLabel {
                color: #cccccc;
                font-size: 12px;
                font-weight: 400;
                margin-bottom: 15px;
                text-align: center;
                background: transparent;
            }            
            QLabel#PythonLogo {
                background: transparent;
                border: none;
            }            
            QGroupBox {
                border: 2px solid #dc2626;
                border-radius: 8px;
                padding: 15px;
                background-color: #1a1a1a;
                margin-top: 8px;
                font-weight: 700;
                color: #ffffff;
            }            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: #dc2626;
                font-weight: 700;
                font-size: 14px;
                background-color: #1a1a1a;
            }            
            QComboBox {
                background-color: #000000;
                border: 2px solid #dc2626;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
                min-width: 100px;
                color: #ffffff;
                font-size: 13px;
                min-height: 20px;
            }            
            QComboBox:focus {
                border-color: #b91c1c;
                outline: none;
            }            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #dc2626;
                border-radius: 0px;
            }            
            QComboBox QAbstractItemView {
                background-color: #000000;
                border: 2px solid #dc2626;
                color: #ffffff;
                selection-background-color: #dc2626;
                selection-color: #ffffff;
                outline: none;
                padding: 4px;
            }            
            QComboBox QAbstractItemView::item {
                padding: 6px 8px;
                border-radius: 4px;
            }            
            QComboBox QAbstractItemView::item:selected {
                background-color: #dc2626;
                color: #ffffff;
            }            
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 700;
                font-size: 14px;
                letter-spacing: 0.3px;
                min-height: 20px;
            }            
            QPushButton:hover {
                background-color: #b91c1c;
            }            
            QPushButton:pressed {
                background-color: #991b1b;
            }            
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }            
            QProgressBar {
                border: 2px solid #dc2626;
                border-radius: 6px;
                background-color: #000000;
                text-align: center;
                color: #ffffff;
                font-weight: 600;
                height: 25px;
                font-size: 12px;
            }            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc2626, stop:1 #b91c1c);
                border-radius: 4px;
            }            
            QLabel {
                background: transparent;
                color: #ffffff;
            }
        """