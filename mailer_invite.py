##########################################################################
# File:         mailer_invite.py                                         #
# Purpose:      Automatic send 專題說明會 invitation mails to professors   #
# Last changed: 2015/06/21                                               #
# Author:       Yi-Lin Juang (B02 學術長)                                 #
# Edited:       2021/12/13 莊加旭
#               2021/07/01 Eleson Chuang (B08 Python大佬)                 #
#               2018/05/22 Joey Wang (B05 學術長)                         #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email.mime.image import MIMEImage
import sys
import time
import configparser as cp
import os
import os.path
import csv
from string import Template
from pathlib import Path
from optparse import OptionParser
import json


def connectSMTP(userid, password) -> smtplib.SMTP_SSL:
    try:
        # check the user's time of enrollment, ntumail before 09 uses different server setting
        if int(userid[1:3]) >= 9:
            server = smtplib.SMTP_SSL("smtps.ntu.edu.tw", 465, timeout=5)
        else:
            server = smtplib.SMTP('mail.ntu.edu.tw', 587)
    except Exception as e:
        print(e)
        print('error: smtp connection failed, try using another wifi')
    # Uncomment this line to go through SMTP connection status.
    server.ehlo()
    if server.has_extn("STARTTLS"):
        server.starttls()
        server.ehlo()
    try:
        server.login(userid, password)
    except:
        print('error: login failed, please check your acount.ini file')

    print("SMTP Connected!")
    return server


def load_account_config() -> tuple:
    '''load account info from account.ini'''
    account_config = cp.ConfigParser()
    account_config.read("account.ini")
    try:
        userid = account_config["ACCOUNT"]["userid"]
        password = account_config["ACCOUNT"]["password"]
    except Exception as e:
        print(e)
        print("Fail reading the config file!\nPlease check the account.ini ...")
        exit()

    return [userid, password]


def load_recipient_list(path):
    with open(path, 'r', newline='', encoding="utf-8") as csvfile:
        recipients = csv.reader(csvfile)
        recipients = [recipient for recipient in recipients]

    return recipients


def load_letter_config(path):
    with open(path, encoding='utf-8') as f:
        letter_config = json.load(f)

    try:
        email_subject = letter_config["subject"]
        email_from = letter_config["from"]
    except Exception as e:
        print(e)
        print("Fail reading letter config file!\nPlease check your config.json")
        exit()

    return [email_subject, email_from]


def send_mail(msg, server):
    server.sendmail(msg["From"], msg["To"], msg.as_string())
    print(f'Sent mail to {msg["To"]}')


def attach_files_METHOD1(msg):
    '''This method will attach all the files in the ./attach folder.'''
    dir_path = os.getcwd()+"/attach"
    files = os.listdir("attach")
    for f in files:  # add files to the message
        file_path = os.path.join(dir_path, f)
        attachment = MIMEApplication(open(file_path, "rb").read())
        attachment.add_header('Content-Disposition', 'inline', filename=f)
        msg.attach(attachment)


def attach_files_METHOD2(msg):
    '''Reading attachment, put file_path in args'''
    for argvs in sys.argv[1:]:
        attachment = MIMEApplication(open(str(argvs), "rb").read())
        attachment.add_header("Content-Disposition",
                              "attachment", filename=str(argvs))
        msg.attach(attachment)


def server_rest(count):
    '''for bypassing email server limitation'''
    if count % 10 == 0 and count > 0:
        print(f'{count} mails sent, resting...')
        time.sleep(10)
    if count % 130 == 0 and count > 0:
        print(f'{count} mails sent, resting...')
        time.sleep(20)
    if count % 260 == 0 and count > 0:
        print(f'{count} mails sent, resting...')
        time.sleep(20)


def main(opts, args):
    # choose the receiver list
    email_root_path = Path(f'letters/{args[0]}')
    email_list_path = os.path.join(email_root_path, Path("recipients.csv"))
    email_config_path = os.path.join(email_root_path, Path("config.json"))
    email_content_path = os.path.join(email_root_path, Path("content.html"))

    # load letter config
    [email_subject, email_from] = load_letter_config(email_config_path)

    # load email account info
    userid, password = load_account_config()

    # load recipient list
    if opts.test:
        recipients = [["王小明", f'{userid}@ntu.edu.tw']]
    else:
        recipients = load_recipient_list(email_list_path)

    # load content as template string
    email_html = Template(Path(email_content_path).read_text(encoding="utf-8"))

    server = connectSMTP(userid, password)
    sent_n = 0

    for recipient in recipients:
        email = MIMEMultipart("alternative")
        email["Subject"] = email_subject

        # letter content
        body = email_html.substitute({"recipient": recipient[0]})
        email.attach(MIMEText(body, "html"))

        if '@' in recipient[1]:
            email["To"] = recipient[1]
        else:
            email["To"] = recipient[1] + "@ntu.edu.tw"

        # check if the 'from' field in config.json is filled
        if len(email_from) > 0:
            email['From'] = formataddr(
                (Header(email_from, 'utf-8').encode(), f'{userid}@ntu.edu.tw'))

        # attach enerything in './attach' folder
        if(opts.attach):
            attach_files_METHOD1(email)

        send_mail(email, server)

        sent_n += 1
        server_rest(sent_n)

    server.quit()
    print(f'{sent_n} mails sent{" in test mode" if opts.test else ""}, exitting...')


if __name__ == '__main__':
    parser = OptionParser()
    parser.set_usage(
        "python mailer_invite.py <LETTER>\nLETTER is the name of the folder in the 'letters' folder where your email lives")
    parser.add_option("-a", "--attach", dest="attach", default=False, action="store_true",
                      help="attach files  in ./attach folder to the email")
    parser.add_option("-t", "--test", dest="test", default=False, action="store_true",
                      help="send email in test mode (to yourself)")
    opts, args = parser.parse_args()

    if len(args) == 0:
        print("please specify the letter you want to send")
        exit()

    main(opts, args)
