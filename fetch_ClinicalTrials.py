import requests
import json
import urllib3
import pandas as pd
from datetime import date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def make_call(expr, min_rnk, max_rnk = 1, fmt = 'json'):

    url = 'https://clinicaltrials.gov/api/query/full_studies'
    headers = {'Content-Type': 'application/json'}
    params = {'expr': expr, 'min_rnk': min_rnk, 'max_rnk' : max_rnk , 'fmt': fmt}
    try:
        response = requests.get(url, params = params, headers = headers, verify=False)
        #print(response.encoding)
        print('Status Code: ' + str(response.status_code))
        if response.status_code >= 500:
            print('[!] [{0}] Server Error'.format(response.status_code))
            return None
        elif response.status_code == 404:
            print('[!] [{0}] URL not found: [{1}]'.format(response.status_code,url))
            return None
        elif response.status_code == 401:
            print('[!] [{0}] Authentication Failed'.format(response.status_code))
            return None
        elif response.status_code == 400:
            print('[!] [{0}] Bad Request'.format(response.status_code))
            return None
        elif response.status_code >= 300:
            print('[!] [{0}] Unexpected Redirect'.format(response.status_code))
            return None
        elif response.status_code == 200:
            ssh_keys = json.loads(response.content.decode('utf-8'))
            return ssh_keys
        else:
            print('[?] Unexpected Error: [HTTP {0}]: Content: {1}'.format(response.status_code, response.content))
    except requests.exceptions.RequestException as e:
        print(e)

def exclude_phase(d, phase):
    return [val for val in d if val != phase]

def fetch_data(expr, pipID):
    min = 1
    data = make_call(expr, min, 100)
    clinicalData = data['FullStudiesResponse']['FullStudies']
    min += 100
    while (data['FullStudiesResponse']['NStudiesFound'] > min):
        max = min + 99
        if max < 500:
            data = make_call(expr, min, max)
            clinicalData.extend(data['FullStudiesResponse']['FullStudies'])
            min += 100
        else: break

    return {'pipelineId': pipID, 'studyResponse': clinicalData, 'aiMatchPercentage': ''}

if __name__ == '__main__':
    fetch_Data('covid')




