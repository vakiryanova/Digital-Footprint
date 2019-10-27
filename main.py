import lib
import auth

#примеры работы функций

#аутентификация через аккаунт преподавателя

#загружаем список студентов со всех курсов, которые ведет преподаватель
students = lib.get_students()
#загружаем данные (курсы, задания, работы) одного студента
students[2]['courses'] = lib.get_data(students[2]['userId'])
#записываем их в файл
lib.make_file('student', students[2])

#все работы одного студента
stud_subm = lib.get_submission_history(students[2]['courses'][0]['studentSubmissions'])
#история изменения статуса и оценок каждого задания (history[0] и history[1])
history = lib.get_submission_history(stud_subm)

#ИЛИ

#аутентификация через аккаунт студента

#загружаем данные из профиля авторизированного студента
student = lib.get_my_profile()
#загружаем его данные о курсах
student['courses'] = lib.get_data('me')
#записываем их в файл
lib.make_file('student', student)
