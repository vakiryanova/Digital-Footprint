import classroom as lib
from datetime import date
from pymongo import MongoClient
import configparser

def dump():
    
    #подключение к БД
    config = configparser.ConfigParser()
    config.read('auth/db.ini')
    username = config['DEFAULT']['User']
    password = config['DEFAULT']['Password']
    ip = config['DEFAULT']['IP']
    client = MongoClient('mongodb://%s:%s@%s' % (username, password, ip))
    col = client.app.classroom

    #загружаем курсы
    courses = lib.get_courses()
    
    #загружаем студентов
    students=[]
    for course in courses:
        s = None
        s = lib.get_students(course)
        if s!=[]:
            [students.append(i) for i in s]
            
    #удаляем повторяющихся студентов
    students = [dict(t) for t in {tuple(d.items()) for d in students}]
    
    #устанавливаем временной период, данные из которого хотим загрузить (подробнее в readme)
    date_from = 1
    date_to = 1
    
    #загружаем информацию для каждого студента и сохраняем ее в БД
    for student in students:
        student['dateFrom'] = date_from
        student['dateTo'] = date_to
        student['data'] = lib.get_data_by_student(student, date_from, date_to)
        col.insert_one(student)

if __name__ == '__main__':
    dump()
