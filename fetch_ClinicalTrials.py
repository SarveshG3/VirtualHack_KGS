import requests
import json
import urllib3
import threading
import pandas as pd
import ast
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler
import pickle


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

loaded_model = None

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
    try:
        clinicalData = data['FullStudiesResponse']['FullStudies']
    except Exception as e:
        print('Error!' + str(e) +"\n Hint: Please check the submitted keyword for typos")
        raise e
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
    #print(df.columns)
    df = df[
        ['NCTId', 'OrgFullName', 'OrgClass', 'HasExpandedAccess', 'ResponsiblePartyType', 'LeadSponsorClass', 'OversightHasDMC',
         'IsFDARegulatedDrug', 'IPDSharing', 'Phase', 'DesignPrimaryPurpose']]
    return df

def prepare_data(df):
    df['Phase'] = df['Phase'].map(lambda x: list(ast.literal_eval(str(x).lower()))[-1])
    # df.to_excel('ClinicalData_Processed.xlsx', "Data", index=False)
    df = df.apply(lambda x: x.fillna('Unknown'))
    df.set_index('NCTId', inplace=True)
    le = LabelEncoder()
    df['OrgFullName'] = le.fit_transform(df['OrgFullName'])
    df['OrgClass'] = le.fit_transform(df['OrgClass'])
    df['HasExpandedAccess'] = le.fit_transform(df['HasExpandedAccess'])
    df['ResponsiblePartyType'] = le.fit_transform(df['ResponsiblePartyType'])
    df['DesignPrimaryPurpose'] = le.fit_transform(df['DesignPrimaryPurpose'])
    df['Phase'] = le.fit_transform(df['Phase'])
    df['LeadSponsorClass'] = le.fit_transform(df['LeadSponsorClass'])
    df['OversightHasDMC'] = le.fit_transform(df['OversightHasDMC'])
    df['IPDSharing'] = le.fit_transform(df['IPDSharing'])
    df['IsFDARegulatedDrug'] = le.fit_transform(df['IsFDARegulatedDrug'])
    scaler = MinMaxScaler(copy=False)
    scaled_df = scaler.fit_transform(df)
    df = pd.DataFrame(scaled_df, columns=df.columns, index=df.index)
    return df


def predict(row):
    row = row.values.reshape(1, -1)
    prediction = loaded_model.predict_proba(row)
    pred_value = prediction.item(0, 0) * 100
    old_min, old_max, new_min, new_max = [0, 100, 40, 100]
    scaled_pred = ((pred_value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
    return scaled_pred


def send_to_appian(score_data):
    url = 'https://kgs-india-hackathon-10-2020.appiancloud.com/suite/webapi/cciSendAnalysedData'
    headers = {'Content-Type': 'application/json',
               'appian-api-key': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlMGI3NDBkZC1lNjkyLTRlOTAtODczZi1iZWM5NThlMzBiODUifQ.PQaVLx48wncqGojHzQYbKPTqFbkzOGeevwfJEPZj0Is'}
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
    global loaded_model
    trials_df = fetch_data(expr)
    model_df = prepare_data(trials_df)
    with open('mysaved_md_pickle', 'rb') as file:
        loaded_model = pickle.load(file)
    model_df['aiMatchPercentage'] = [predict(row) for idx, row in model_df.iterrows()]
    model_df.reset_index(inplace=True)
    relevant_results = model_df[['NCTId', 'aiMatchPercentage']]
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




