# 學術部寄信程式

## Requirements

- **Python Interpreter**
  - python 3.X 64bit
- **Packages**
  - 不使用 GUI: 套件皆有內建，不需額外安裝
  - 使用 GUI: 依照 requirement.txt 說明

## Usage

- **請不要把信件內容push上來**，負責人可以寫完信之後zip好傳給其他人
- 請複製 letters 資料夾中的 template 來創建新的信件
- content.html 放信件內文
  - **記得在內文中加入$recipient**，此處會被替換成收件人，及其稱謂
- recipients.csv 收件人及信箱名單
  - 可以用 excel 編輯 csv 檔案，格式詳見 template
  - **第一欄填收件人姓名，第二欄填收件人信箱**
  - 如果是臺大的信箱，可以不用填 '@ntu.edu.tw'，會自動加上去
- config.json 裡面可以修改信件設定
  - subject 為主旨
  - from 為寄件人名稱顯示，如果 from 留空白會顯示你原本的名稱
  - recipientTitle 裡面的 Title 不是空字串則會把這個 title 接到收件人姓名後面
  - lastNameOnly 如果是 true，使用「姓氏+稱謂」，反之則使用「全名+稱謂」
- attachments 資料夾裡放要附加的檔案
  - 執行時使用-a 選項來附加，預設不附加檔案，下面有範例
  - 如果你很在乎順序的話，取檔名的時候記得要確認順序
- **account-default.ini的檔名改成account.ini** 裡面放自己的計中帳密
  - **把檔案寄給別人時這個要改掉，不然大家都知道了**

## GUI Usage
<img src="https://i.imgur.com/reuBmUU.jpg" width="100%">

### Functionality

- **Save** (儲存信件 / User 資訊)
  - 一般存檔直接按下即可，信件內容與 User 資訊皆會寫入
  - 若要新建信件，在 letter 欄位指定信件資料夾名稱後再按下
- **Load** (載入信件)
  - 若 letter 欄位為空或該信件不存在，會開啟視窗選擇信件資料夾
  - 若 letter 欄位中的信件正確則會正常載入
- **Send** (寄出信件)
  - 按下後會暫時無法操作(我還沒做 multi thread)，請靜待執行完成
  - 預設為 Test mode 與 No attach

## Run (No GUI)

    python main.py LETTER
    python3 main.py LETTER

LETTER is the name of the folder in the 'letters' folder where your email lives

### Options

    -h, --help    show help message and exit
    -a, --attach  attach files in 'letters/LETTER/attachments' folder to the email
    -t, --test    send email in test mode (to yourself)

## Run (With GUI)

    python main.py
    python3 main.py

## Examples

    python3 main.py template -t
    python main.py letter1 -a
