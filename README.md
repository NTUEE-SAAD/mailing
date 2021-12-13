# 學術部寄信程式

## Requirements

- python 3.X 64bit
- 套件皆有內建，不需額外安裝

## Usage

- 請複製letters資料夾中的template來創建新的信件
- content.html 放信件內文
- recipients.csv 收件人及信箱名單
  - 可以用excel編輯csv檔案，格式詳見template
  - 第一欄填收件人姓名，第二欄填收件人信箱
  - 如果是臺大的信箱，可以不用填 '@ntu.edu.tw'，會自動加上去
- config.json 裡面可以修改信件主旨以及寄件人名稱顯示，如果from留空白會顯示你原本的名稱
- account.ini 裡面改成自己的計中帳密
  - **把檔案寄給別人時這個要改掉，不然大家都知道了**

## Run

    python mailer_invite.py LETTER
    python3 mailer_invite.py LETTER

LETTER is the name of the folder in the 'letters' folder where your email lives

### Options

    -h, --help    show help message and exit
    -a, --attach  attach files in ./attach folder to the email
    -t, --test    send email in test mode (to yourself)

## Examples

    python mailer_invite.py template -t
    python mailer_invite.py letter1

## Features

- Sending Emails with attachments
  This method will attach all the files in ./attach folder.
  If you need the files be attached in order (especially images), add numbers in front of their filenames.
