import pandas as pd
import time
import json
import lib
import auth

# If modifying these scopes, delete the file token.pickle.
students = lib.get_students()
students[101]['courses'] = lib.get_data(students[101]['userId'])
print(students[101])
