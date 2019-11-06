import auth
import numpy as np
import pandas as pd

#аутентификация
service = auth.auth()



def get_students():
    """
    Эта функция загружает список курсов, доступных преподавателю или администратору,
    и достает списки студентов, подписанных на них.cПовторяющиеся студенты удаляются.
    
    Фунцкия возвращает список всех студентов со всех курсов (можно использовать для
    БД студентов, чтобы потом по id доставать нужную информацию)
    """
    courses = service.courses().list().execute().get('courses', [])
    students = []
    for course in courses:
    #загружаем список студентов каждого курса
        flag = False
        token = ''
        while not flag:
            result = service.courses().students().list(courseId=course['id'], pageToken=token).execute()
            student = result.get('students', [])
            [students.append(i) for i in student]
            token = result.get('nextPageToken', [])
            if not token:
                flag = True
    
    #удаляем повторяющихся студентов
    result = []
    for i in range(len(students)): 
        if students[i] not in students[i + 1:]: 
            result.append(students[i])
            
    return result


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
                    res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
                    submissions.append(res.get('studentSubmissions',[])[0])
                #сохраняем задание
                    coursework.append(task)
        #если задание для всех студентов
            else:
            #загружаем и сохраняем информацию о работе
                res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
                submissions.append(res.get('studentSubmissions',[])[0])
                coursework.append(task)
        else:
            res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=task['id'],
                                                                          userId=studentId).execute()
            submissions.append(res.get('studentSubmissions',[])[0])
            coursework.append(task)
    return coursework, submissions
    

def get_data(studentId):
    """
    Эта функция принимает id студента.
    Возвращает список его курсов, заданий, работ.
    Вместо id можно передать строку "me", если авторизация была произведена через аккаунт студента, тогда функция вернет
    информацию о его курсах.
    """
    
    missingKeys = [['late', False], ['assignedGrade', np.NaN]]
    
    #загружаем список курсов, который доступны авторизированному пользователю
    courses = service.courses().list(studentId=studentId).execute().get('courses', [])
    
    for course in courses:
        studentSumbissions = []
        #загружаем список заданий для каждого курса
        result = service.courses().courseWork().list(courseId=course['id']).execute().get('courseWork', [])
        
        #загружаем список работ по заданиям и добавляем недостающие поля 
        [courseWork, studentSumbissions] = get_submissions(course['id'], result, studentId)
        for work in studentSumbissions:
            work = checkMissingKeys(work, missingKeys)

        #добавляем список заданий и работ в информацию о курсе 
        course['courseWork'] = courseWork
        course['studentSubmissions'] = studentSumbissions
        
    return courses


def get_my_profile():
    """
    Возвращает информацию из профиля авторизированного студента
    """
    student_missing_keys = [['photoUrl', np.NaN], ['verifiedTeacher', False]]
    student = service.userProfiles().get(userId='me').execute()
    student = checkMissingKeys(student, student_missing_keys)
    return student


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
