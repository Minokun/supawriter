# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
import sys

import requests
from typing import List
import json

from alibabacloud_dingtalk.oauth2_1_0.client import Client as dingtalkoauth2_1_0Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalkoauth_2__1__0_models
from alibabacloud_tea_util.client import Client as UtilClient


class Sample:
    def __init__(self):
        pass

    @staticmethod
    def create_client() -> dingtalkoauth2_1_0Client:
        """
        使用 Token 初始化账号Client
        @return: Client
        @throws Exception
        """
        config = open_api_models.Config()
        config.protocol = 'https'
        config.region_id = 'central'
        return dingtalkoauth2_1_0Client(config)

    @staticmethod
    def main(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        get_access_token_request = dingtalkoauth_2__1__0_models.GetAccessTokenRequest(
            app_key='dingffguwdhgehersspn',
            app_secret='tFYBcBifIuvbLCvRaBVbMtp4Gtk_EBiabIUsWv_49hu2BGlsCD3Kba4ZnBp6B93-'
        )
        try:
            client.get_access_token(get_access_token_request)
            print(client.__dict__)
        except Exception as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                # err 中含有 code 和 message 属性，可帮助开发定位问题
                pass

    @staticmethod
    async def main_async(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        get_access_token_request = dingtalkoauth_2__1__0_models.GetAccessTokenRequest(
            app_key='dingffguwdhgehersspn',
            app_secret='tFYBcBifIuvbLCvRaBVbMtp4Gtk_EBiabIUsWv_49hu2BGlsCD3Kba4ZnBp6B93-'
        )
        try:
            await client.get_access_token_async(get_access_token_request)
        except Exception as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                # err 中含有 code 和 message 属性，可帮助开发定位问题
                pass


class DingDingTool:
    def __init__(self):
        self.access_token = self.get_access_token()
        self.department_ids = self.get_department_list()

    def get_access_token(self):

        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        headers = {
            "Host": "api.dingtalk.com",
            "Content-Type": "application/json"
        }
        data = {
            "appKey": "dingffguwdhgehersspn",
            "appSecret": "tFYBcBifIuvbLCvRaBVbMtp4Gtk_EBiabIUsWv_49hu2BGlsCD3Kba4ZnBp6B93-"
        }

        response = requests.post(url, headers=headers, json=data)
        result = json.loads(response.text)
        return result['accessToken']

    def get_department_list(self):
        url = f"https://oapi.dingtalk.com/topapi/v2/department/listsub?access_token={self.access_token}"
        # data = {
        #     "access_token": self.access_token,
        # }
        response = requests.post(url)
        result = json.loads(response.text)
        print(self.access_token, result)
        return result['result']

    def get_user_id_list(self):
        url = f"https://oapi.dingtalk.com/topapi/user/listid?access_token={self.access_token}"

        response = requests.post(url)

        print(response.text)

if __name__ == '__main__':
    # Sample.main(sys.argv[1:])
    dd_obj = DingDingTool()
