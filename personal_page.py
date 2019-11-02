import auth
import numpy as np

service = auth.auth()

"""
Функция принимает словарь (или список словарей) и список ключей, которые нужно оставить.
Функция возвращает словарь (или список словарей) только с требуемыми ключами.

Примечание: если значение ключа nan, это значит, что либо оно не было задано изначально, 
либо такого ключа не существует
"""
def extract_keys(data, keys):
    
    def recursion(data, keys, step):
        if keys[step] == keys[-1]:
            if keys[step] in list(data.keys()):
                return data[keys[step]]
            else:
                return 'subkey ' + keys[step] + ' does not exist in key ' + keys[step-1]
        else:
            if keys[step] in list(data.keys()):
                res = recursion(data[keys[step]], keys, step+1)
                return res
            else:
                return 'subkey ' + keys[step] + ' does not exist in key ' + keys[step-1]
    
    def extract_from_item(item):
        newItem = {}
        for key in keys:
            if type(key) != list:
                if key in list(item.keys()):
                    newItem[key] = item[key]
                else:
                    newItem[key] = np.NaN
            else:
                newItem[key[-1]] = recursion(item, key, 0)
        return newItem
    
    if type(data) == list:
        newList = []
        for item in data:
            newList.append(extract_from_item(item))
        return newList
    else:
        return extract_from_item(data)
       
"""
Принимает список студентов и список заданий курса (в каждом задании имеется список работ студентов)
Ничего не возвращает, но добавляет в запись о каждом студенте информацию о прогрессе
"""
def get_progress(students, courseWork):
    
    def calc_progress(work, progress):
        i = 0
    #считаем прогресс каждого студента
        for item in progress:
        #максимальное количество баллов за текущее задание
            item['max'] += work['maxPoints']
        
        #оценка за задание
            curr = work['studentSubmissions'][i]['assignedGrade']
        
        #если оценка есть, добавляем ее
            if type(curr)==int:
                item['curr'] += curr
            #считаем количество потерянных баллов и записываем его
                item['lost'] += work['maxPoints'] - curr
        #если оценки нет
            else:
            #и работа просрочена, добавляем к потерянным баллам max балл за задание
                if work['studentSubmissions'][i]['late'] == True:
                    item['lost'] += work['maxPoints']
        #список студентов и список сабмишеннов не в одном порядке, поэтому нужно запомнить id студента        
            item['id'] = work['studentSubmissions'][i]['userId']
            i += 1
    
    def get_student_by_id(userId, students):
        return [element for element in students if element['userId'] == userId]

    progress = [{'max': 0, 'curr': 0, 'lost': 0} for i in range(len(students))]
    for work in courseWork:
        calc_progress(work, progress)
    
    for item in progress:
        student = get_student_by_id(item['id'], students)[0]
        student['progress'] = item
        
"""
Принимает json структуру курса.
Ничего не возвращает, но добавляет к информации о курсе список студентов, преподавателей, заданий и работ студентов.
"""
def get_course_info(course):
    
    #ключи, которые требуется оставить
    #если добавляются новые, нужно прописывать полный путь к ключу, например:
    #{userId:'id', 'profile':
                        #{'name':
                            #{'firstName':'first', 
                            #'lastName':'last'}}}
    #путь к ключу lastName - ['profile', 'name', 'lastName']
    courseKeys = ['id', 'name', 'description']
    teacherKeys = ['userId', ['profile', 'name', 'fullName'], ['profile', 'emailAddress']]
    studentKeys = ['userId', ['profile', 'name', 'fullName'], ['profile', 'emailAddress']]
    courseWorkKeys = ['courseId', 'id', 'title', 'maxPoints', 'dueDate', 'dueTime']
    studentSubmissionsKeys = ['courseId', 'courseWorkId', 'userId', 'state', 'assignedGrade', 'late']
    
    """
    Функция ничего не принимает и не возвращает.
    Она загружает список студентов курса с учетом nextPageToken.
    """
    def get_students():
        students = []
        flag = False
        token = ''
        while not flag:
            result = service.courses().students().list(courseId=course['id'], pageToken=token).execute()
            student = result.get('students', [])
            [students.append(i) for i in student]
            token = result.get('nextPageToken', [])
            if not token:
                flag = True
        return students
    
    """
    Функция принимает список заданий курса, высчитывает оставшееся время до дедлайнов и записывает их в поле timeLeft
    
    Если дедлайн еще не наступил, структура timeLeft выглядит следующим образом:
    {"year":int, "month":int, "day":int, "hour":int, "minute":int, "second":int}
    Если дедлайн прошел, то {'timeLeft':'late'}
    Если дедлайна у задания нет, то {'timeLeft':}
    """
    def calc_deadline(courseWork):
        from datetime import datetime
        now = datetime.now()
        for work in courseWork:
            if type(work['dueDate']) == dict:
                timeLeft = {'year':0, 'month':0, 'day':0, 'hour':0, 'minute':0, 'second':0}
                timeLeft['year'] = work['dueDate']['year'] - now.year
                timeLeft['month'] = work['dueDate']['month'] - now.month
                timeLeft['day'] = work['dueDate']['day'] - now.day
                timeLeft['hour'] = work['dueTime']['hours'] - now.hour
                timeLeft['minute'] = work['dueTime']['minutes'] - now.minute
                flag = False
                for i in list(timeLeft.keys()):
                    i = timeLeft[i]
                    if i<0:
                        flag = True
                        break
                if flag == True:
                    timeLeft = 'late'
            else: 
                timeLeft = np.nan
            work['timeLeft'] = timeLeft    
    
    course = extract_keys(course, courseKeys)
    
    students = get_students()
    course["students"] = extract_keys(students, studentKeys)

    teachers = service.courses().teachers().list(courseId=course["id"]).execute().get("teachers", [])
    course["teachers"] = extract_keys(teachers, teacherKeys)

    courseWork = service.courses().courseWork().list(courseId=course["id"]).execute().get("courseWork", [])
    course["courseWork"] = extract_keys(courseWork, courseWorkKeys)
    calc_deadline(course["courseWork"])
    
    for work in course["courseWork"]: 
        studentSubmissions = service.courses().courseWork().studentSubmissions().list(courseId=course["id"], 
                                                                              courseWorkId = work["id"]).execute()
        studentSubmissions = studentSubmissions.get("studentSubmissions", [])          
        work["studentSubmissions"] = extract_keys(studentSubmissions, studentSubmissionsKeys)    
    
    return course
    
    
courses = service.courses().list().execute().get("courses", [])
for course in courses:
    get_course_info(course)
    get_progress(course['students'], course['courseWork'])
