from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#область видимости: доступ к каким данным пользователя запрашивает приложение
SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly', #список курсов
          'https://www.googleapis.com/auth/classroom.rosters.readonly', #список студентов и преподавателей
          'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly', #работы студентов
          'https://www.googleapis.com/auth/classroom.profile.emails', #электронная почта пользователей
          'https://www.googleapis.com/auth/classroom.profile.photos' #аватары пользователей
         ]

def auth():
    creds = None

    if os.path.exists('auth/token.pickle'):
        with open('auth/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    #если токенов нет, откроется страница авторизации Google
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'auth/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        #токены сохранены для последующего использования
        with open('auth/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('classroom', 'v1', credentials=creds)
    return service

auth()
