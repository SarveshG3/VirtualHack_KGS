import requests
import json
import urllib3
import random
import pandas as pd
import threading
from datetime import date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def make_call(expr, min_rnk, max_rnk = 1, fmt = 'json'):

    url = 'https://clinicaltrials.gov/api/query/full_studies'
    headers = {'Content-Type': 'application/json'}
    params = {'expr': expr, 'min_rnk': min_rnk, 'max_rnk' : max_rnk , 'fmt': fmt}
    try:
        response = requests.get(url, params = params, headers = headers, verify=False)
        #print(response.encoding)
        #print(response.status_code)
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
    return not(phase in d)

def fetch_data(expr):
    min = 1
    data = make_call(expr, min, 100)
    #clinicalData = pd.json_normalize(data['FullStudiesResponse']['FullStudies'])
    clinicalData = data['FullStudiesResponse']['FullStudies']
    min += 100
    while (data['FullStudiesResponse']['NStudiesFound'] > min):
        max = min + 99
        if max < 500:
            data = make_call(expr, min, max)
            clinicalData.extend(data['FullStudiesResponse']['FullStudies'])
            #clinicalData = clinicalData.append(pd.json_normalize(data['FullStudiesResponse']['FullStudies']))
            min += 100
        else: break

    #clinicalData = [{k: v for k, v in d.items() if k.lower() != 'rank'} for d in clinicalData]
    #df = pd.DataFrame(clinicalData)
    df = pd.json_normalize(clinicalData)
    df.rename(columns=lambda s: s.split('.')[-1].strip(), inplace=True)
    df = df[df['StudyType'].str.contains('Interventional')]
    df = df[df['Phase'].map(lambda x: exclude_phase(x, 'Phase 4'))]
    #df.to_excel('ClinicalData_Processed.xlsx', "Data", index=False)
    return df

def predict(row):
    return random.randint(70, 92)


def send_to_appian(score_data):
    url = 'https://kpmgusdemo.appiancloud.com/suite/webapi/cciSendAnalysedData'
    headers = {'Content-Type': 'application/json',
               'appian-api-key': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJiNGNhMWNkNy05N2E2LTRmZjAtODg2ZS1jNmJlM2Q5YTAwODgifQ.w8ect0wYDnGxgResr-8pApLpXr-yq-FzqTxCm-bmZPQ'}
    try:
        response = requests.post(url, headers=headers, data=score_data, verify=True)
        print("Appian POST response code: " + str(response.status_code))
        if response.status_code == 200:
            ssh_keys = json.loads(response.content.decode('utf-8'))
            return ssh_keys
        else:
            print('[?] Unexpected Error: [HTTP {0}]: Content: {1}'.format(response.status_code, response.content))
    except requests.exceptions.RequestException as e:
        print(e)


def prepare_send_result(expr, pipID):
    trials_df = fetch_data(expr)
    trials_df['aiMatchPercentage'] = [predict(row) for row in trials_df.iterrows()]
    relevant_results = trials_df[['NCTId', 'aiMatchPercentage']]
    returnString = relevant_results.to_json(orient='records')
    res = send_to_appian(json.dumps({'pipelineId': pipID, 'studyResponse': {'FullStudies': returnString}}))
    print(json.dumps(res))



def handle_request(req_data):
    #prepare_send_result(req_data['expr'], req_data['pipelineId'])
    threading.Thread(target=prepare_send_result, args=(req_data['expr'], req_data['pipelineId']), name="predict_result",
                    daemon=True).start()
    return "Data received successfully"


if __name__ == '__main__':
    fetch_data('covid')




