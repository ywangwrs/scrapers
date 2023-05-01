#!/usr/bin/env python3

from pymongo import MongoClient
import csv

myclient  = MongoClient("mongodb://localhost:27017/")
mydb      = myclient["dbtelegram"]
dbmembers = mydb["members"]

input_file = 'members.csv'
with open(input_file, encoding='UTF-8') as f:
    rows = csv.reader(f,delimiter=",",lineterminator="\n")
    next(rows, None)
    for row in rows:
        # if anyone of username, id, access_hash and name is empty, drop it
        for i in 0,1,2,3:
            if row[i] == '':
                continue

        # if this user exists in db, drop it
        mysearch = {"user_id": int(row[1])}
        cursors = dbmembers.find(mysearch)
        result = list(cursors)
        if len(result) != 0:
            continue

        document = {
            "username": row[0],
            "user_id": int(row[1]),
            "access_hash": int(row[2]),
            "name": row[3],
            "src_group": row[4],
            "src_group_id": int(row[5]),
        }

        print('New member %s inserted.' % row[0])
        dbmembers.insert_one(document)
