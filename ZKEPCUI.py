from bs4 import BeautifulSoup
import requests
from PyQt5 import QtCore, QtGui, QtWidgets
import time
import smtplib
import threading

class Web_Epc(object):

    def epcmain(self, usr):
        session = requests.session()
        self.login(session, usr[3], usr[4])
        cinfo = self.getCourse(session, usr[9])
        cinfo = self.transInfo(cinfo)
        cstat = self.judgeCourse(usr[6], usr[7], usr[5], usr[8], cinfo)
        self.bookCourse(session, cstat, cinfo, usr[1], usr[2], usr[0], usr[10])

    def login(self, session, stid, stpwd):
        url_login = 'http://epc.ustc.edu.cn/n_left.asp'
        headers = {
            'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/85.0.4183.121 '
                'Safari/537.36'
        }
        logindata = {
            'submit_type': 'user_login',
            'name': stid,
            'pass': stpwd,
            'user_type': '2',
            'Submit': 'LOG IN'
        }
        loginresp = session.post(url_login, headers=headers, data=logindata)

    def getCourse(self, session, ctype):
        url = [
            'http://epc.ustc.edu.cn/m_practice.asp?second_id=2001',  # Situation
            'http://epc.ustc.edu.cn/m_practice.asp?second_id=2002',  # Topic
            'http://epc.ustc.edu.cn/m_practice.asp?second_id=2003',
            'http://epc.ustc.edu.cn/m_practice.asp?second_id=2004',  # Drama
        ]
        cresp = session.get(url[ctype])
        soup = BeautifulSoup(cresp.text, 'lxml')
        ini_info = soup.find_all('form')
        flag = 0
        cinfo = []
        for line in ini_info:
            link_info = line['action']
            tmp_cinfo = line.find_all('td')
            cinfo.append([])
            for tdline in tmp_cinfo:
                if tdline.string is None:
                    tmp_str = ''
                    for string in tdline.strings:
                        tmp_str = tmp_str + ' ' + string
                    cinfo[flag].append(tmp_str)
                else:
                    cinfo[flag].append(tdline.string)
            cinfo[flag].append(link_info)
            flag += 1
        return cinfo

    def transInfo(self, cinfo):
        day_dic = {'周一': '1', '周二': '2', '周三': '3', '周四': '4', '周五': '5', '周六': '6', '周日': '7'}
        for cline in cinfo:
            cline[1] = cline[1][1:-1]
            cline[2] = day_dic[cline[2]]
        return cinfo

    def judgeCourse(self, week_av, day_av, teacher_av, time_av, cinfo):
        cstat = []
        for cline in cinfo:
            if cline[-2].strip() != '':
                cstat.append('1')
                continue
            '''
            if cline[-2].strip() == '您已经预约过该时间段的课程':
                cstat.append('10')
                continue
            if cline[-2].strip() == '已达预约上限':
                cstat.append('11')
                continue
            if cline[-2].strip() == '已选择过该教师与话题相同的课程，不能重复选择':
                cstat.append('12')
                continue
            '''
            if cline[2] not in day_av:
                cstat.append('2')
                continue
            else:
                index = day_av.index(cline[2])
                dtime = time_av[index].strip().split('&')
                dtimeflag = 0
                for dtime_av in dtime:
                    if dtime_av == '0':
                        dtimeflag = 1
                        break
                    if dtime_av == '1':
                        dtime_av = '06:00-12:00'
                    elif dtime_av == '2':
                        dtime_av = '14:00-18:30'
                    elif dtime_av == '3':
                        dtime_av = '19:00-22:00'
                    if cline[5][-11:-6] >= dtime_av[-11:-6] and cline[5][-5:-1] <= dtime_av[-5:-1]:
                        dtimeflag = 1
                        break
                if dtimeflag == 0:
                    cstat.append('5')
                    continue
            if teacher_av[0] == '!':
                if cline[3] in teacher_av[1:].strip().split('&'):
                    cstat.append('3')
                    continue
            else:
                if cline[3] not in teacher_av.strip().split('&') and teacher_av != '0':
                    cstat.append('3')
                    continue
            if cline[1] not in week_av.split('&') and week_av != '0':
                cstat.append('4')
                continue
            cstat.append('0')
        return cstat

    def sendMail(self, acc, pwd, receiver, check_info):
        from email.mime.text import MIMEText
        from email.header import Header
        sname = acc.strip().split('@')[1]
        account = acc.strip().split('@')[0]
        mailhost = 'smtp.' + sname
        neteasemail = smtplib.SMTP()
        neteasemail.connect(mailhost, 25)
        neteasemail.login(account, password=pwd)
        sender = account + '@' + sname
        content = "From ZeKyoU: Book a epc class successfully!\n Time:" + check_info[7] + \
                  '\n Topic: ' + check_info[1] + '\n Room: ' + check_info[0] + '\n Teacher: ' + check_info[2]
        if int(receiver[0:5]) + int(receiver[5:10]) == 17522:
            content = 'Darling!' + content
        message = MIMEText(content, 'plain', 'utf-8')
        subject = 'USTC-EPC'
        message['Subject'] = Header(subject, 'utf-8')
        message['From'] = '<' + acc + '>'
        message['To'] = "'<" + receiver + ">'"
        neteasemail.sendmail(sender, receiver, message.as_string())
        neteasemail.quit()

    def bookCourse(self, session, cstat, cinfo, acc, pwd, emailaddress, eflag):
        flag = 0
        cflag = 0
        bookdata = {
            'submit_type': 'book_submit'
        }
        for stat in cstat:
            if stat == '0':
                bookurl = r'http://epc.ustc.edu.cn/' + cinfo[flag][-1]
                bookresp = session.post(url=bookurl, data=bookdata)
                self.checkCourse(session, cinfo[flag][0], acc, pwd, emailaddress, eflag)
                cflag = cflag +1
            flag = flag +1
            if cflag >5:
                break

    def checkCourse(self, session, bookname, acc, pwd, emailaddress, eflag):
        checkurl = 'http://epc.ustc.edu.cn/record_book.asp'
        checkresp = session.get(url=checkurl)
        soup = BeautifulSoup(checkresp.text, 'lxml')
        ini_check_info = soup.find_all('form')[-1]
        check_info = []
        tmp_info = ini_check_info.find_all('td')
        for cinfo in tmp_info:
            if cinfo.string is None:
                tmp_str = ''
                for string in cinfo.strings:
                    tmp_str = tmp_str + ' ' + string
                check_info.append(tmp_str)
            else:
                check_info.append(cinfo.string)
        if check_info[1] == bookname and eflag:
            self.sendMail(acc, pwd, emailaddress, check_info)


    # end of script

class Ui_ZKEPC(object):

    def __init__(self):
        self.stime = 1000
        self.mtime = 1500
        self.ltime = 2000

    def decorate(self):
        self.statusbar.setStyleSheet('background:rgba(255,240,245,0.8)')
        linestyl1 = 'border:1px solid orange;border-radius:10px;padding:2px 4px;background:rgba(255,218,185,0.7)'
        self.lineEdit.setStyleSheet(linestyl1)
        self.lineEdit_2.setStyleSheet(linestyl1)
        self.lineEdit_3.setStyleSheet(linestyl1)
        self.lineEdit_4.setStyleSheet(linestyl1)
        self.lineEdit_5.setStyleSheet(linestyl1)
        self.lineEdit_6.setStyleSheet(linestyl1)
        self.lineEdit_7.setStyleSheet(linestyl1)
        self.lineEdit_8.setStyleSheet(linestyl1)
        self.lineEdit_9.setStyleSheet(linestyl1)
        self.lineEdit_10.setStyleSheet(linestyl1)
        self.lineEdit_11.setStyleSheet(linestyl1)
        self.lineEdit_12.setStyleSheet(linestyl1)
        labelstyl1 = 'border:1px solid cyan;border-radius:10px;padding:2px 4px;background:' \
                     'rgba(187,255,255,0.7)'
        self.label_4.setText('ZeKyoU')
        self.label_4.setStyleSheet('color:rgb(255,240,245)')
        self.label_6.setStyleSheet(labelstyl1)
        self.label_7.setStyleSheet(labelstyl1)
        self.label_8.setStyleSheet(labelstyl1)
        self.label_9.setStyleSheet(labelstyl1)
        self.label_10.setStyleSheet(labelstyl1)
        self.label_12.setStyleSheet(labelstyl1)
        self.label_13.setStyleSheet(labelstyl1)
        self.label_14.setStyleSheet(labelstyl1)
        self.label_15.setStyleSheet(labelstyl1)
        self.label_16.setStyleSheet(labelstyl1)
        self.label_17.setStyleSheet(labelstyl1)
        self.label_15.setMaximumWidth(130)
        checkstyl1 = 'border-radius:3px;background:rgba(245,245,220,0.8)'
        self.checkBox.setStyleSheet(checkstyl1)
        self.checkBox_2.setStyleSheet(checkstyl1)
        self.checkBox_3.setStyleSheet(checkstyl1)
        self.checkBox_4.setStyleSheet(checkstyl1)
        self.checkBox_5.setStyleSheet(checkstyl1)
        self.checkBox_6.setStyleSheet(checkstyl1)
        self.checkBox_7.setStyleSheet(checkstyl1)
        self.checkBox_8.setStyleSheet(checkstyl1)
        self.checkBox_9.setStyleSheet(checkstyl1)
        self.checkBox.setMaximumWidth(90)
        self.checkBox_2.setMaximumWidth(95)
        self.checkBox_3.setMaximumWidth(125)
        self.checkBox_4.setMaximumWidth(90)
        self.checkBox_5.setMaximumWidth(98)
        self.checkBox_6.setMaximumWidth(105)
        self.checkBox_7.setMaximumWidth(98)
        self.checkBox_8.setMaximumWidth(90)
        self.checkBox_9.setMaximumWidth(115)
        radiostyl1 = 'border-radius:2px;background:rgba(221,160,221,0.8)'
        self.radioButton.setStyleSheet(radiostyl1)
        self.radioButton_2.setStyleSheet(radiostyl1)
        self.radioButton_3.setStyleSheet(radiostyl1)
        self.spinBox.setStyleSheet(labelstyl1)
        self.radioButton_2.setMaximumWidth(70)
        self.radioButton_3.setMaximumWidth(85)
        btnstyl1 = 'QPushButton{background:rgba(255,193,193,0.8);border-style:outset;border-radius:10px;' \
                   'border:3px solid rgb(255,218,185)}QPushButton:pressed{background:rgba(255,193,193,0.2);' \
                   'border-radius:10px;border-style:outset;border:3px solid rgb(255,218,185)}QPushButton:hover'\
                   '{background:rgba(255,114,86,0.9)}'
        self.pushButton.setFixedSize(22,22)
        self.pushButton_2.setFixedSize(22,22)
        self.pushButton.setStyleSheet(
            '''QPushButton{background:#6DDF6D;border-radius:5px;}QPushButton:hover{background:green;}''')
        self.pushButton_2.setStyleSheet(
            '''QPushButton{background:#F76677;border-radius:5px;}QPushButton:hover{background:red;}''')
        self.pushButton_3.setStyleSheet(btnstyl1)
        self.pushButton_4.setStyleSheet(btnstyl1)
        self.pushButton_5.setStyleSheet(btnstyl1)
        self.pushButton_6.setStyleSheet(btnstyl1)
        self.pushButton_3.setMaximumWidth(100)
        self.pushButton_4.setMaximumWidth(115)
        self.pushButton_5.setMaximumWidth(130)
        self.pushButton_6.setMaximumWidth(145)
        self.spinBox.setMaximumWidth(50)

        self.pushButton_3.setToolTip('使用说明(本地文档)')
        self.pushButton_4.setToolTip('终止搜索')
        self.pushButton_5.setToolTip('开始搜索')
        self.pushButton_6.setToolTip('关于ZeKyoU(GitHub)')
        self.checkBox.setToolTip('是否使用邮件通知')
        self.checkBox_2.setToolTip('隐藏账号密码信息')
        self.checkBox_3.setToolTip('当你打包程序给他人注意不要勾选该选项')
        self.checkBox_9.setToolTip('黑名单模式')
        self.label_7.setToolTip('EPC密码(非其他)')
        self.label_8.setToolTip('接收邮件地址')
        self.label_9.setToolTip('发送邮件地址(目前仅支持QQ和163)')
        self.label_10.setToolTip('POP3/SMTP码(非登录密码)')
        self.label_13.setToolTip('想要课程周数,以下均支持&符号多选')
        self.label_15.setToolTip('具体时间，格式hh:mm-hh:mm')
        self.label_17.setToolTip('搜索频率(建议设大些减少EPC服务器压力)')

        self.font()

    def font(self):
        signfont = QtGui.QFont()
        signfont.setFamily('UD Digi Kyokasho NK-B')
        signfont.setPointSize(20)
        signfont.setBold(True)
        self.label_4.setFont(signfont)
        btnfont = QtGui.QFont()
        btnfont.setFamily('Bauhaus 93')
        btnfont.setPointSize(13)
        self.pushButton_3.setFont(btnfont)
        self.pushButton_4.setFont(btnfont)
        self.pushButton_5.setFont(btnfont)
        self.pushButton_6.setFont(btnfont)
        labelfont1 = QtGui.QFont()
        labelfont1.setFamily('Berlin Sans FB')
        labelfont1.setPointSize(10)
        self.label_6.setFont(labelfont1)
        self.label_7.setFont(labelfont1)
        self.label_8.setFont(labelfont1)
        self.label_9.setFont(labelfont1)
        self.label_10.setFont(labelfont1)
        self.label_12.setFont(labelfont1)
        self.label_13.setFont(labelfont1)
        self.label_14.setFont(labelfont1)
        self.label_15.setFont(labelfont1)
        self.label_16.setFont(labelfont1)
        self.label_17.setFont(labelfont1)
        radiofont1 = QtGui.QFont()
        radiofont1.setFamily('Bradley Hand ITC')
        radiofont1.setBold(True)
        radiofont1.setPointSize(11)
        self.radioButton.setFont(radiofont1)
        self.radioButton_2.setFont(radiofont1)
        self.radioButton_3.setFont(radiofont1)
        checkfont1 = QtGui.QFont()
        checkfont1.setFamily('Comic Sans MS')
        checkfont1.setBold(True)
        self.checkBox.setFont(checkfont1)
        self.checkBox_2.setFont(checkfont1)
        self.checkBox_3.setFont(checkfont1)
        self.checkBox_4.setFont(checkfont1)
        self.checkBox_5.setFont(checkfont1)
        self.checkBox_6.setFont(checkfont1)
        self.checkBox_7.setFont(checkfont1)
        self.checkBox_8.setFont(checkfont1)
        self.checkBox_9.setFont(checkfont1)
        self.spinBox.setFont(checkfont1)
        linefont1 = QtGui.QFont()
        linefont1.setFamily('Comic Sans MS')
        linefont1.setBold(False)
        self.lineEdit.setFont(linefont1)
        self.lineEdit_2.setFont(linefont1)
        self.lineEdit_2.setFont(linefont1)
        self.lineEdit_3.setFont(linefont1)
        self.lineEdit_5.setFont(linefont1)
        self.lineEdit_4.setFont(linefont1)
        self.lineEdit_7.setFont(linefont1)
        self.lineEdit_6.setFont(linefont1)
        self.lineEdit_8.setFont(linefont1)
        self.lineEdit_9.setFont(linefont1)
        self.lineEdit_10.setFont(linefont1)
        self.lineEdit_11.setFont(linefont1)
        self.lineEdit_12.setFont(linefont1)

    def defaultitems(self):
        self.radioButton.setChecked(True)
        self.pushButton_5.setEnabled(True)

        self.checkBox.setChecked(False)
        self.checkBox_2.setChecked(False)
        self.checkBox_3.setChecked(False)
        self.checkBox_4.setChecked(False)
        self.checkBox_5.setChecked(False)
        self.checkBox_6.setChecked(False)
        self.checkBox_7.setChecked(False)
        self.checkBox_8.setChecked(False)
        self.checkBox_9.setChecked(False)

        self.spinBox.setMinimum(2)
        self.spinBox.setMaximum(30)
        self.spinBox.setSingleStep(2)
        self.spinBox.setValue(5)

    def hideinfo(self):
        if self.checkBox_2.isChecked():
            self.lineEdit.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
            self.lineEdit_2.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
            self.lineEdit_3.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
            self.lineEdit_4.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
            self.lineEdit_5.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
        else:
            self.lineEdit.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.lineEdit_2.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.lineEdit_3.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.lineEdit_4.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.lineEdit_5.setEchoMode(QtWidgets.QLineEdit.Normal)

    def remember(self):
        import os
        if self.checkBox_3.isChecked():
            usr = [self.lineEdit.text(), self.lineEdit_2.text(), self.lineEdit_3.text(),
                   self.lineEdit_5.text(), self.lineEdit_4.text(), self.lineEdit_7.text(),
                   self.lineEdit_6.text(), self.lineEdit_8.text(), self.lineEdit_9.text(),
                   self.lineEdit_10.text(), self.lineEdit_11.text(), self.lineEdit_12.text(),
                   self.spinBox.value(),  self.checkBox.isChecked(), self.checkBox_4.isChecked(),
                   self.checkBox_5.isChecked(), self.checkBox_6.isChecked(), self.checkBox_7.isChecked()
                   , self.checkBox_8.isChecked(), self.checkBox_9.isChecked()]
            flag = 0
            with open('./src/usr.tmp', 'w') as fusr:
                for line in usr:
                    fusr.write(str(usr[flag])+'\n')
                    flag = flag + 1
            self.statusbar.showMessage('ZeKyoU has remembered you!', self.mtime)
        else:
            if os.path.exists('./src/usr.tmp'):
                try:
                    os.remove('./src/usr.tmp')
                    self.statusbar.showMessage('ZeKyoU has forgot you!', self.mtime)
                except:
                    self.statusbar.showMessage('Error about removing tmp file!', self.mtime)

    def action(self):
        self.pushButton_3.clicked.connect(self.usage)
        self.pushButton_4.clicked.connect(self.cancel)
        self.pushButton_5.clicked.connect(self.onsearch)
        self.pushButton_6.clicked.connect(self.about)
        self.checkBox_3.stateChanged.connect(self.remember)
        self.checkBox_2.stateChanged.connect(self.hideinfo)

    def usage(self):
        import webbrowser
        import os
        webbrowser.open('file:///' + os.getcwd() + r'\src\usage.html')

    def about(self):
        import webbrowser
        webbrowser.open('https://github.com/zekyou/ZKEPC-USTC')

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowIcon(QtGui.QIcon('./src/main.ico'))
        MainWindow.setStyleSheet('QMainWindow{border-image:url(./src/bg.jpg)}')
        MainWindow.resize(630, 520)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.gridLayout_7 = QtWidgets.QGridLayout()
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.lineEdit_4 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_4.setObjectName("lineEdit_4")
        self.gridLayout_7.addWidget(self.lineEdit_4, 6, 3, 1, 2)
        self.label_12 = QtWidgets.QLabel(self.centralwidget)
        self.label_12.setAlignment(QtCore.Qt.AlignCenter)
        self.label_12.setObjectName("label_12")
        self.gridLayout_7.addWidget(self.label_12, 9, 2, 1, 1)
        self.lineEdit_7 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_7.setObjectName("lineEdit_7")
        self.gridLayout_7.addWidget(self.lineEdit_7, 12, 3, 1, 2)
        self.checkBox_7 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_7.setObjectName("checkBox_7")
        self.gridLayout_7.addWidget(self.checkBox_7, 15, 2, 1, 1)
        self.checkBox_2 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_2.setObjectName("checkBox_2")
        self.gridLayout_7.addWidget(self.checkBox_2, 4, 3, 1, 1)
        self.checkBox_9 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_9.setObjectName("checkBox_9")
        self.gridLayout_7.addWidget(self.checkBox_9, 17, 4, 1, 1)
        self.lineEdit_12 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_12.setObjectName("lineEdit_12")
        self.gridLayout_7.addWidget(self.lineEdit_12, 17, 3, 1, 1)
        self.lineEdit_11 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_11.setObjectName("lineEdit_11")
        self.gridLayout_7.addWidget(self.lineEdit_11, 16, 3, 1, 2)
        self.lineEdit_3 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.gridLayout_7.addWidget(self.lineEdit_3, 5, 3, 1, 2)
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setAlignment(QtCore.Qt.AlignCenter)
        self.label_8.setObjectName("label_8")
        self.gridLayout_7.addWidget(self.label_8, 5, 2, 1, 1)
        self.checkBox = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox.setObjectName("checkBox")
        self.gridLayout_7.addWidget(self.checkBox, 4, 2, 1, 1)
        self.checkBox_5 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_5.setObjectName("checkBox_5")
        self.gridLayout_7.addWidget(self.checkBox_5, 13, 2, 1, 1)
        self.lineEdit_10 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_10.setObjectName("lineEdit_10")
        self.gridLayout_7.addWidget(self.lineEdit_10, 15, 3, 1, 2)

        self.lineEdit_6 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_6.setObjectName("lineEdit_6")
        self.gridLayout_7.addWidget(self.lineEdit_6, 9, 4, 1, 1)
        self.label_10 = QtWidgets.QLabel(self.centralwidget)
        self.label_10.setAlignment(QtCore.Qt.AlignCenter)
        self.label_10.setObjectName("label_10")
        self.gridLayout_7.addWidget(self.label_10, 7, 2, 1, 1)
        self.label_9 = QtWidgets.QLabel(self.centralwidget)
        self.label_9.setAlignment(QtCore.Qt.AlignCenter)
        self.label_9.setObjectName("label_9")
        self.gridLayout_7.addWidget(self.label_9, 6, 2, 1, 1)
        self.lineEdit_5 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_5.setObjectName("lineEdit_5")
        self.gridLayout_7.addWidget(self.lineEdit_5, 7, 3, 1, 2)
        self.checkBox_3 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_3.setObjectName("checkBox_3")
        self.gridLayout_7.addWidget(self.checkBox_3, 4, 4, 1, 1)
        self.label_11 = QtWidgets.QLabel(self.centralwidget)
        self.label_11.setAlignment(QtCore.Qt.AlignCenter)
        self.label_11.setObjectName("label_11")
        self.gridLayout_7.addWidget(self.label_11, 8, 2, 1, 3)
        self.checkBox_8 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_8.setObjectName("checkBox_8")
        self.gridLayout_7.addWidget(self.checkBox_8, 16, 2, 1, 1)
        self.checkBox_6 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_6.setObjectName("checkBox_6")
        self.gridLayout_7.addWidget(self.checkBox_6, 14, 2, 1, 1)
        self.lineEdit_8 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_8.setObjectName("lineEdit_8")
        self.gridLayout_7.addWidget(self.lineEdit_8, 13, 3, 1, 2)
        self.label_16 = QtWidgets.QLabel(self.centralwidget)
        self.label_16.setAlignment(QtCore.Qt.AlignCenter)
        self.label_16.setObjectName("label_16")
        self.gridLayout_7.addWidget(self.label_16, 17, 2, 1, 1)
        self.radioButton = QtWidgets.QRadioButton(self.centralwidget)
        self.radioButton.setObjectName("radioButton")
        self.gridLayout_7.addWidget(self.radioButton, 10, 2, 1, 1)
        self.radioButton_2 = QtWidgets.QRadioButton(self.centralwidget)
        self.radioButton_2.setObjectName("radioButton_2")
        self.gridLayout_7.addWidget(self.radioButton_2, 10, 3, 1, 1)
        self.radioButton_3 = QtWidgets.QRadioButton(self.centralwidget)
        self.radioButton_3.setObjectName("radioButton_3")
        self.gridLayout_7.addWidget(self.radioButton_3, 10, 4, 1, 1)
        self.label_14 = QtWidgets.QLabel(self.centralwidget)
        self.label_14.setAlignment(QtCore.Qt.AlignCenter)
        self.label_14.setObjectName("label_14")
        self.gridLayout_7.addWidget(self.label_14, 11, 2, 1, 1)
        self.label_15 = QtWidgets.QLabel(self.centralwidget)
        self.label_15.setAlignment(QtCore.Qt.AlignCenter)
        self.label_15.setObjectName("label_15")
        self.gridLayout_7.addWidget(self.label_15, 11, 3, 1, 2)
        self.lineEdit_9 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_9.setObjectName("lineEdit_9")
        self.gridLayout_7.addWidget(self.lineEdit_9, 14, 3, 1, 2)
        self.checkBox_4 = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBox_4.setObjectName("checkBox_4")
        self.gridLayout_7.addWidget(self.checkBox_4, 12, 2, 1, 1)
        self.label_13 = QtWidgets.QLabel(self.centralwidget)
        self.label_13.setAlignment(QtCore.Qt.AlignCenter)
        self.label_13.setObjectName("label_13")
        self.gridLayout_7.addWidget(self.label_13, 9, 3, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.gridLayout_7.addWidget(self.label_5, 1, 2, 3, 3)
        self.gridLayout_5.addLayout(self.gridLayout_7, 0, 1, 1, 1)
        self.gridLayout_6 = QtWidgets.QGridLayout()
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.pushButton_6 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_6.setObjectName("pushButton_6")
        self.gridLayout_6.addWidget(self.pushButton_6, 10, 1, 1, 2)
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout_6.addWidget(self.label_2, 2, 2, 1, 1)
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setObjectName("pushButton")
        self.gridLayout_6.addWidget(self.pushButton, 1, 1, 1, 1)
        self.label_17 = QtWidgets.QLabel(self.centralwidget)
        self.label_17.setAlignment(QtCore.Qt.AlignCenter)
        self.label_17.setObjectName('label_17')
        self.gridLayout_6.addWidget(self.label_17, 6, 1, 1, 1)
        self.spinBox = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox.setObjectName('spin')
        self.gridLayout_6.addWidget(self.spinBox, 6, 2, 1, 1)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setLineWidth(1)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout_6.addWidget(self.label, 2, 1, 1, 1)
        self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_4.setObjectName("pushButton_4")
        self.gridLayout_6.addWidget(self.pushButton_4, 8, 1, 1, 2)
        self.lineEdit_2 = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.gridLayout_6.addWidget(self.lineEdit_2, 4, 2, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setAlignment(QtCore.Qt.AlignCenter)
        self.label_6.setObjectName("label_6")
        self.gridLayout_6.addWidget(self.label_6, 3, 1, 1, 1)
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.gridLayout_6.addWidget(self.pushButton_2, 1, 2, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.gridLayout_6.addWidget(self.label_4, 11, 1, 1, 2)
        self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_3.setObjectName("pushButton_3")
        self.gridLayout_6.addWidget(self.pushButton_3, 7, 1, 1, 2)
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.gridLayout_6.addWidget(self.label_3, 5, 1, 1, 2)
        self.pushButton_5 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_5.setObjectName("pushButton_5")
        self.gridLayout_6.addWidget(self.pushButton_5, 9, 1, 1, 2)
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setAlignment(QtCore.Qt.AlignCenter)
        self.label_7.setObjectName("label_7")
        self.gridLayout_6.addWidget(self.label_7, 4, 1, 1, 1)
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setObjectName("lineEdit")
        self.gridLayout_6.addWidget(self.lineEdit, 3, 2, 1, 1)
        self.gridLayout_5.addLayout(self.gridLayout_6, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 600, 36))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def checkinput(self):
        flag = 1
        ctype = 0
        recadd = ''
        sender = ''
        poppwd = ''
        try:
            stid = self.lineEdit.text()
            stpwd = self.lineEdit_2.text()
            if self.checkBox.isChecked():
                try:
                    recadd = self.lineEdit_3.text()
                    sender = self.lineEdit_4.text()
                    poppwd = self.lineEdit_5.text()
                except:
                    self.statusbar.showMessage('Error about email info!', self.ltime)
                if '' in [recadd, sender, poppwd]:
                    self.statusbar.showMessage('Email info is empty', self.stime)
                    flag = 0
        except:
            self.statusbar.showMessage('Error about basic info!', self.ltime)
        if '' in [stid, stpwd]:
            self.statusbar.showMessage('StID or PWD is empty', self.stime)
            flag = 0
        try:
            teacherav = self.lineEdit_12.text()
            if teacherav == '':
                teacherav = '0'
            if self.checkBox_9.isChecked():
                teacherav = '!' + teacherav
            weekav = self.lineEdit_6.text()
        except:
            self.statusbar.showMessage('Error about week and teacher!!', self.ltime)
        dayav = []
        stime = []
        try:
            if self.checkBox_4.isChecked():
                dayav.append('1')
                stime.append(self.lineEdit_7.text())
                if stime[-1] == '':
                    stime[-1] = '0'
            if self.checkBox_5.isChecked():
                dayav.append('2')
                stime.append(self.lineEdit_8.text())
                if stime[-1] == '':
                    stime[-1] = '0'
            if self.checkBox_6.isChecked():
                dayav.append('3')
                stime.append(self.lineEdit_9.text())
                if stime[-1] == '':
                    stime[-1] = '0'
            if self.checkBox_7.isChecked():
                dayav.append('4')
                stime.append(self.lineEdit_10.text())
                if stime[-1] == '':
                    stime[-1] = '0'
            if self.checkBox_8.isChecked():
                dayav.append('5')
                stime.append(self.lineEdit_11.text())
                if stime[-1] == '':
                    stime[-1] = '0'
            if not dayav:
                dayav.append('8')
        except:
            self.statusbar.showMessage('Error about day and time', self.ltime)
        if weekav == '':
            weekav = '0'
        if self.radioButton.isChecked():
            ctype = 0
        elif self.radioButton_2.isChecked():
            ctype = 1
        elif self.radioButton_3.isChecked():
            ctype = 3
        return [flag, recadd, sender, poppwd, stid, stpwd, teacherav, weekav, dayav, stime, ctype]

    def checkrem(self):
        import os
        if os.path.exists('./src/usr.tmp'):
            try:
                usr = []
                with open('./src/usr.tmp','r') as fusr:
                    for line in fusr:
                        usr.append(line.strip())
                self.lineEdit.setText(usr[0])
                self.lineEdit_2.setText(usr[1])
                self.lineEdit_3.setText(usr[2])
                self.lineEdit_5.setText(usr[3])
                self.lineEdit_4.setText(usr[4])
                self.lineEdit_7.setText(usr[5])
                self.lineEdit_6.setText(usr[6])
                self.lineEdit_8.setText(usr[7])
                self.lineEdit_9.setText(usr[8])
                self.lineEdit_10.setText(usr[9])
                self.lineEdit_11.setText(usr[10])
                self.lineEdit_12.setText(usr[11])
                self.spinBox.setValue(int(usr[12]))
                self.checkBox.setChecked(usr[13] == 'True')
                self.checkBox_4.setChecked(usr[14] == 'True')
                self.checkBox_5.setChecked(usr[15] == 'True')
                self.checkBox_6.setChecked(usr[16] == 'True')
                self.checkBox_7.setChecked(usr[17] == 'True')
                self.checkBox_8.setChecked(usr[18] == 'True')
                self.checkBox_9.setChecked(usr[19] == 'True')
            except:
                self.statusbar.showMessage('Error loading history info!', self.stime)

    def onsearch(self):
        self.thread = threading.Thread(target=self.start)
        self.thread.setDaemon(True)
        self.thread.start()

    def start(self):
        self.tflag = 1
        while True:
            if self.tflag == 1:
                [flag, recadd, sender, poppwd, stid, stpwd, teacherav, weekav, dayav, stime, ctype] = self.checkinput()
                if flag == 0:
                    self.errorinput()
                    break
                else:
                    try:
                        self.statusbar.showMessage('Start searching available course!', self.stime)
                        self.pushButton_5.setEnabled(False)
                        sptime = self.spinBox.value()*60
                        eflag = self.checkBox.isChecked()
                        web = Web_Epc()
                        web.epcmain([recadd, sender, poppwd, stid, stpwd, teacherav, weekav, dayav, stime, ctype, eflag])
                        time.sleep(sptime)
                    except:
                        self.statusbar.showMessage('Error unexpected happens!', self.ltime)
                        break
            else:
                break

    def errorinput(self):
        self.tflag = 0
        #self.statusbar.showMessage('Error about input data!')

    def cancel(self):
        self.pushButton_5.setEnabled(True)
        self.tflag = 0
        self.statusbar.showMessage('Cancelled successfully!', self.ltime)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ZKEPCv2.0"))
        self.label_6.setText(_translate("MainWindow", "StudentID"))
        self.label_7.setText(_translate("MainWindow", "Password"))
        self.label_8.setText(_translate("MainWindow", "Receiver"))
        self.label_9.setText(_translate("MainWindow", "Sender"))
        self.label_10.setText(_translate("MainWindow", "POP3PWD"))
        self.label_12.setText(_translate("MainWindow", "CourseType"))
        self.label_13.setText(_translate("MainWindow", "WeekAva"))
        self.label_14.setText(_translate("MainWindow", "DayAva"))
        self.label_15.setText(_translate("MainWindow", "SpecificTime"))
        self.label_16.setText(_translate("MainWindow", "TeacherLike"))
        self.label_17.setText(_translate("MainWindow", "Sleep(min)"))

        self.radioButton.setText(_translate("MainWindow", "Situation"))
        self.radioButton_2.setText(_translate("MainWindow", "Topic"))
        self.radioButton_3.setText(_translate("MainWindow", "Drama"))

        self.pushButton_3.setText(_translate("MainWindow", "USAGE!"))
        self.pushButton_4.setText(_translate("MainWindow", "CANCLE!"))
        self.pushButton_5.setText(_translate("MainWindow", "START!"))
        self.pushButton_6.setText(_translate("MainWindow", "ABOUT!"))

        self.checkBox.setText(_translate("MainWindow", "E-mail?"))
        self.checkBox_2.setText(_translate("MainWindow", "Hide info"))
        self.checkBox_3.setText(_translate("MainWindow", "RememberMe?"))
        self.checkBox_4.setText(_translate("MainWindow", "Monday"))
        self.checkBox_5.setText(_translate("MainWindow", "Tuesday"))
        self.checkBox_6.setText(_translate("MainWindow", "Wednesday"))
        self.checkBox_7.setText(_translate("MainWindow", "Thursday"))
        self.checkBox_8.setText(_translate("MainWindow", "Friday"))
        self.checkBox_9.setText(_translate('MainWindow', 'Black List?'))

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = QtWidgets.QMainWindow()
    ui = Ui_ZKEPC()
    ui.setupUi(mainwindow)
    ui.defaultitems()
    ui.decorate()
    ui.action()
    ui.checkrem()
    mainwindow.show()
    sys.exit(app.exec())