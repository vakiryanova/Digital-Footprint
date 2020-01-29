#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import classroom as lib
from datetime import datetime, timezone
from pymongo import MongoClient
import configparser
import logging
logger=lib.logger

def main():
    #подключение к БД
    config = configparser.ConfigParser()
    config.read('auth/config.ini')
    username = config['DB']['User']
    password = config['DB']['Password']
    ip = config['DB']['IP']
    client = MongoClient('mongodb://%s:%s@%s' % (username, password, ip))
    col = client.app.classroom

    #проверка даты на корректный формат
    def date_check(ddate, values, string):
        rdate = None
        if len(ddate) == 1:
            try:
                rdate = int(ddate)
                if rdate not in values:
                    logger.log(logging.WARNING, 'неправильная дата '+string)
                    return None
                return rdate
            except:
                logger.log(logging.WARNING, 'неправильная дата '+string)
                return None
        else:
            try:
                rdate = datetime.strptime(ddate, "%d-%m-%Y") #.date()
                return rdate
            except:
                logger.log(logging.WARNING, 'неправильная дата '+string)
                return None

    #устанавливаем временной период, данные из которого хотим загрузить (подробнее в readme)
    date_from = date_check(config['TIME PERIOD']['from'], [0, 1], 'от')
    date_to = date_check(config['TIME PERIOD']['to'], [1], 'до')
    if date_from == None or date_to == None:
        exit(1)
    if date_from == -1:
        date_from = 0
    if date_from == 0:
        kostyl = -1
    else:
        kostyl = date_from
    logger.log(logging.INFO, 'временной период: с {} по {}'.format(kostyl, date_to))
    #загружаем курсы
    courses = lib.get_courses()

    #загружаем студентов
    students=[]
    count = 1
    for course in courses:
        s = None
        s = lib.get_students(course, count)
        for student in s:
            student['courseIds'] = []
            student['courseIds'].append(course['id'])
        if s!=[]:
            [students.append(i) for i in s]
        course['courseWork'] = lib.get_courseWork(course, count)
        count+=1

    #составляем список уникальных имейлов
    emails = []
    for student in students:
        emails.append(student['emailAddress'])
    emails = set(emails)

    #составляем список студентов без повторений
    new_students = []
    for id in emails:
        #print(id)
        doubles = [item for item in students if item['emailAddress'] == id]
        for j in range(1, len(doubles)):
            doubles[0]['courseIds'].append(doubles[j]['courseIds'][0])
        new_students.append(doubles[0])
    count = 1
    logger.log(logging.INFO, 'всего {} студентов'.format(len(new_students)))

    for student in new_students:
        from pprint import pprint
        pprint(student)
        student['courses'] = lib.get_data_by_student(student, courses, date_from, date_to, count)
        if student['courses'] != []:
            col.insert_one(student)
        student['courses'] = None
        count += 1

if __name__ == '__main__':
    main()
