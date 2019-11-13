import auth
import logs
import numpy as np
import datetime as dt
import logging
from googleapiclient.errors import HttpError

#аутентификация
service = auth.auth()

#инициализация логгинга
logger = logs.logger_init()

def get_courses():
    """
    Принимает: -
    Вовзращает: список курсов, к которым есть доступ с используемым токеном 
                пользователя.
    """
    courses = service.courses().list().execute().get('courses', [])

    if courses == []:
        logger.log(logging.WARNING, 'нет курсов')
    else:
        logger.log(logging.INFO, 'загружено {} курсов'.format(len(courses)))
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


    
def get_students(course):
    """
    Принимает: один курс (или только поля курса id и name).
    Вовзращает: список студентов курса.
    """
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
            
    if students == []:
        logger.log(logging.WARNING, 'на курсе {} ({}) нет студентов'.format(course['name'], course['id']))
    else:
        logger.log(logging.INFO, 'загружено {} студентов с курса {} ({})'.format(len(students), course['name'], course['id']))
    
    #удаляем ненужные ключи
    for student in students:
        for i in ['permissions', 'verifiedTeacher']:
            if i in student.keys():
                student.pop(i)
    return students



def get_courseWork(course):
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
        logger.log(logging.WARNING, 'на курсе {} ({}) нет заданий'.format(course['name'], course['id']))
    else:
        logger.log(logging.INFO, 'загружено {} заданий с курса {} ({})'.format(len(courseWork), course['name'], course['id']))
        
    return courseWork



def get_studentSubmissions_by_student(courseWork, studentId):
    """
    Принимает: список заданий курса (courseWork) и id студента.
    Возвращает: список заданий, которые доступны этому студенту и его работы по ним.
    
    *Некоторые задания курса индивидуальны, а значит могут быть не доступны 
     студенту, информацию которого мы запрашиваем.
    """
    
    def download_submissions(courseWorkId, coursework, submissions):
        try:
            res = service.courses().courseWork().studentSubmissions().list(courseId=courseId, 
                                                                          courseWorkId=courseWorkId,
                                                                          userId=studentId).execute()
            submissions.append(res.get('studentSubmissions',[])[0])
            coursework.append(task)
        except HttpError as err:
            print(err)
            logger.log(logging.ERROR, err)
    
    courseId = courseWork[0]['courseId']
    submissions = []
    coursework = []
    
    for task in courseWork:
        #если задание не для всех студентов, а для некоторых
        if task['assigneeMode']=='INDIVIDUAL_STUDENTS': 
            #и текущий студент имеет доступ к этому заданию
            if studentId in task['individualStudentsOptions']['studentIds']: 
                #загружаем и сохраняем информацию о работе
                download_submissions(task['id'], coursework, submissions)
        else: #если задание для всех студентов
            download_submissions(task['id'], coursework, submissions)
           
    change_submsissions_date_format(submissions)
    
    for item in submissions:
        if 'updateTime' in item.keys():
            item['updateTime'] = timestamp_to_dict(item['updateTime'])
            
    return coursework, submissions
    


def get_studentSubmissions_by_courseWork(courseId, courseWorkId):
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
        logger.log(logging.WARNING, 'на курсе {} нет студентов'.format(courseId))
    else:
        logger.log(logging.INFO, 'для задания {} загружено {} работ'.format(courseWorkId, len(studentSubmissions)))
        
    change_submsissions_date_format(studentSubmissions)
    
    for item in studentSubmissions:
        if 'updateTime' in item.keys():
            item['updateTime'] = timestamp_to_dict(item['updateTime'])

    return studentSubmissions



def get_data_by_student(studentId):
    """
    Принимает: id студента.
    Возвращает: список курсов, заданий, работ этого студента.
    """
    courseWorkMissingKeys = {'assigneeMode':'ALL_STUDENTS'}
    submissionsMissingKeys = {'late': False, 'assignedGrade': np.NaN}
    
    #загружаем список курсов, которые доступны конкретному студенту
    courses = service.courses().list(studentId=studentId).execute().get('courses', [])
    
    if courses == []:
        logger.log(logging.WARNING, 'студент {} не подписан ни на один курс'.format(studentId))
        return
    else:
        logger.log(logging.INFO, 'студент {} подписан на {} курсов'.format(studentId, len(courses)))
    
    for course in courses:
        studentSumbissions = []
        
        #загружаем список заданий для каждого курса
        result = service.courses().courseWork().list(courseId=course['id']).execute().get('courseWork', [])
        result = checkMissingKeys(result, courseWorkMissingKeys)
        
        if result == []:
            logger.log(logging.INFO, 'у курса {} нет заданий'.format(course['name']))
        else:
            logger.log(logging.INFO, 'у курса {} {} заданий'.format(course['name'], len(result)))
            
        #загружаем список работ по заданиям и добавляем недостающие поля 
        [courseWork, studentSumbissions] = get_studentSubmissions_by_student(result, studentId)
        
        for work in studentSumbissions:
            work = checkMissingKeys(work, submissionsMissingKeys)

        #добавляем список заданий и работ в информацию о курсе 
        course['courseWork'] = courseWork
        course['studentSubmissions'] = studentSumbissions
    return courses



def checkMissingKeys(data, missingValues):
    """
    Принимает: исходную информацию (list of dict или dict); список полей, которые
               должны присутвсовать в структуре, и их значений по умолчанию (dict).
    Возвращает: исходные данные, но с новыми полями.
    
    *Некоторые поля могут остуствовать в загружаемой информации, поэтому при 
    попытке обратиться к ним возникнет ошибка.
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
    
    
    
def select_data_by_date(studentsSubmissions, d_from=0, d_to=0):
    """
    Принимает: список работ студента (studentsSubmissions) и временной период 
               (даты в формате datetime.date).
    Возвращает: список работ, который были изменены в этот период.
    
    1) Можно задать не обе даты, а только одну.
    2) В возвращаемом списке работ, в графах submissionHistory содержится не 
       вся история изменений, а лишь те события, которые произошли в указанный 
       период.
    """
    
    if d_from==0 and d_to==0:
        logger.log(logging.INFO, 'период не указан')
        return
    
    if type(d_from)!=dt.date and d_from!=0:
        logger.log(logging.WARNING, 'дата должна быть в формате datetime.date')
        return
    
    if type(d_to)!=dt.date and d_to!=0:
        logger.log(logging.WARNING, 'дата должна быть в формате datetime.date')
        return
    
    if d_from!=0 and d_to!=0 and d_from > d_to:
        logger.log(logging.WARNING, 'дата "от" должна быть меньше даты "до"')
        return
    
    #проверка на вхождения работ в заданный диапазон дат    
    new_data = []
    for work in studentSubmissions:
        buf = []
        if work['state']!='NEW':
            for item in work['submissionHistory']:
                el_type = state_or_grade(item)
                curr = item[el_type+'History']
                curr['date'] = dt.date(
                        curr['timestamp']['year'], 
                        curr['timestamp']['month'], 
                        curr['timestamp']['day'])
                
                flag = False
                if d_from != 0:
                    if (curr['date'] - d_from).days > -1:
                        logger.log(logging.INFO, 'добавили {} тк {} > {}'.format(work['id'], curr['date'], d_from))
                        buf.append({state_or_grade(item)+'History': curr})
                        flag = True
                    
                if d_to != 0:
                    if (d_to - curr['date']).days > -1:
                        if not flag:
                            buf.append({state_or_grade(item)+'History': curr})
                            logger.log(logging.INFO, 'добавили {} тк {} < {}'.format(work['id'], curr['date'], d_to))
                            flag = True
                    else:
                        if flag:
                            logger.log(logging.INFO, 'удалили {} тк {} > {}'.format(work['id'], curr['date'], d_to))
                            buf.pop(-1)
                        
                if d_from != 0:
                    if flag == True:
                        if (curr['date'] - d_from).days <= -1:
                            logger.log(logging.INFO, 'удалили {} тк {} > {}'.format(work['id'], curr['date'], d_to))
                            buf.pop(-1)
            
            if buf != []:            
                for i in buf:
                    i[state_or_grade(i)+'History'].pop('date')
                new_data.append(work.copy())
                new_data[-1]['submissionHistory'] = buf
                
    if new_data == []:
        logger.log(logging.INFO, 'за указанный период нет работ')
        logger.log(logging.INFO, '')
        return
    else:
        logger.log(logging.INFO, 'за указанный период было найдено {} работ'.format(len(new_data)))
    logger.log(logging.INFO, '')
                    
    return new_data



def timestamp_to_dict(timestamp):
    """
    Принимает: timestamp в формате 2014-10-02T15:01:23.045123456Z
    Возвращает: словарь.
    """
        
    #избавляется от лишней части отметки времени
    def helper(time):
        new_time = time
        if ('.') in time:
            new_time = time.split('.', 1)[0]
        else:
            new_time = time.split('Z', 1)[0]
        if new_time == time:
            logger.log(logging.WARNING, 'что-то пошло не так при парсинге отметки времени')
        return new_time
        
    timestamp = helper(timestamp)
    timestamp = dt.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
    new_timestamp = {}
    new_timestamp['year'] = timestamp.year
    new_timestamp['month'] = timestamp.month
    new_timestamp['day'] = timestamp.day
    new_timestamp['hours'] = timestamp.hour
    new_timestamp['minutes'] = timestamp.minute
    new_timestamp['seconds'] = timestamp.second
    return new_timestamp



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
                element[el_type+'History']['timestamp'] = timestamp_to_dict(element[el_type+'History'].pop(el_type+'Timestamp'))
