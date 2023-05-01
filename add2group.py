#!/bin/env python3

from telethon import errors
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser
from telethon.tl.functions.channels import InviteToChannelRequest
from datetime import datetime, timedelta
from pymongo import MongoClient
import configparser
import os, sys
import csv
import traceback
import time
import random
import asyncio

myclient  = MongoClient("mongodb://localhost:27017/")
mydb      = myclient["dbtelegram"]
dbmembers = mydb["members"]

re="\033[1;31m"
gr="\033[1;32m"
cy="\033[1;36m"

def update_member (user_id, tgt_group, tgt_group_id, error):
    #print("update_member:", user_id, tgt_group, tgt_group_id, error)
    if error == 'refused':
        document = {"refused": "yes"}
    elif error == 'too_many_grps':
        document = {"too_many_grps": "yes"}
    elif error == 'invalid_id':
        document = {"invalid_id": "yes"}
    else:
        now = datetime.now()
        current_time = now.strftime("%Y/%m/%d %H:%M")
        document = {
            "tgt_group": tgt_group,
            "tgt_group_id": int(tgt_group_id),
            "assign_time": current_time,
        }

    dbmembers.update_one({'user_id': user_id}, {'$set': document})

# For test
#update_member(6011653050, '约法三章', 1678832047, '', '')
#update_member(1915869296, '约法三章', 1678832047, 'yes', '')
#sys.exit()

cpass = configparser.RawConfigParser()
cpass.read('config.data')

try:
    api_id = cpass['cred']['id']
    api_hash = cpass['cred']['hash']
    phone = cpass['cred']['phone']
    client = TelegramClient(phone, api_id, api_hash)
except KeyError:
    print(re+"[!] run python3 setup.py first !!\n")
    sys.exit(1)

client.connect()
if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input(gr+'[+] Enter the code: '+re))

chats = []
last_date = None
chunk_size = 200
groups=[]

result = client(GetDialogsRequest(
             offset_date=last_date,
             offset_id=0,
             offset_peer=InputPeerEmpty(),
             limit=chunk_size,
             hash = 0
         ))
chats.extend(result.chats)

for chat in chats:
    try:
        if chat.megagroup== True:
            groups.append(chat)
    except:
        continue

group_title = sys.argv[1]

i=0
for group in groups:
    if group.title == group_title:
        target_group_id = group.id
        target_group_access_hash = group.access_hash
        print(gr+'Target group: ['+cy+str(i)+gr+']'+cy+' - '+group.title)
        print('id:', target_group_id, '; access_hash:', target_group_access_hash)
        break
    i+=1

target_group_entity = InputPeerChannel(target_group_id, target_group_access_hash)

total_users = len(list(dbmembers.find()))

# Search database to find not assigned members
mysearch = {"refused": {'$ne': "yes"},
            "too_many_grps": {'$ne': "yes"},
            "invalid_id": {'$ne': "yes"},
            "tgt_group": {'$exists': False}}
users = dbmembers.find(mysearch)

if not users:
    print("Can't find any members to add!")
    sys.exit()
else:
    available_users = len(list(users))
    print("Total members: %d, members can be added: %d" % (total_users, available_users))

mode = 1
while True:
    user = dbmembers.find_one(mysearch)
    user_id = int(user['user_id'])
    access_hash = int(user['access_hash'])
    time.sleep(1)
    try:
        print ("Adding", user_id)
        if mode == 1:
            user_to_add = client.get_input_entity(user['username'])
        elif mode == 2:
            print("user_id:", user_id, "user_hash:", access_hash)
            user_to_add = InputPeerUser(user_id, access_hash)
        client(InviteToChannelRequest(target_group_entity,[user_to_add]))
        update_member(user_id, group_title, target_group_id, '')
        print(gr+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
    except errors.PeerFloodError:
        print(re+"[!] Getting Flood Error from telegram. \n[!] Script is stopping now. Please try again after some time.")
        sys.exit()
    except errors.UserBannedInChannelError:
        print(re+"[!] You're banned from sending messages in supergroups/channels. \n[!] Script is stopping now. Please try again after some time.")
        sys.exit()
    except errors.UserPrivacyRestrictedError:
        print(re+"[!] The user's privacy settings do not allow you to do this. Skipping.")
        # Mark this member to be refused
        update_member(user_id, group_title, target_group_id, 'refused')
        print(re+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
    except errors.UserChannelsTooMuchError:
        print(re+"[!] One of the users you tried to add is already in too many channels/supergroups (caused by InviteToChannelRequest).")
        # Mark this member to be too_many_grps
        update_member(user_id, group_title, target_group_id, 'too_many_grps')
        print(re+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
        continue
    except errors.UserIdInvalidError:
        print(re+"[!] Invalid object ID for a user. Make sure to pass the right types (caused by InviteToChannelRequest).")
        # Mark this member to be too_many_grps
        update_member(user_id, group_title, target_group_id, 'invalid_id')
        print(re+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
        continue
    except errors.FloodWaitError as e:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        next_time_sec = now + timedelta(seconds=e.seconds)
        next_time = next_time_sec.strftime("%H:%M:%S")
        print(re+"Have to sleep", e.seconds, "seconds, start from:", current_time, "until", next_time)
        time.sleep(e.seconds)
        continue
    except errors.ChatAdminRequiredError:
        print(re+"[!] Invalid permissions used for the channel or group (caused by InviteToChannelRequest)")
        print(re+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
        continue
    except:
        traceback.print_exc()
        print(re+"[!] Unexpected Error")
        print(re+"[+] Waiting for 60-120 Seconds...")
        time.sleep(random.randrange(60, 120))
        continue
