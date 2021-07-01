##########################################################################
# File:         mailer_invite.py                                         #
# Purpose:      Automatic send 專題說明會 invitation mails to professors   #
# Last changed: 2015/06/21                                               #
# Author:       Yi-Lin Juang (B02 學術長)                                 #
# Edited:       2021/07/01 Eleson Chuang (B08 Python大佬)                 #
#               2018/05/22 Joey Wang (B05 學術長)                         #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import sys
import time
import re
import configparser as cp

#write your letter in letter.txt
with open('letter.txt', 'r',encoding='utf-8') as infile:
    text = infile.read()

#choose the receiver list
email_list = 'test_list'

#load email account info
config = cp.ConfigParser()
config.read('account.ini')  #reading sender account information
try:
    user = config['ACCOUNT']['user']
    pw = config['ACCOUNT']['pw']
except:
    print('Reading config file fail!\nPlease check the config file...')
    exit()

def connectSMTP():
    # Send the message via NTU SMTP server.
    #For students ID larger than 09 
    s = smtplib.SMTP_SSL('smtps.ntu.edu.tw', 465)
    #For students ID smaller than 08 i.e. elders
    #s = smtplib.SMTP('mail.ntu.edu.tw', 587)
    s.set_debuglevel(False)
    #Uncomment this line to go through SMTP connection status.
    s.ehlo()
    if s.has_extn('STARTTLS'):
        s.starttls()
        s.ehlo()
    s.login(user, pw)
    print("SMTP Connected!")
    return s

def disconnect(server):
    server.quit()

def read_list(file_name):
    obj = list()
    with open(file_name,'r',encoding='utf-8') as f:
        for line in f:
            t = line.split()
            if t is not None:
                obj.append(t)
    return obj

def send_mail(msg, server):
    server.sendmail(msg['From'], msg['To'] , msg.as_string())
    print("Sent message from {} to {}".format(msg['From'], msg['To']))

# recipient  = recipient's email address
sender = "{}@ntu.edu.tw".format(user)
# 2. Sender email address (yours).
recipients = read_list(email_list)       
## Uncomment this line to send to yourself. (for TESTING)
server = connectSMTP()
count = 0

for recipient in recipients:
    if count % 10 == 0 and count > 0:
        print('{} mails sent, resting...'.format(count))
        time.sleep(10)  #for mail server limitation
    msg = MIMEMultipart()
    msg['Subject'] = "【主旨haha】"#remember to change
    msg['From'] = sender
    msg.preamble = 'Multipart massage.\n'
    #letter content
    part =  MIMEText("{}教授您好：\n\n{}".format(recipient[0][0],text))
    msg.attach(part)
    #Reading attachment, put file_path in args
    if len(sys.argv) > 1:
        part = MIMEApplication(open(str(sys.argv[1]),"rb").read())
        if len(sys.argv) > 2:
            attachname = str(sys.argv[2])
        else:
            attachname = str(sys.argv[1])
        part.add_header('Content-Disposition', 'attachment', filename=attachname)
        msg.attach(part)
    msg['To'] = recipient[1]
    send_mail(msg, server)
    count += 1

disconnect(server)
print("{} mails sent. Exiting...".format(count))