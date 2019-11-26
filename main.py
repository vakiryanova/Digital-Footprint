import footprint as lib
from auth import auth

#примеры работы функций

#аутентификация через аккаунт преподавателя

#загружаем список студентов со всех курсов, которые ведет преподаватель
students = lib.get_students()
#загружаем данные (курсы, задания, работы) одного студента
students[2]['courses'] = lib.get_data(students[2]['userId'])

#все работы одного студента
stud_subm = lib.get_submission_history(students[2]['courses'][0]['studentSubmissions'])
#история изменения статуса и оценок каждого задания (history[0] и history[1])
history = lib.get_submission_history(stud_subm)
