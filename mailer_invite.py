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
import poplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate
from email.parser import Parser as EmailParser
import email.message
import time
import configparser as cp
import os.path
import csv
import re
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


def load_account_config():
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
        recipients = [recipient[:2] for recipient in recipients]

    return recipients


def handle_recipient_title(recipients, recipTitle, lastNameOnly):
    # cat title to recipient names
    if len(recipTitle) > 0:
        for recipient in recipients:
            if lastNameOnly:
                recipient[0] = recipient[0][0] + recipTitle
            else:
                recipient[0] += recipTitle

    return recipients


def load_letter_config(path):
    with open(path, encoding='utf-8') as f:
        letter_config = json.load(f)

    try:
        email_subject = letter_config["subject"]
        email_from = letter_config["from"]
        recipTitle = letter_config["recipientTitle"]["title"]
        if len(recipTitle) > 0:
            lastNameOnly = letter_config["recipientTitle"]["lastNameOnly"]
        else:
            lastNameOnly = False
    except Exception as e:
        print(e)
        print("Fail reading letter config file!\nPlease check your config.json")
        exit()

    return [email_subject, email_from, recipTitle, lastNameOnly]


def attach_files(msg, path):
    '''This method will attach all the files in the ./attach folder.'''
    attachments = os.listdir(path)
    for a in attachments:
        attachment = MIMEApplication(
            open(os.path.join(path, a), "rb").read(), Name=a)
        attachment['Content-Disposition'] = f'attachment; filename="{a}"'
        msg.attach(attachment)


def send_mail(email, server):
    try:
        server.sendmail(email["From"], email["To"], email.as_string())
    except:
        print(f'failed to send email to {email["To"]}')
        return False

    print(f'Sent mail to {email["To"]}')
    return True


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


def handle_bounce_backs(retr_n, userid, password):
    '''show help message if emails are bounced back, this usually happens when trying to email a wrong school email address'''
    print("checking for bounce-backs...")
    time.sleep(3)  # wait for bounce back
    
    # connect to pop3 server
    pop3 = poplib.POP3_SSL('msa.ntu.edu.tw', 995)
    pop3.user(userid)
    pop3.pass_(password)

    # retrieve last n emails
    _, mails, _ = pop3.list()
    email_contents = [pop3.retr(i)[1]
                      for i in range(len(mails), len(mails) - retr_n, -1)]

    # Concat message pieces:
    email_contents = [b'\r\n'.join(mssg).decode('utf-8')
                      for mssg in email_contents]
    
    # Parse message into an email object:
    email_contents = [EmailParser().parsestr(content, headersonly=True)
                      for content in email_contents]

    bounced_list = []

    for content in email_contents:
        if not re.match('(Delivery Status Notification)|(Undelivered Mail Returned to Sender)', content['subject']):
            continue

        for part in content.walk():
            if part.get_content_type():
                body = str(part.get_payload(decode=True))
                
                # match for email addresses
                bounced = re.findall(
                    '[a-z0-9-_\.]+@[a-z0-9-\.]+\.[a-z\.]{2,5}', body)

                if bounced:
                    bounced = str(bounced[0].replace(userid, ''))
                    if bounced == '':
                        break

                    bounced_list.append(bounced)

    if len(bounced_list) > 0:
        print('emails sent to these addresses are bounced back (failed):')
        for address in bounced_list:
            print(f'\t{address},')
        print('Please check these emails.')
    else:
        print('No bounce-backs found, all emails are delivered successfully')

    return len(bounced_list)


def main(opts, args):
    # choose the receiver list
    email_root_path = Path(f'letters/{args[0]}')
    email_list_path = os.path.join(email_root_path, Path("recipients.csv"))
    email_config_path = os.path.join(email_root_path, Path("config.json"))
    email_content_path = os.path.join(email_root_path, Path("content.html"))
    email_attachments_path = os.path.join(email_root_path, Path("attachments"))

    # load letter config
    [email_subject, email_from, recipTitle,
        lastNameOnly] = load_letter_config(email_config_path)

    # load email account info
    userid, password = load_account_config()

    # load recipient list
    if opts.test:
        recipients = [["王小明", f'{userid}@ntu.edu.tw']]
    else:
        recipients = load_recipient_list(email_list_path)

    recipients = handle_recipient_title(recipients, recipTitle, lastNameOnly)

    # load content as template string
    email_html = Template(Path(email_content_path).read_text(encoding="utf-8"))

    smtp = connectSMTP(userid, password)
    sent_n = 0

    if not opts.test:
        isSure = input(
            f'about send emails to {len(recipients)} recipients, are you sure? [yn]:\n')
        if isSure == 'y' or isSure == 'Y':
            pass
        else:
            print('Please check the email in test mode before you send it.')
            exit()

    for recipient in recipients:
        email = MIMEMultipart()
        email["Subject"] = email_subject
        email["Date"] = formatdate(localtime=True)

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

        # attach enerything in '/attachments' folder
        if(opts.attach):
            attach_files(email, email_attachments_path)

        success = send_mail(email, smtp)
        sent_n += 1 if success else 0
        server_rest(sent_n)

    smtp.quit()

    bounced_n = handle_bounce_backs(len(recipients), userid, password)
    
    print(f'{sent_n - bounced_n}/{len(recipients)} mails sent successfully{" in test mode" if opts.test else ""}.')


if __name__ == '__main__':
    optParser = OptionParser()
    optParser.set_usage(
        "python mailer_invite.py <LETTER>\nLETTER is the name of the folder in the 'letters' folder where your email lives")
    optParser.add_option("-a", "--attach", dest="attach", default=False, action="store_true",
                         help="attach files in 'letters/LETTER/attachments' folder to the email")
    optParser.add_option("-t", "--test", dest="test", default=False, action="store_true",
                         help="send email in test mode (to yourself)")
    opts, args = optParser.parse_args()

    if len(args) == 0:
        print("please specify the letter you want to send")
        exit()

    main(opts, args)
