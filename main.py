import sys
import requests
import re
import time
import random
from google import google

#https://developers.google.com/analytics/devguides/collection/protocol/v1/

def main():
    test = analytics_request(document_referrer="http://hacker.com", document_location="https://zonksec.com",tracking_id='UA-72589501-1',client_id=999)
    test.send()

class session:
    def __init__(self, target_urls, bounce_urls, page_delay=3000, page_delay_jitter=10, bounces=0):
        self.target_urls = target_urls
        self.page_delay = page_delay
        self.page_delay_jitter = page_delay_jitter
        self.bounces = bounces
        self.bounce_urls = bounce_urls

        if bounces != 0 and bounces < 10 and bounce_urls is None:
            search_results = google.search("site:"+target_urls, 10)
            for result in search_results:
                bounce_urls.append(result.link)

        else:
            search_results = google.search("site:"+target_urls, bounces)
            for result in search_results:
                bounce_urls.append(result.link)

class analytics_request:
    def __init__(self,document_referrer,document_location,tracking_id,client_id,version=1,hit_type='pageview',user_agent ='Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',geo_id ='US', anon_ip =1):
        self.version = version
        self.tracking_id = tracking_id
        self.client_id = client_id
        self.hit_type = hit_type
        self.user_agent = user_agent
        self.geo_id = geo_id
        self.document_referrer = document_referrer
        self.document_location = document_location
        self.anon_ip = anon_ip

    def send(self):
        params = {}
        params['v'] = self.version
        params['tid'] = self.tracking_id
        params['cid'] = self.client_id
        params['t'] = self.hit_type
        params['aip'] = self.anon_ip
        params['d'] = self.document_location
        params['dr'] =self.document_referrer

        r = requests.get('https://www.google-analytics.com/collect', params=params)
        print(r)


main()