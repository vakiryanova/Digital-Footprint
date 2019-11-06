import auth
import numpy as np
import pandas as pd
import logging
from datetime import datetime
from googleapiclient.errors import HttpError

#аутентификация
service = auth.auth()
logging.basicConfig(filename='example.log',level=logging.INFO)

def log_event(level, message, timestamp, function, file):
    def get_numeric_level(level):
        if level=='debug':
            return 10
        elif level=='info':
            return 20
        elif level=='warning':
            return 30
        elif level=='error':
            return 40
        elif level=='critical':
            return 50
        else:
            return 0   
    log = {}
    log['level'] = level
    log['message'] = message
    log['timestamp'] = timestamp
    log['function'] = function
    log['file'] = file
    logging.log(get_numeric_level(level), log)

    
def get_students():
    """
    Эта функция загружает список курсов, доступных преподавателю,
    и достает списки студентов, подписанных на них.
    Повторяющиеся студенты удаляются.
    Фунцкия возвращает список всех студентов со всех курсов (можно использовать для
    БД студентов, чтобы потом по id доставать нужную информацию)
    """
    
    courses = service.courses().list().execute().get('courses', [])
    if courses == []:
        log_event('warning','нет доступных курсов', str(datetime.now()), 'get_students()', 'lib.py')
        return
    else:
        log_event('info','загружено ' + str(len(courses)) + " курсов", str(datetime.now()), 'get_students()', 'lib.py')
    
    students = []
    for course in courses:
        #загружаем список студентов каждого курса
        flag = False
        token = ''
        course_students = []
        while not flag:
            result = service.courses().students().list(courseId=course['id'], pageToken=token).execute()
            student = result.get('students', [])
            [course_students.append(i['profile']) for i in student]
            token = result.get('nextPageToken', [])
            if not token:
                flag = True
        students.append({'courseId':course['id'], 'students':course_students})
                
    if students == []:
        log_event('warning','студентов нет', str(datetime.now()), 'get_students()', 'lib.py')
    else:
        log_event('info','студенты загружены', str(datetime.now()), 'get_students()', 'lib.py')
    return students


def get_submissions(courseId, courseWork, studentId):
    """
    Некоторые задания курса индивидуальны, а значит могут быть не доступны студенту, информацию которого мы запрашиваем.
    Эта функция принимает id курса, список ВСЕХ заданий курса и id студента.
    Возвращает: список заданий, которые этому студенту доступны и его работы по ним.
    """
    
    submissions = []
    coursework = []
    i=0
    for task in courseWork:
        #если задание не для всех студентов
        if 'assigneeMode' in list(task.keys()):
            if task['assigneeMode']=='INDIVIDUAL_STUDENTS':
                # и текущий студент имеет доступ к этому заданию
                if studentId in task['individualStudentsOptions']['studentIds']:
                    #загружаем и сохраняем информацию о работе
                    try:
                        res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
                        submissions.append(res.get('studentSubmissions',[])[0])
                        coursework.append(task)
                    except HttpError as err:
                        print(err)
                        logging.log(0, err)
            else:
                try:
                    res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
                    submissions.append(res.get('studentSubmissions',[])[0])
                    coursework.append(task)
                except HttpError as err:
                    print(err)
                    logging.log(0, err)
        else:
            try:
                res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
                submissions.append(res.get('studentSubmissions',[])[0])
                coursework.append(task)
            except HttpError as err:
                print(err)
                logging.log(0, err)
            
    return coursework, submissions
    

def get_data(studentId):
    """
    Эта функция принимает id студента.
    Возвращает список его курсов, заданий, работ.
    
    (структура courses в файле на диске)
    """
    
    missingKeys = [['late', False], ['assignedGrade', np.NaN]]
    #загружаем список курсов, который доступны авторизированному пользователю
    courses = service.courses().list(studentId=studentId).execute().get('courses', [])
    
    if courses == []:
        log_event('error','нет доступных курсов', str(datetime.now()), 'get_data()', 'lib.py')
        return
    else:
        log_event('error','загружено ' + str(len(courses)) + ' курсов', str(datetime.now()), 'get_data()', 'lib.py')
    
    for course in courses:
        studentSumbissions = []
        
        #загружаем список заданий для каждого курса
        result = service.courses().courseWork().list(courseId=course['id']).execute().get('courseWork', [])
        
        if result == []:
            log_event('warning','у курса ' + str(course['id']) + ' нет заданий', str(datetime.now()), 'get_data()', 'lib.py')
        else:
            log_event('warning','у курса ' + str(course['id'])+' '+str(len(res)) + ' заданий', str(datetime.now()), 'get_data()', 'lib.py')
        #загружаем список работ по заданиям и добавляем недостающие поля 
        [courseWork, studentSumbissions] = get_submissions(course['id'], result, studentId)
        
        for work in studentSumbissions:
            work = checkMissingKeys(work, missingKeys)

        #добавляем список заданий и работ в информацию о курсе 
        course['courseWork'] = courseWork
        course['studentSubmissions'] = studentSumbissions
        
    return courses


def checkMissingKeys(data, missingValues):
    """
    Некоторые поля могут остуствовать в загружаемой информации, поэтому при попытке
    обратиться к ним возникнет ошибка.
    Эта функция принимает исходную информацию (в формате dict), а также список полей, которые
    должны присутвсовать в структуре, и их значений по умолчанию.
    Возвращает: исходные данные, но с новыми полями.
    """
    for key in missingValues:
        if key[0] not in list(data.keys()):
            data[key[0]] = key[1]
            
    return data


def get_submission_history(data):
    """
    Эта функция принимает список studentSubmissions и возвращает списки изменений
    состояния и оценок для каждого задания.
    """
    gradeHistory = []
    stateHistory = []
    for segment in data:
        if 'submissionHistory' not in segment:
            stateHistory.append([])
            gradeHistory.append([])
        else:
            subm = segment['submissionHistory']
            state = []
            grade = []
            if len(subm)>1:
                for j in subm:
                    if 'stateHistory' in j:
                        state.append(j['stateHistory'])
                    else:
                        grade.append(j['gradeHistory'])
                stateHistory.append(state)
                gradeHistory.append(grade)
            else:
                if 'stateHistory' in subm[0]:
                    stateHistory.append(subm[0]['stateHistory'])
                else:
                    gradeHistory.append(subm[0]['gradeHistory'])
    a = [stateHistory, gradeHistory]
    return a


def make_file(title, data):
    """
    Эта функция принимает название файла и информацию (dict). Функция создает и
    записывает в него эту информацию.
    """
    import os
    import json
    try:
        os.mkdir('data/')
    except OSError:
        pass
    with open('data/' + title + '.json', 'w+') as fp:
        json.dump(data, fp)
        print (title + '.json created')
