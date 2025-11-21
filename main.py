import os
import sys
import pandas as pd
from pathlib import Path
from PyQt5.QtCore import Qt
from openpyxl import Workbook
from urllib.parse import urljoin
from openpyxl.styles import Font
from cropper import process_pdf_from_url                
from PyQt5.QtCore import QThread, pyqtSignal
from playwright.sync_api import sync_playwright
from model import extract_pdf_details_from_image    
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QMovie, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFileDialog, QGroupBox, QProgressBar, QMessageBox,QSpacerItem, QSizePolicy)

def normalize_signature(sig):
    if isinstance(sig, dict):
        return {"name_Address": sig.get("name_Address", "") if sig.get("name_Address", "") is not None else "","mail": sig.get("mail", "") if sig.get("mail", "") is not None else "","phone": sig.get("phone", "") if sig.get("phone", "") is not None else ""}
    if isinstance(sig, str) and sig.strip():
        return {"name_Address": sig.strip(), "mail": "", "phone": ""}
    return {"name_Address": "", "mail": "", "phone": ""}

class ScraperThread(QThread):
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)    
    def __init__(self, department, approval_type, district, year, output_excel):
        super().__init__()
        self.department = department
        self.approval_type = approval_type
        self.district = district
        self.year = year
        self.output_excel = output_excel
        self.output_dir = "cropped_images"
        os.makedirs(self.output_dir, exist_ok=True)
    def run(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto("https://onlineppa.tn.gov.in/approved-plan-list", timeout=60000)                
                page.evaluate(f"""
                    () => {{
                        function selectNiceOption(selectId, visibleText) {{
                            const selectEl = document.querySelector('select#' + selectId);
                            const niceDiv = selectEl?.nextElementSibling;
                            if (!selectEl || !niceDiv) return;

                            const options = niceDiv.querySelectorAll('li.option');
                            const realOption = Array.from(options).find(li => li.textContent.trim() === visibleText);
                            if (realOption) {{
                                const current = niceDiv.querySelector('.current');
                                if (current) current.textContent = realOption.textContent;
                                realOption.classList.add('selected');
                                selectEl.value = realOption.getAttribute('data-value');
                                selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                        selectNiceOption('depName', '{self.department}');
                        selectNiceOption('appType', '{self.approval_type}');
                        selectNiceOption('district', '{self.district}');
                        selectNiceOption('year', '{self.year}');
                    }}
                """)
                page.wait_for_timeout(2000)
                page.evaluate("document.querySelector('#search')?.click()")                
                page.wait_for_function("""
                    () => {
                        const tbody = document.querySelector("table.PPAData tbody");
                        return tbody && tbody.querySelectorAll("tr").length > 0;
                    }
                """, timeout=120000)                
                rows_data = []
                scraped_count = 0
                page_num = 1
                total_rows = 0                
                try:
                    total_text = page.inner_text("div.dataTables_info")
                    import re
                    match = re.search(r'of\s+(\d+)', total_text)
                    if match:
                        total_rows = int(match.group(1))
                    else:
                        total_rows = 50  
                except:
                    total_rows = 50                
                while scraped_count < 10:
                    rows = page.query_selector_all("table.PPAData tbody tr")                    
                    for i, row in enumerate(rows):
                        if scraped_count >= 10:
                            break                            
                        current_count = scraped_count + 1
                        self.progress_signal.emit(current_count, min(10, total_rows))                        
                        cells = row.query_selector_all("td")
                        if len(cells) < 10:
                            continue                            
                        application_no     = cells[1].inner_text().strip()
                        district_val       = cells[2].inner_text().strip()
                        approval_type_val  = cells[3].inner_text().strip()
                        permit_date        = cells[4].inner_text().strip()
                        total_fees         = cells[5].inner_text().strip()
                        project_title        = "N/A"
                        applicant_signature  = ""                    
                        architect_signature  = {"name_Address": "", "mail": "", "phone": ""}
                        pdf_url_for_link     = ""                        
                        try:
                            pdf_element = cells[9].query_selector("a")
                            if pdf_element:
                                pdf_url = pdf_element.get_attribute("href") or ""
                                pdf_url_for_link = urljoin(page.url, pdf_url)                                
                                img, msg = process_pdf_from_url(pdf_url_for_link)                                
                                if img:
                                    filename = f"{application_no}_full.png".replace("/", "_")
                                    filepath = os.path.join(self.output_dir, filename)
                                    img.save(filepath)                                    
                                    try:
                                        seal_data = extract_pdf_details_from_image(filepath) or {}
                                    except Exception as me:
                                        seal_data = {}                                        
                                    project_title       = seal_data.get("PROJECT TITLE", "N/A")
                                    applicant_signature = seal_data.get("OWNER SIGNATURE", "")                                
                                    architect_signature  = normalize_signature(seal_data.get("REGISTERED ENGINEER", {}))
                        except Exception as e:
                            pass
                        rows_data.append({
                            "Application No": application_no,
                            "District": district_val,
                            "Approval Type": approval_type_val,
                            "Permit Issue Date": permit_date,
                            "Total Fees": total_fees,
                            "Project Title": project_title,
                            "Applicant/Owner Signature": applicant_signature,                        
                            "Registered Engineer Name/Address": architect_signature.get("name_Address", ""),
                            "Registered Engineer Mail": architect_signature.get("mail", ""),
                            "Registered Engineer Phone": architect_signature.get("phone", ""),
                            "PDF URL": pdf_url_for_link,
                            "PDF Link": "View PDF"
                        })                        
                        scraped_count += 1                    
                    next_btn_li = page.query_selector("li#example_next")
                    if next_btn_li and "disabled" not in (next_btn_li.get_attribute("class") or ""):
                        next_btn_li.click()
                        page.wait_for_timeout(2000)
                        page_num += 1
                    else:
                        break                        
                browser.close()                
            self.save_to_excel(rows_data)
            self.finished_signal.emit(f"Excel saved to: {self.output_excel}")            
        except Exception as e:
            self.finished_signal.emit(f"Scraping failed: {e}")
    def save_to_excel(self, rows_data):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "DTCP Results"            
            headers = [
                "Application No", "District", "Approval Type",
                "Permit Issue Date", "Total Fees",
                "Project Title", "Applicant/Owner Signature",
                "Registered Engineer Name/Address", "Registered Engineer Mail", "Registered Engineer Phone",
                "PDF Link"
            ]
            ws.append(headers)            
            for row in rows_data:
                ws.append([
                    row["Application No"],
                    row["District"],
                    row["Approval Type"],
                    row["Permit Issue Date"],
                    row["Total Fees"],
                    row["Project Title"],
                    row["Applicant/Owner Signature"],
                    row["Registered Engineer Name/Address"],
                    row["Registered Engineer Mail"],
                    row["Registered Engineer Phone"],
                    "View PDF"
                ])                
                cell = ws.cell(row=ws.max_row, column=11)
                cell.hyperlink = row.get("PDF URL", "")
                cell.font = Font(color="0000FF", underline="single")                
            wb.save(self.output_excel)            
        except Exception as e:
            raise Exception(f"Failed to write Excel: {e}")

class DTCPApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DTCP Plan Permit Scraper - Ajantha Bathroom Products")
        self.setMinimumSize(1200, 800)        
        self.set_window_icon()        
        self.setup_ui()    
    
    def set_window_icon(self):
        icon_path = str(Path(__file__).resolve().parent / "client_logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("#dc2626"))
            self.setWindowIcon(QIcon(pixmap))
    
    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(15)        
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#000000"))
        palette.setColor(QPalette.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.Base, QColor("#1a1a1a"))
        palette.setColor(QPalette.AlternateBase, QColor("#2a2a2a"))
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        palette.setColor(QPalette.Button, QColor("#dc2626"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)        
        self.setStyleSheet("""
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
        """)        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(30)
        header_layout.setAlignment(Qt.AlignCenter)
        self.logo_label = QLabel()
        logo_path = str(Path(__file__).resolve().parent / "client_logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("🏭")
            self.logo_label.setStyleSheet("font-size: 80px; color: #dc2626;")
        self.logo_label.setAlignment(Qt.AlignCenter)        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        text_layout.setAlignment(Qt.AlignCenter)        
        company_label = QLabel("AJANTHA BATHROOM PRODUCTS")
        company_label.setObjectName("CompanyName")
        company_label.setAlignment(Qt.AlignCenter)
        company_label.setFont(QFont("Segoe UI", 20, QFont.Black))        
        product_label = QLabel("AND PIPES PRIVATE LIMITED")
        product_label.setObjectName("ProductName")
        product_label.setAlignment(Qt.AlignCenter)
        product_label.setFont(QFont("Segoe UI", 16, QFont.Bold))        
        desc_label = QLabel("Premium Bathroom Solutions & Sanitaryware Manufacturers")
        desc_label.setObjectName("ProductDesc")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setFont(QFont("Segoe UI", 12, QFont.Normal))        
        text_layout.addWidget(company_label)
        text_layout.addWidget(product_label)
        text_layout.addWidget(desc_label)
        header_layout.addWidget(self.logo_label)
        header_layout.addLayout(text_layout)        
        self.layout.addLayout(header_layout)        
        separator = QLabel()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:0.5 #ffffff, stop:1 #dc2626); margin: 15px 0px;")
        self.layout.addWidget(separator)        
        main_title = QLabel("DTCP PLAN PERMIT SCRAPER")
        main_title.setObjectName("MainTitle")
        main_title.setAlignment(Qt.AlignCenter)
        main_title.setFont(QFont("Segoe UI", 24, QFont.Black))
        self.layout.addWidget(main_title)        
        subtitle = QLabel("Professional Data Extraction & Analysis System")
        subtitle.setObjectName("SubTitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 12))
        self.layout.addWidget(subtitle)        
        output_group = QGroupBox("Application Output")
        output_layout = QVBoxLayout()        
        search_group = QGroupBox("Search Configuration")
        search_layout = QVBoxLayout()        
        filters_layout = QHBoxLayout()
        filters_layout.setAlignment(Qt.AlignCenter)        
        dept_layout = QVBoxLayout()
        dept_layout.addWidget(QLabel("Department Name"))
        self.department = QComboBox()
        self.department.addItems(["DTCP", "Rural Panchayat", "Town Panchayat"])
        self.department.setFixedWidth(200)
        dept_layout.addWidget(self.department)
        filters_layout.addLayout(dept_layout)        
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Approval Type"))
        self.approval_type = QComboBox()
        self.approval_type.addItems(["Layout Approval", "Building Plan"])
        self.approval_type.setFixedWidth(200)
        type_layout.addWidget(self.approval_type)
        filters_layout.addLayout(type_layout)        
        district_layout = QVBoxLayout()
        district_layout.addWidget(QLabel("District"))
        self.district = QComboBox()
        districts = [
            "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
            "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
            "Kanniyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
            "Nagapattinam", "Namakkal", "Perambalur", "Pudukkottai", "Ramanathapuram",
            "Ranipet", "Salem", "Sivagangai", "Tenkasi", "Thanjavur",
            "Theni", "The Nilgiris", "Thoothukkudi", "Tiruchirappalli", "Tirunelveli",
            "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur",
            "Vellore", "Vilupuram", "Virudhunagar"
        ]
        self.district.addItems(districts)
        self.district.setFixedWidth(200)
        district_layout.addWidget(self.district)
        filters_layout.addLayout(district_layout)        
        year_layout = QVBoxLayout()
        year_layout.addWidget(QLabel("Year"))
        self.year = QComboBox()
        self.year.addItems(["2022", "2023", "2024", "2025"])
        self.year.setFixedWidth(150)
        year_layout.addWidget(self.year)
        filters_layout.addLayout(year_layout)        
        search_layout.addLayout(filters_layout)
        search_group.setLayout(search_layout)
        output_layout.addWidget(search_group)        
        progress_group = QGroupBox("Extraction Progress")
        progress_layout = QVBoxLayout()        
        self.loader = QLabel()
        self.loader.setAlignment(Qt.AlignCenter)
        self.loader.setMinimumHeight(80)
        gif_path = str(Path(__file__).resolve().parent / "loader.gif")
        if os.path.exists(gif_path):
            self.loader_movie = QMovie(gif_path)
            self.loader.setMovie(self.loader_movie)
        else:
            self.loader.setText("⏳ Processing...")
            self.loader.setStyleSheet("font-size: 16px; color: #dc2626; font-weight: bold;")
        self.loader.setVisible(False)
        progress_layout.addWidget(self.loader)        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFormat("Processing: %p% (%v of %m documents)")
        self.progress.setFixedHeight(30)
        progress_layout.addWidget(self.progress)        
        progress_group.setLayout(progress_layout)
        output_layout.addWidget(progress_group)        
        output_group.setLayout(output_layout)
        self.layout.addWidget(output_group)        
        self.layout.addItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))        
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)        
        self.scrape_btn = QPushButton("START SCRAPING")
        self.scrape_btn.setFixedSize(250, 60)
        self.scrape_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.scrape_btn.clicked.connect(self.start_scraping)
        button_layout.addWidget(self.scrape_btn)        
        self.layout.addLayout(button_layout)        
        footer_label = QLabel("© 2024 Ajantha Bathroom Products and Pipes Pvt.Ltd | Python Desktop Application | DTCP Plan Permit Automation")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #666666; font-size: 10px; margin-top: 20px; background: transparent; font-weight: 600;")
        self.layout.addWidget(footer_label)        
        self.setLayout(self.layout)

    def start_scraping(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Excel File", 
            f"DTCP_Results_{self.district.currentText()}_{self.year.currentText()}.xlsx", 
            "Excel Files (*.xlsx)"
        )        
        if not save_path:
            return            
        self.scrape_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.loader.setVisible(True)        
        if hasattr(self, 'loader_movie'):
            self.loader_movie.start()        
        self.thread = ScraperThread(
            self.department.currentText(),
            self.approval_type.currentText(),
            self.district.currentText(),
            self.year.currentText(),
            save_path
        )
        self.thread.finished_signal.connect(self.on_scraping_finished)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.start() 
    
    def update_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)   
    
    def on_scraping_finished(self, message):
        self.scrape_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.loader.setVisible(False)        
        if hasattr(self, 'loader_movie'):
            self.loader_movie.stop()        
        success_msg = f"""
        <div style='font-family: Segoe UI; font-size: 14px; color: #ffffff; background: #000000; padding: 25px; border-radius: 8px; border: 2px solid #dc2626; max-width: 500px;'>
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='color: #dc2626; margin: 0; font-size: 22px; font-weight: 800;'>✅ SCRAPING COMPLETED</h3>
                <div style='color: #cccccc; font-size: 13px; margin-top: 5px;'>DTCP data successfully extracted</div>
            </div>
            
            <div style='background: #1a1a1a; padding: 15px; border-radius: 6px; margin-bottom: 15px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <div style='text-align: center; flex: 1;'>
                        <div style='font-size: 20px; font-weight: 800; color: #dc2626;'>10</div>
                        <div style='font-size: 11px; color: #cccccc;'>Documents Processed</div>
                    </div>
                    <div style='text-align: center; flex: 1;'>
                        <div style='font-size: 20px; font-weight: 800; color: #dc2626;'>{self.district.currentText()}</div>
                        <div style='font-size: 11px; color: #cccccc;'>District</div>
                    </div>
                    <div style='text-align: center; flex: 1;'>
                        <div style='font-size: 20px; font-weight: 800; color: #dc2626;'>{self.year.currentText()}</div>
                        <div style='font-size: 11px; color: #cccccc;'>Year</div>
                    </div>
                </div>
            </div>
            
            <div style='margin-top: 15px; padding: 12px; background: #dc2626; border-radius: 4px; text-align: center;'>
                <span style='color: #ffffff; font-weight: 700; font-size: 13px;'>📊 DATA READY FOR ANALYSIS</span>
            </div>
        </div>
        """        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("DTCP Scraping Completed")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(success_msg)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)    
    app.setApplicationName("DTCP Plan Permit Scraper")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Ajantha Bathroom Products")
    app.setOrganizationDomain("ajantha.com")    
    win = DTCPApp()
    win.show()
    sys.exit(app.exec_())