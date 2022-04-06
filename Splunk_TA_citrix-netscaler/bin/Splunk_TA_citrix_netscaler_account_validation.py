#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-1-2020
#
#
import splunk.admin as admin
from solnlib import conf_manager
from ta_util2 import rest
from ta_util2 import utils
import httplib2
try:
    from httplib2 import SSLHandshakeError
except:
    from ssl import SSLError as SSLHandshakeError
import json
import traceback
import copy
from splunktaucclib.rest_handler.endpoint.validator import Validator
from citrix_netscaler import proxy_port_value_validation

APP_NAME = "Splunk_TA_citrix-netscaler"
_LOGGER = utils.setup_logging("ta_citrix_netscaler_appliance_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class AccountValidation(Validator):

    ## Validate Citrix Netscaler appliance's credentials

    def __init__(self, *args, **kwargs):
        super(AccountValidation, self).__init__(*args, **kwargs)

    def get_ssl_proxy_settings(self, defaults):

        ## Get SSL and Proxy configurations from splunk_ta_citrix_netscaler_settings.conf
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key
        settings_cfm = conf_manager.ConfManager(session_key, APP_NAME,
                                                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_citrix_netscaler_settings".format(
                                                    APP_NAME))
        splunk_ta_citrix_netscaler_settings = settings_cfm.get_conf("splunk_ta_citrix_netscaler_settings").get_all()

        for key, value in splunk_ta_citrix_netscaler_settings["additional_parameters"].items():
            defaults[key] = value

        for key, value in splunk_ta_citrix_netscaler_settings["proxy"].items():
            defaults[key] = value

        return defaults

    def validate(self, value, data):
        _LOGGER.info("Validating Citrix Netscaler appliance's credentials")

        
        ## Get SSL and Proxy configurations from splunk_ta_citrix_netscaler_settings.conf
        defaults = self.get_ssl_proxy_settings(copy.deepcopy(data))

        ## Validate if proxy port is valid
        if utils.is_true(defaults.get("proxy_enabled") or "0") and "proxy_port" in defaults and not proxy_port_value_validation(defaults["proxy_port"]):
            self.put_msg("Invalid Proxy Port value in Configuration file, Proxy Port should be within the range of [1 and 65535]", True)
            return False

        ## Validate if http_scheme is valid, i.e. http or https
        http_scheme = defaults['http_scheme']
        _LOGGER.debug("Validating http_scheme parameter value from splunk_ta_citrix_netscaler_settings.conf")
        if http_scheme.lower() not in ('http', 'https'):
            msg = (
            "In splunk_ta_citrix_netscaler_settings.conf, the http_scheme value, {}, is invalid. The only valid values are http and https. To add an appliance, update this value and retry.".format(
                http_scheme))
            _LOGGER.error(
                "Incorrect http_scheme value, %s, in the splunk_ta_citrix_netscaler_settings.conf file of the Splunk Add-on for Citrix Netscaler. To connect successfully to host %s, enter a valid http_scheme value (http or https)",
                http_scheme, defaults["server_url"])
            self.put_msg(msg, True)
            return False
        _LOGGER.debug("http_scheme parameter value %s, successfully validated", http_scheme)

        ## Append http_scheme to host and form the url
        application_url = defaults['http_scheme'] + "://" + defaults['server_url'] + "/nitro/v1/config/login"

        payload = json.dumps(
            {"login": {"username": defaults['account_name'], "password": defaults['account_password']}})
        headers = {"Content-Type": "application/json", }

        try:
            _http = rest.build_http_connection(defaults)
            resp, content = _http.request(application_url, method="POST", headers=headers, body=payload)
        except SSLHandshakeError:
            msg = (
                "Failed to verify your SSL certificate. Verify your SSL configurations in splunk_ta_citrix_netscaler_settings.conf and retry.")
            self.put_msg(msg, True)
            _LOGGER.error(
                "Failed to verify the SSL Certificate for Citrix Netscaler host %s. Verify your SSL configurations in splunk_ta_citrix_netscaler_settings.conf.\nreason=%s",
                defaults['server_url'], traceback.format_exc())
            return False
        except httplib2.ServerNotFoundError:
            msg = (
                "Unable to find Citrix Netscaler server {}. Check your Host details or network connection, and retry.".format(
                    defaults["server_url"]))
            _LOGGER.error(
                "Unable to reach Citrix Netscaler server %s. Verify the host and retry.\nreason=%s",
                defaults["server_url"], traceback.format_exc())
            self.put_msg(msg, True)
            return False
        except Exception:
            msg = (
                "Some error occured while validating credentials for Citrix Netscaler host {}. Check ta_citrix_netscaler_appliance_validation.log for more details.".format(
                    defaults["server_url"]))
            _LOGGER.error(
                "While validating credentials for Citrix Netscaler host %s, some error occured. Check the Host value you entered in the Splunk Add-on for Citrix Netscaler or your network connection, and try again.\nreason=%s",
                defaults["server_url"], traceback.format_exc())
            self.put_msg(msg, True)
            return False
        else:
            if int(resp['status']) not in (200, 201):
                dict_content = json.loads(content)
                response_message = dict_content['message']
                msg = ("{}".format(response_message))
                _LOGGER.error("%s", format(response_message))
                self.put_msg(msg, True)
                return False
            else:
                _LOGGER.info("Successfully validated Citrix Netscaler appliance %s's credentials.",
                            defaults["server_url"])
                return True

class ProxyValidation(Validator):
    """
        Validate Proxy details provided
    """

    def __init__(self, *args, **kwargs):
        super(ProxyValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        _LOGGER.info("Validating proxy details")

        username_val = data.get("proxy_username")
        password_val = data.get("proxy_password")

        # If password is specified, then username is required
        if password_val and not username_val:
            self.put_msg(
                'Username is required if password is specified', high_priority=True
            )
            return False
        # If username is specified, then password is required
        elif username_val and not password_val:
            self.put_msg(
                'Password is required if username is specified', high_priority=True
            )
            return False

        # If length of username is not satisfying the String length criteria
        if username_val:
            str_len = len(username_val)
            _min_len = 1
            _max_len = 50
            if str_len < _min_len or str_len > _max_len:
                msg = 'String length of username should be between %(min_len)s and %(max_len)s' % {
                    'min_len': _min_len,
                    'max_len': _max_len
                }
                self.put_msg(msg, high_priority=True)
                return False

        return True
