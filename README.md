# 學術部寄信程式

### Requirements
- python 3.X 64bit 
- 套件皆有內建，不需額外安裝

### Files
* mailer_invite.py 寄信程式<br>
  * 若是08以上請把40行去註解，並註解掉38行。<br>
    若是09以下則不需更動。
  * **記得改第98行的信件主旨！**

- letter.txt 放信件內文

* account.ini 裡面改成自己的計中帳密<br>
	* **把檔案寄給別人時這個要改掉，不然大家都知道了XD**

- test_list 收件人及信箱名單<br>
  - 收件人和信箱是空白分隔。所以姓名如果是2個字，姓和名之間不能有空格。
  - 名單格式舉例：莊詠翔 b08901093@ntu.edu.tw
  - 如果test_list只有姓名和學號兩欄，那可以對mailer_invite.py 第129行的 msg["To"] 動手腳，自己加上"@ntu.edu.tw"

### Features
* Sending Emails without Attachments
	* To run(Linux): python3 mailer_invite.py
	* To run(Win  ): python mailer_invite.py
	
- Sending Emails with attachments
	- METHOD1: 
		This method will attach all the files in the ./attach folder.
		If you need the files be attached in order (especially images), add numbers in front of their filenames.
		- To run(Linux): python3 mailer_invite.py
		- To run(Win  ): python mailer_invite.py
	
	* METHOD2:
		By sys.argvs. Make sure your attachment is under the current directory.
		No need to modify filenames. The files would be attached in the order as expected.
		* To run(Linux): python3 mailer_invite.py Classic.png Mexican.png
		* To run(Win  ): python3 mailer_invite.py Classic.png Mexican.png
	

### Debug Info
- 若遇到[SMTP主機相關Error](https://docs.python.org/zh-tw/3/library/smtplib.html)
	- 搜尋 ntu mail SMTP主機還有連接埠(以下以09以後為例)
		- https://jsc.cc.ntu.edu.tw/ntucc/email/mailsoftwaresetup.html
	- 在第38行
	- `s = smtplib.SMTP_SSL(HOST, PORT)`
	- 更改成新的主機(HOST)和連接埠(PORT)
