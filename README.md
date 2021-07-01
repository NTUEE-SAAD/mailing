# 學術部專題說明會寄信程式

- 裝python 3.X 64bit 
- 套件皆有內建，不需額外安裝
- 在mailer_invite.py中
	- 若是08以上請把40行去註解，並註解掉38行
	- 若是09以下則不需更動
- 找模板信，把要寄的信放在letter.txt，把署名寫上去
- code裡記得改主旨，和把account.ini裡面改成自己的帳密(阿小心如果要把檔案寄給別人時這個要改掉，不然大家都知道了XD)
- 寄信的名單放在test list裡，注意格式(建議先放自己或認識的寄一次看看信有沒有問題)
- 名單格式如：莊詠翔 b08901093@ntu.edu.tw
- to run: python3 mailer_invite.py


- 若遇到[SMTP主機相關Error](https://docs.python.org/zh-tw/3/library/smtplib.html)
	- 搜尋 ntu mail SMTP主機還有連接埠(以下以09以後為例)
		- https://jsc.cc.ntu.edu.tw/ntucc/email/mailsoftwaresetup.html
	- 在第38行
	- `s = smtplib.SMTP_SSL(HOST, PORT)`
	- 更改成新的主機(HOST)和連接埠(PORT)
