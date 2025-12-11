import pandas as pd
import requests
from datetime import datetime

class Avec:
    def __init__(self, authorization):
        self.authorization = authorization

    def __get_data(self, url):
        headers = {"Authorization": self.authorization}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro: status {response.status_code} - {response.text}")
            return None

    def __get_all_data(self, base_url, page):
        headers = {"Authorization": self.authorization}
        all_results = []

        while True:
            separator = '&' if '?' in base_url else '?'
            url = f"{base_url}{separator}page={page}"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                break

            data = response.json()
            report = data['data']['report']
            results = report.get('result', [])
            all_results.extend(results)

            if not report.get('hasMore'):
                break

            page += 1

        return all_results  # ← Faltava isso!

    def rel_0033_all(self, page=1):
        base_url = "https://api.avec.beauty/reports/0033?limit=250"
        return self.__get_all_data(base_url, page)



