#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

dirpath = os.path.dirname(os.path.abspath(__file__))
scopes_path = dirpath + '/scopes.txt'
project_creds_path = dirpath + '/credentials.json'
user_creds_path = dirpath + '/token.pickle'

#читаем из файла области видимости (доступ к каким данным будем запрашивать у пользователя)
SCOPES = [line.rstrip('\n') for line in open(scopes_path)]

def get_token(creds=None):
    """
    Принимает: токен 
      *если вызывать модуль из командной строки - токен не передается, по умолчанию он None
    Возвращает: обновленный токен
    """
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
                               project_creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
    #токены сохраняются для последующего использования
    with open(user_creds_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_service():
    """
    Принимает: -
    Возвращает: сервис, с помощью которого можно отправлять запросы к апи
    """
    creds = None
    if os.path.exists(user_creds_path):
        with open(user_creds_path, 'rb') as token:
            creds = pickle.load(token)
    #если токенов нет, откроется страница авторизации Google
    if not creds or not creds.valid:
        creds = get_token(creds)
        
    service = build('classroom', 'v1', credentials=creds)
    return service

#при вызове модуля через командную строку выполнится только функция get_token(), чтобы загрузить/обновить токен
if __name__ == '__main__':
    get_token()
