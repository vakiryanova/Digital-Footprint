#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from auth import auth
import logs
from datetime import datetime
from datetime import date
import logging
from googleapiclient.errors import HttpError

#аутентификация
service = auth.get_service()

#инициализация логгинга
logger = logs.logger_init()

def get_course(courseId):
    return service.courses().get(id=courseId).execute()

def get_courses(studentId = None):
    """
    Принимает: -
    Вовзращает: список курсов, к которым есть доступ с используемым токеном
                пользователя.
    """
    if studentId==None:
        courses = service.courses().list().execute().get('courses', [])
        if courses == []:
            logger.log(logging.INFO, 'нет курсов')
        else:
            logger.log(logging.INFO, 'загружено {} курсов'.format(len(courses)))
    else:
        courses = service.courses().list(studentId=studentId).execute().get('courses', [])

    for course in courses:
        course['creationTime'] = to_timestamp(course['creationTime'])
        course['updateTime'] = to_timestamp(course['updateTime'])

    return courses



def get_teachers(course):
    """
    Принимает: один курс (или только поля курса id и name).
    Вовзращает: список преподавателей курса.
    """
    teachers = []
    flag = False
    token = ''
    while not flag:
        result = service.courses().teachers().list(courseId=course['id'], pageToken=token).execute()
        teacher = result.get('teachers', [])
        [teachers.append(i['profile']) for i in teacher]
        token = result.get('nextPageToken', [])
        if not token:
            flag = True
    logger.log(logging.INFO, 'загружено {} преподавателей с курса {} ({})'.format(len(teachers), course['name'], course['id']))

    for teacher in teachers:
        for i in ['permissions', 'verifiedTeacher']:
            if i in teacher.keys():
                teacher.pop(i)
    return teachers



def get_students(course, count = 1):
    """
    Принимает: один курс (или только поля курса id и name).
    Вовзращает: список студентов курса.
    """
    #загрузка данных с API
    students = []
    flag = False
    token = ''
    while not flag:
        result = service.courses().students().list(courseId=course['id'], pageToken=token).execute()
        student = result.get('students', [])
        [students.append(i['profile']) for i in student]
        token = result.get('nextPageToken', [])
        if not token:
            flag = True

    #логгинг
    if students == []:
        logger.log(logging.INFO, '{}) на курсе {} ({}) нет студентов'.format(count, course['name'], course['id']))
    else:
        logger.log(logging.INFO, '{}) загружено {} студентов с курса {} ({})'.format(count, len(students), course['name'], course['id']))

    #удаляем ненужные ключи, добавляем требуемые
    for student in students:
        if 'givenName' in student['name'].keys():
                student['firstName'] = student['name']['givenName']
        else:
                student['firstName'] = '-'

        if 'familyName' in student['name'].keys():
                student['lastName'] = student['name']['familyName']
        else:
                student['lastName'] = '-'
        for i in ['permissions', 'verifiedTeacher', 'photoUrl', 'name']:
            if i in student.keys():
                    student.pop(i)

    return students



def get_courseWork(course, count = 1):
    """
    Принимает: один курс (или только поля курса id и name).
    Вовзращает: список заданий курса.
    """
    courseWork = []
    flag = False
    token = ''
    while not flag:
        result = service.courses().courseWork().list(courseId=course['id'], pageToken=token).execute()
        work = result.get('courseWork', [])
        [courseWork.append(i) for i in work]
        token = result.get('nextPageToken', [])
        if not token:
            flag = True

    if courseWork == []:
        logger.log(logging.INFO, '{}) на курсе {} ({}) нет заданий'.format(count, course['name'], course['id']))
    else:
        logger.log(logging.INFO, '{}) загружено {} заданий с курса {} ({})'.format(count, len(courseWork), course['name'], course['id']))

    for work in courseWork:
        work['creationTime'] = to_timestamp(work['creationTime'])
        work['updateTime'] = to_timestamp(work['updateTime'])

    return courseWork



def get_cW_and_sS_by_student(courseWork, student, date_from=0, date_to=1): #get_cW_and_sS_by_student()
    """
    Принимает: список заданий курса (courseWork) и id студента.
    Возвращает: список заданий, которые доступны этому студенту и его работы по ним.

    *Некоторые задания курса индивидуальны, а значит могут быть не доступны
     студенту, информацию которого мы запрашиваем.
    """

    def download_submissions(courseWorkId):
        try:
            res = service.courses().courseWork().studentSubmissions().list(courseId=courseId,
                                                                          courseWorkId=courseWorkId,
                                                                          userId=student['id']).execute()
            res = res.get('studentSubmissions',[])[0]
            change_submsissions_date_format([res])
            res1 = select_data_by_date([res], date_from, date_to)
            if res1==None:
                return []
            else:
                res1 = checkMissingKeys(res1, submissionsMissingKeys)
                return res1
        except HttpError as err:
            print(err)
            logger.log(logging.ERROR, err)

    courseWorkMissingKeys = {'assigneeMode':'ALL_STUDENTS'}
    submissionsMissingKeys = {'late': False, 'assignedGrade': -1}

    courseWork=checkMissingKeys(courseWork, courseWorkMissingKeys)
    courseId = courseWork[0]['courseId']
    coursework = []

    for task in courseWork:
        #если задание не для всех студентов, а для некоторых
        if task['assigneeMode']=='INDIVIDUAL_STUDENTS':
            #и текущий студент имеет доступ к этому заданию
            if student['id'] in task['individualStudentsOptions']['studentIds']:
                #загружаем и сохраняем информацию о работе
                result = download_submissions(task['id'])
                if result!=[]:
                    coursework.append(task)
                    coursework[-1]['studentSubmissions'] = result
        else: #если задание для всех студентов
            result = download_submissions(task['id'])
            if result!=[]:
                coursework.append(task)
                coursework[-1]['studentSubmissions'] = result
    return coursework

def get_studentSubmissions_by_student(courseWork, studentId, date_from=0, date_to=1):
    """
    Принимает: список заданий курса (courseWork) и id студента.
    Возвращает: список работ студента по тем заданиям, которые ему доступны

    *Некоторые задания курса индивидуальны, а значит могут быть не доступны
     студенту, информацию которого мы запрашиваем.
    """

    def download_submissions(courseWorkId):
        try:
            res = service.courses().courseWork().studentSubmissions().list(courseId=courseId,
                                                                          courseWorkId=courseWorkId,
                                                                          userId=studentId).execute()
            res = res.get('studentSubmissions',[])[0]
            change_submsissions_date_format([res])
            res1 = select_data_by_date([res], date_from, date_to)
            if res1==None:
                return []
            else:
                res1 = checkMissingKeys(res1, submissionsMissingKeys)
                return res1
        except HttpError as err:
            print(err)
            logger.log(logging.ERROR, err)

    courseWorkMissingKeys = {'assigneeMode':'ALL_STUDENTS'}
    submissionsMissingKeys = {'late': False, 'assignedGrade': -1}

    courseWork=checkMissingKeys(courseWork, courseWorkMissingKeys)
    courseId = courseWork[0]['courseId']
    studentSubmissions = []

    for task in courseWork:
        #если задание не для всех студентов, а для некоторых
        if task['assigneeMode']=='INDIVIDUAL_STUDENTS':
            #и текущий студент имеет доступ к этому заданию
            if studentId in task['individualStudentsOptions']['studentIds']:
                #загружаем и сохраняем информацию о работе
                result = download_submissions(task['id'])
                if result!=[]:
                    #coursework.append(task)
                    #coursework[-1]['studentSubmissions'] = result
                    studentSubmissions.append(result[0])
        else: #если задание для всех студентов
            result = download_submissions(task['id'])
            if result!=[]:
                studentSubmissions.append(result[0])

    return studentSubmissions


def get_studentSubmissions_by_courseWork(course, courseWork):
    """
    Принимает: id курса и id задания.
    Вовзращает: список работ студентов (studentSubmissions) по этому заданию.
    """
    studentSubmissions = []
    flag = False
    token = ''
    while not flag:
        result = service.courses().courseWork().studentSubmissions().list(
                courseId=courseId,
                courseWorkId=courseWorkId,
                pageToken=token).execute()
        subm = result.get('studentSubmissions', [])
        [studentSubmissions.append(i) for i in subm]
        token = result.get('nextPageToken', [])
        if not token:
            flag = True

    if studentSubmissions == []:
        logger.log(logging.WARNING, 'на курсе {} нет студентов'.format(course['id']))
    else:
        logger.log(logging.INFO, 'для задания {} загружено {} работ'.format(courseWork['id'], len(studentSubmissions)))

    change_submsissions_date_format(studentSubmissions)

    for item in studentSubmissions:
        if 'updateTime' in item.keys():
            item['updateTime'] = to_timestamp(item['updateTime'])

    return studentSubmissions

def get_data_by_students(col, all_courses, students, date_from=0, date_to=1):
    count = 0 #счетчик студентов для логгинга

    for student in students:
        #logger.log(logging.INFO, 'student {} {}'.format(student['emailAddress'], student['id']))

        #добавляем информацию о времени загрузки
        if date_from == 1:
            student['dateFrom'] = datetime.combine(date.today(), datetime.min.time())
        else:
            student['dateFrom'] = date_from
        if date_to == 1:
            student['dateTo'] = datetime.combine(date.today(), datetime.min.time())
        else:
            student['dateTo'] = date_to

        #из всех курсов выбираем те, на которые подписан студент
        courses = [i for i in all_courses if i['id'] in student['courseIds']]

        #загружаем данные по курсам, оставляем только те курсы,
        #на которых была активность в указанный период
        courses_new = []
        for course in courses:
            if course['courseWork']!=[]:
                try:
                    course['courseWork'] = get_cW_and_sS_by_student(course['courseWork'], student['id'], date_from, date_to)
                    logger.log(logging.INFO, '{}. загружены данные для {}'.format(count, student['emailAddress']))
                except:
                    logger.log(logging.ERROR,
                                   '{}. не удается загрузить информацию о работах\
                                   {}'.format(count, student['emailAddress']))
                courses_new.append(course)
        count+=1

        #добавляем в БД данные о студенте
        if courses_new != [] and col != None:
            student['data'] = courses_new
            student.pop('courseIds')
            col.insert_one(student)

    #return students


def get_data_by_student(student, all_courses, date_from=0, date_to=1, count=1):
    """
    Принимает: запись (dict) о студенте, список курсов и даты.
    Возвращает: список курсов, заданий, работ этого студента.
    """
    #добавляем информацию о времени загрузки
    if date_from == 1:
        student['dateFrom'] = datetime.combine(date.today(), datetime.min.time())
    elif date_from == 0:
        student['dateFrom'] = -1
    else:
        student['dateFrom'] = date_from
    if date_to == 1:
        student['dateTo'] = datetime.combine(date.today(), datetime.min.time())
    else:
        student['dateTo'] = date_to

    #из всех курсов выбираем те, на которые подписан студент
    courses = [i for i in all_courses if i['id'] in student['courseIds']]

    #загружаем информацию по каждому курсу
    courses_new = []
    for course in courses:
        if course['courseWork']!=[]:
                try:
                    course['courseWork'] = get_cW_and_sS_by_student(course['courseWork'], student, date_from, date_to)
                    logger.log(logging.INFO, '{}. загружены данные для {}'.format(count, student['emailAddress']))
                    courses_new.append(course)
                except:
                    logger.log(logging.ERROR,
                                   '{}. не удается загрузить информацию о работах\
                                   {}'.format(count, student['emailAddress']))
    return courses_new


def checkKeys(data, keys):
    """
    Принимает: исходную информацию (list of dict); список полей, которые
               должны присутствоовать в структуре, и их значений по умолчанию (dict).
    Возвращает: исходные данные, но только с требуемыми полями.

    *Добавляет недостающие и удаляет лишние поля
    """
    data = checkMissingKeys(data, keys)

    for item in data:
        for key in item.keys():
            if key not in keys.keys():
                item.pop(key)

    return data


def checkMissingKeys(data, missingValues):
    """
    Принимает: исходную информацию (list of dict или dict); список полей, которые
               должны присутствоовать в структуре, и их значений по умолчанию (dict).
    Возвращает: исходные данные, но с новыми полями.

    *Добавляет недостающие поля
    """
    if type(data) == list:
        for key in missingValues.keys():
            for item in data:
                if key not in item.keys():
                    item[key] = missingValues[key]
    else:
        for key in missingValues.keys():
            if key not in data.keys():
                data[key] = missingValues[key]
    return data


def state_or_grade(element):
    """
    Принимает: 1 элемент из истории изменений работы (submissionHistory).
    Возвращает: строку state или grade, в зависимости от того, к какому типу
                относится элемент.
    """
    if 'stateHistory' in element.keys():
        return 'state'
    else:
        return 'grade'



def select_data_by_date(studentSubmissions, d_from=0, d_to=1):
    """
    Принимает: список работ студента (studentsSubmissions) и временной период
               (даты в формате datetime.date).
    Возвращает: список работ, который были изменены в этот период.

    1) Можно задать не обе даты, а только одну.
    2) В возвращаемом списке работ, в графах submissionHistory содержится не
       вся история изменений, а лишь те события, которые произошли в указанный
       период.
    """

    if d_from==0 and d_to==1:
#        logger.log(logging.INFO, 'вся история')
        return studentSubmissions

    if type(d_from)!=date and d_from not in [0,1]:
#        logger.log(logging.WARNING, 'дата "от" должна быть в формате datetime.date или "0" или "1"')
        return studentSubmissions

    if type(d_to)!=date and d_to!=1:
#        logger.log(logging.WARNING, 'дата "до" должна быть в формате datetime.date или "1"')
        return studentSubmissions

    if d_from!=0 and d_to!=1 and d_from > d_to:
        logger.log(logging.WARNING, 'дата "от" должна быть меньше даты "до"')
        return studentSubmissions


    if d_from == 1:
        d_from=datetime.now().date()

    #проверка на вхождения работ в заданный диапазон дат
    new_data = []
    for work in studentSubmissions:
        buf = []
        if work['state']!='NEW':
            for item in work['submissionHistory']:
                el_type = state_or_grade(item)
                curr = item[el_type+'History']

                flag = False
                if d_from != 0:
                    if (curr['timestamp'].date() - d_from).days > -1:
#                        logger.log(logging.INFO, 'добавили {} тк {} > ({})'.format(work['id'], curr['timestamp'], d_from))
                        buf.append({state_or_grade(item)+'History': curr})
                        flag = True

                if d_to != 1:
                    if (d_to - curr['timestamp'].date()).days > -1:
                        if not flag:
                            buf.append({state_or_grade(item)+'History': curr})
#                            logger.log(logging.INFO, 'добавили {} тк {} < ({})'.format(work['id'], curr['timestamp'], d_to))
                            flag = True
                    else:
                        if flag:
#                            logger.log(logging.INFO, 'удалили {} тк {} > ({})'.format(work['id'], curr['timestamp'], d_to))
                            buf.pop(-1)

                if d_from != 0:
                    if flag == True:
                        if (curr['timestamp'].date() - d_from).days <= -1:
#                            logger.log(logging.INFO, 'удалили {} тк {} > ({})'.format(work['id'], curr['timestamp'], d_to))
                            buf.pop(-1)

            if buf != []:
                new_data.append(work.copy())
                new_data[-1]['submissionHistory'] = buf

    if new_data == []:
#        logger.log(logging.INFO, 'за указанный период нет работ')
#        logger.log(logging.INFO, '')
        return
    else:
        pass
#        logger.log(logging.INFO, 'за указанный период было найдено {} работ'.format(len(new_data)))
#    logger.log(logging.INFO, '')

    return new_data



def to_timestamp(timestamp):
    """
    Принимает: timestamp в формате 2014-10-02T15:01:23.045123456Z
    Возвращает: отметку времени в формате datetime.
    """

    #избавляется от лишней части отметки времени
    def helper(time):
        new_time = time
        if ('.') in time:
            new_time = time.split('.', 1)[0]
        else:
            new_time = time.split('Z', 1)[0]
        if new_time == time:
            logger.log(logging.ERROR, 'что-то пошло не так при парсинге отметки времени')
        return new_time

    timestamp = helper(timestamp)
    timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
    return timestamp


def change_submsissions_date_format(studentsSubmissions):
    """
    Принимает: список работ студента (studentsSubmissions).
    Возвращает: -

    *Парсит в каждой работе формат отметки времени в словарь.
    """
    for item in studentsSubmissions:
        if 'submissionHistory' in item.keys():
            for element in item['submissionHistory']:
                el_type = state_or_grade(element)
                element[el_type+'History']['timestamp'] = to_timestamp(element[el_type+'History'].pop(el_type+'Timestamp'))
