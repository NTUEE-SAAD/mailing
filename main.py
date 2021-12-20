import json
from optparse import OptionParser

try:
    from PyQt5 import QtWidgets, QtCore
    from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox
    from PyQt5 import QtWebEngineWidgets

    GUI = True
    # GUI = False
except:
    GUI = False

import qt.editor as editor
from mailer import mailer_invite

import sys
from os import mkdir
from os.path import split, join, abspath, exists
import configparser as cp


CURRENT_DIR = split(abspath(__file__))[0]


class Main(QMainWindow, editor.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.html_viewer = QtWebEngineWidgets.QWebEngineView(self.label.parentWidget())
        self.html_viewer.setGeometry(self.label.geometry())
        self.html_viewer.setStyleSheet(self.label.styleSheet())
        self.html_viewer.setObjectName("html_viewer")

        self.button_load.clicked.connect(lambda: self.load())
        self.button_save.clicked.connect(lambda: self.save(popup=True))
        self.button_send.clicked.connect(lambda: self.send())

    def load(self):
        self.letter = join(CURRENT_DIR, "letters", self.edit_letter.text())
        if self.edit_letter.text() == "" or not exists(self.letter):
            self.letter = str(QFileDialog.getExistingDirectory(self, "Select Directory",
                                                               join(CURRENT_DIR, "letters")))
            if self.letter == "":
                return

        self.edit_letter.setText(split(self.letter)[1])

        account = cp.ConfigParser()
        account.read(join(CURRENT_DIR, "account.ini"), encoding="utf-8")

        # read sender account information
        account_info = account["ACCOUNT"]
        acc_user_name = account_info["name"]
        acc_user_id = account_info["userid"]
        acc_password = account_info["password"]

        self.edit_user_name.setText(acc_user_name)
        self.edit_user_id.setText(acc_user_id)
        self.edit_password.setText(acc_password)

        config = json.loads(open(
            join(self.letter, "config.json"), 'r', encoding="utf-8"
        ).read())

        # read message information
        mes_from = config["from"]
        mes_subject = config["subject"]
        mes_title = config["recipientTitle"]["title"]
        mes_last_name_only = config["recipientTitle"]["lastNameOnly"]

        self.edit_from.setText(mes_from)
        self.edit_subject.setText(mes_subject)
        self.edit_title.setText(mes_title)
        self.check_last.setChecked(mes_last_name_only)

        # read recipient list
        self.edit_recipient.setText(open(
            join(self.letter, "recipients.csv"), 'r', encoding="utf-8"
        ).read())
        # self.edit_recipient.setHtml(open(
        #     self.folder + "\\test.html", 'r', encoding="utf-8"
        # ).read())

        # read letter detail
        self.html_viewer.load(QtCore.QUrl().fromLocalFile(
            join(self.letter, "content.html"))
        )

    def save(self, popup):
        if self.edit_letter.text() == "":
            return

        account = cp.ConfigParser()
        account.read(join(CURRENT_DIR, "account.ini"), encoding="utf-8")

        account.set("ACCOUNT", "userid", self.edit_user_id.text())
        account.set("ACCOUNT", "name", self.edit_user_name.text())
        account.set("ACCOUNT", "password", self.edit_password.text())

        with open(join(CURRENT_DIR, "account.ini"), "w", encoding="utf-8") as config_file:
            account.write(config_file)

        if not (hasattr(self, 'letter') and split(self.letter)[-1] == self.edit_letter.text()):
            self.letter = join(CURRENT_DIR, "letters", self.edit_letter.text())
            if exists(self.letter):
                msg = QMessageBox()
                msg.setWindowTitle("Saving Result")
                msg.setText("Folder Exists!")
                msg.exec_()
                return

            mkdir(self.letter)
            mkdir(join(self.letter, "attach"))
            open(join(self.letter, "content.html"), 'w', encoding="utf-8").close()
            open(join(self.letter, "recipients.csv"), 'w', encoding="utf-8").close()
            open(join(self.letter, "config.json"), 'w', encoding="utf-8").close()

        with open(join(self.letter, "recipients.csv"), 'w', encoding="utf-8") as recipients_file:
            recipients_file.write(self.edit_recipient.toPlainText())

        with open(join(self.letter, "config.json"), 'w', encoding="utf-8") as config_file:
            config = {"subject": self.edit_subject.text(),
                      "from": self.edit_from.text(),
                      "recipientTitle": {
                          "title": self.edit_title.text(),
                          "lastNameOnly": self.check_last.isChecked()
                      }
                      }
            # print(json.dump(config))
            json.dump(config, config_file, ensure_ascii=False, sort_keys=True, indent=4)

        if popup:
            msg = QMessageBox()
            msg.setWindowTitle("Saving Result")
            msg.setText("Successful!")
            msg.exec_()

    def send(self):
        if hasattr(self, 'letter'):
            self.save(popup=False)

            opts = {"attach": self.check_attach.isChecked(),
                    "test": self.check_test.isChecked(),
                    "yes": True,
                    "nosend": False}
            args = [split(self.letter)[-1]]

            msg = QMessageBox()
            msg.setWindowTitle("Sending Result")
            msg.setText(mailer_invite.main(opts, args, CURRENT_DIR))
            msg.exec_()


if __name__ == '__main__':
    if not GUI:
        optParser = OptionParser()
        optParser.set_usage(
            "python mailer_invite.py <LETTER>\nLETTER is the name of the folder in the 'letters' folder where your email lives")
        optParser.add_option("-a", "--attach", dest="attach", default=False, action="store_true",
                             help="attach files in 'letters/LETTER/attachments' folder to the email")
        optParser.add_option("-t", "--test", dest="test", default=False, action="store_true",
                             help="send email in test mode (to yourself)")
        optParser.add_option("-y", "--yes", dest="yes", default=False, action="store_true",
                             help="同意啦，那次不同意")
        optParser.add_option("--nosend", dest="nosend", default=False,
                             action="store_true", help="for debugging")
        opts, args = optParser.parse_args()

        if len(args) == 0:
            print("please specify the letter you want to send")
            exit()

        mailer_invite.main({"attach": opts.attach,
                            "test": opts.test,
                            "yes": opts.yes,
                            "nosend": opts.nosend},
                           args, CURRENT_DIR)

    else:
        app = QtWidgets.QApplication(sys.argv)
        window = Main()
        window.show()
        sys.exit(app.exec_())
