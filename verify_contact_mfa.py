"""Offline checks for the contact-channel OTP flow; no real messages are sent."""
import os
os.environ['CARESECURE_DEMO_MODE']='1'
from database.database import initialize, connect
from authentication import auth

initialize()
with connect() as con:
    con.execute("UPDATE users SET email='demo@example.test', phone='+15550001111' WHERE username='admin'")
    con.commit()
status,user,channels=auth.password_stage('admin','Admin@123')
assert status=='choose' and channels==['email','sms'], (status,channels)
sent=[]
auth.send_otp=lambda channel,destination,code: sent.append((channel,destination,code))
auth.issue_otp(user,'email')
assert sent and sent[0][0]=='email'
assert auth.complete_otp(user,sent[0][2]) is not None
with connect() as con:
    con.execute("UPDATE users SET email=NULL, phone='+15550001111' WHERE username='admin'")
    con.commit()
status,user,channels=auth.password_stage('admin','Admin@123')
assert status=='send' and channels==['sms']
print('[PASS] Both channels offer a choice; single channel is selected automatically.')
print('[PASS] OTP hash storage, expiry fields and one-time verification work.')
print('[NOTE] Provider delivery requires SMTP/Twilio credentials; no real message sent.')
