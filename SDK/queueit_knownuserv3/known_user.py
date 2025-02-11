from .user_in_queue_service import UserInQueueService
from .user_in_queue_state_cookie_repository import UserInQueueStateCookieRepository
from .queueit_helpers import QueueitHelpers
from .models import Utils, KnownUserError, ActionTypes, RequestValidationResult, QueueEventConfig, CancelEventConfig
from .integration_config_helpers import IntegrationEvaluator
from .queue_url_params import QueueUrlParams
from .connector_diagnostics import ConnectorDiagnostics
import json
import sys

class KnownUser:
    QUEUEIT_TOKEN_KEY = "queueittoken"
    QUEUEIT_DEBUG_KEY = "queueitdebug"
    QUEUEIT_AJAX_HEADER_KEY = "x-queueit-ajaxpageurl"

    userInQueueService = None

    @staticmethod
    def __getUserInQueueService(httpContextProvider):
        if KnownUser.userInQueueService is None:
            return UserInQueueService(
                httpContextProvider,
                UserInQueueStateCookieRepository(httpContextProvider))
        return KnownUser.userInQueueService

    @staticmethod
    def __isQueueAjaxCall(httpContextProvider):
        return httpContextProvider.getHeader(
            KnownUser.QUEUEIT_AJAX_HEADER_KEY) is not None

    @staticmethod
    def __generateTargetUrl(originalTargetUrl, httpContextProvider):
        if (KnownUser.__isQueueAjaxCall(httpContextProvider)):
            return QueueitHelpers.urlDecode(
                httpContextProvider.getHeader(
                    KnownUser.QUEUEIT_AJAX_HEADER_KEY))
        return originalTargetUrl

    @staticmethod
    def __logMoreRequestDetails(debugEntries, httpContextProvider):
        debugEntries[
            "ServerUtcTime"] = QueueitHelpers.getCurrentTimeAsIso8601Str(
            )
        debugEntries["RequestIP"] = httpContextProvider.getRequestIp()
        debugEntries["RequestHttpHeader_Via"] = httpContextProvider.getHeader(
            "via")
        debugEntries[
            "RequestHttpHeader_Forwarded"] = httpContextProvider.getHeader(
                "forwarded")
        debugEntries[
            "RequestHttpHeader_XForwardedFor"] = httpContextProvider.getHeader(
                "x-forwarded-for")
        debugEntries[
            "RequestHttpHeader_XForwardedHost"] = httpContextProvider.getHeader(
                "x-forwarded-host")
        debugEntries[
            "RequestHttpHeader_XForwardedProto"] = httpContextProvider.getHeader(
                "x-forwarded-proto")

    @staticmethod
    def __setDebugCookie(debugEntries, httpContextProvider):
        if (debugEntries == None or len(debugEntries) == 0):
            return

        cookieValue = ''
        for k, v in debugEntries.iteritems():
            cookieValue += (k + '=' + str(v) + '|')

        cookieValue = cookieValue.strip('|')
        httpContextProvider.setCookie(KnownUser.QUEUEIT_DEBUG_KEY, cookieValue,
                                      None, None)
    @staticmethod
    def __getRunTime():
        return sys.version

    @staticmethod
    def __resolveQueueRequestByLocalConfig(targetUrl, queueitToken,
                                           queueConfig, customerId, secretKey,
                                           httpContextProvider, debugEntries, isDebug):
        if (isDebug):
            debugEntries["SdkVersion"] = UserInQueueService.SDK_VERSION
            debugEntries["Connector"] = httpContextProvider.getProviderName()
            debugEntries["Runtime"] = KnownUser.__getRunTime()
            debugEntries["TargetUrl"] = targetUrl
            debugEntries["QueueitToken"] = queueitToken
            debugEntries[
                "OriginalUrl"] = httpContextProvider.getOriginalRequestUrl()
            if (queueConfig == None):
                debugEntries["QueueConfig"] = "NULL"
            else:
                debugEntries["QueueConfig"] = queueConfig.toString()
            KnownUser.__logMoreRequestDetails(debugEntries,
                                              httpContextProvider)

        if (Utils.isNilOrEmpty(customerId)):
            raise KnownUserError("customerId can not be none or empty.")

        if (Utils.isNilOrEmpty(secretKey)):
            raise KnownUserError("secretKey can not be none or empty.")

        if (queueConfig == None):
            raise KnownUserError("queueConfig can not be none.")

        if (Utils.isNilOrEmpty(queueConfig.eventId)):
            raise KnownUserError(
                "queueConfig.eventId can not be none or empty.")

        if (Utils.isNilOrEmpty(queueConfig.queueDomain)):
            raise KnownUserError(
                "queueConfig.queueDomain can not be none or empty.")

        minutes = QueueitHelpers.convertToInt(queueConfig.cookieValidityMinute)
        if (minutes <= 0):
            raise KnownUserError(
                "queueConfig.cookieValidityMinute should be integer greater than 0."
            )

        if (queueConfig.extendCookieValidity != True
                and queueConfig.extendCookieValidity != False):
            raise KnownUserError(
                "queueConfig.extendCookieValidity should be valid boolean.")

        userInQueueService = KnownUser.__getUserInQueueService(
            httpContextProvider)
        result = userInQueueService.validateQueueRequest(
            targetUrl, queueitToken, queueConfig, customerId, secretKey)
        result.isAjaxResult = KnownUser.__isQueueAjaxCall(httpContextProvider)
        return result

    @staticmethod
    def __cancelRequestByLocalConfig(targetUrl, queueitToken, cancelConfig,
                                     customerId, secretKey,
                                     httpContextProvider, debugEntries, isDebug):
        targetUrl = KnownUser.__generateTargetUrl(targetUrl, httpContextProvider)

        if (isDebug):
            debugEntries["SdkVersion"] = UserInQueueService.SDK_VERSION
            debugEntries["Connector"] = httpContextProvider.getProviderName()
            debugEntries["Runtime"] = KnownUser.__getRunTime()
            debugEntries["TargetUrl"] = targetUrl
            debugEntries["QueueitToken"] = queueitToken
            debugEntries[
                "OriginalUrl"] = httpContextProvider.getOriginalRequestUrl()
            if (cancelConfig == None):
                debugEntries["CancelConfig"] = "NULL"
            else:
                debugEntries["CancelConfig"] = cancelConfig.toString()
            KnownUser.__logMoreRequestDetails(debugEntries,
                                              httpContextProvider)

        if (Utils.isNilOrEmpty(targetUrl)):
            raise KnownUserError("targetUrl can not be none or empty.")

        if (Utils.isNilOrEmpty(customerId)):
            raise KnownUserError("customerId can not be none or empty.")

        if (Utils.isNilOrEmpty(secretKey)):
            raise KnownUserError("secretKey can not be none or empty.")

        if (cancelConfig == None):
            raise KnownUserError("cancelConfig can not be none.")

        if (Utils.isNilOrEmpty(cancelConfig.eventId)):
            raise KnownUserError(
                "cancelConfig.eventId can not be none or empty.")

        if (Utils.isNilOrEmpty(cancelConfig.queueDomain)):
            raise KnownUserError(
                "cancelConfig.queueDomain can not be none or empty.")

        userInQueueService = KnownUser.__getUserInQueueService(
            httpContextProvider)
        result = userInQueueService.validateCancelRequest(
            targetUrl, cancelConfig, customerId, secretKey)
        result.isAjaxResult = KnownUser.__isQueueAjaxCall(httpContextProvider)

        return result

    @staticmethod
    def __handleQueueAction(currentUrlWithoutQueueITToken, queueitToken,
                            customerIntegration, customerId, secretKey,
                            matchedConfig, httpContextProvider, debugEntries, isDebug):
        queueConfig = QueueEventConfig()
        queueConfig.eventId = matchedConfig["EventId"]
        queueConfig.queueDomain = matchedConfig["QueueDomain"]
        queueConfig.layoutName = matchedConfig["LayoutName"]
        queueConfig.culture = matchedConfig["Culture"]
        queueConfig.cookieDomain = matchedConfig["CookieDomain"]
        queueConfig.actionName = matchedConfig["Name"]
        queueConfig.extendCookieValidity = matchedConfig[
            "ExtendCookieValidity"]
        queueConfig.cookieValidityMinute = matchedConfig[
            "CookieValidityMinute"]
        queueConfig.version = customerIntegration["Version"]

        redirectLogic = matchedConfig["RedirectLogic"]

        if (redirectLogic == "ForcedTargetUrl"):
            targetUrl = matchedConfig["ForcedTargetUrl"]
        elif (redirectLogic == "EventTargetUrl"):
            targetUrl = ""
        else:
            targetUrl = KnownUser.__generateTargetUrl(
                currentUrlWithoutQueueITToken, httpContextProvider)

        return KnownUser.__resolveQueueRequestByLocalConfig(
            targetUrl, queueitToken, queueConfig, customerId, secretKey,
            httpContextProvider, debugEntries, isDebug)

    @staticmethod
    def __handleCancelAction(currentUrlWithoutQueueITToken, queueitToken,
                             customerIntegration, customerId, secretKey,
                             matchedConfig, httpContextProvider, debugEntries, isDebug):
        cancelConfig = CancelEventConfig()
        cancelConfig.eventId = matchedConfig["EventId"]
        cancelConfig.queueDomain = matchedConfig["QueueDomain"]
        cancelConfig.cookieDomain = matchedConfig["CookieDomain"]
        cancelConfig.version = customerIntegration["Version"]
        cancelConfig.actionName = matchedConfig["Name"]

        return KnownUser.__cancelRequestByLocalConfig(
            currentUrlWithoutQueueITToken, queueitToken, cancelConfig,
            customerId, secretKey, httpContextProvider, debugEntries, isDebug)

    @staticmethod
    def extendQueueCookie(eventId, cookieValidityMinute, cookieDomain,
                          secretKey, httpContextProvider):
        if (Utils.isNilOrEmpty(eventId)):
            raise KnownUserError("eventId can not be none or empty.")

        if (Utils.isNilOrEmpty(secretKey)):
            raise KnownUserError("secretKey can not be none or empty.")

        minutes = QueueitHelpers.convertToInt(cookieValidityMinute)
        if (minutes <= 0):
            raise KnownUserError(
                "cookieValidityMinute should be integer greater than 0.")

        userInQueueService = KnownUser.__getUserInQueueService(
            httpContextProvider)
        userInQueueService.extendQueueCookie(eventId, cookieValidityMinute,
                                             cookieDomain, secretKey)

    @staticmethod
    def resolveQueueRequestByLocalConfig(targetUrl, queueitToken, queueConfig,
                                         customerId, secretKey,
                                         httpContextProvider):
        debugEntries = {}
        connectorDiagnostics = ConnectorDiagnostics.verify(customerId, secretKey, queueitToken)
        if (connectorDiagnostics.hasError):
            return connectorDiagnostics.validationResult
        try:
            targetUrl = KnownUser.__generateTargetUrl(targetUrl,
                                                      httpContextProvider)
            return KnownUser.__resolveQueueRequestByLocalConfig(
                targetUrl, queueitToken, queueConfig, customerId, secretKey,
                httpContextProvider, debugEntries, connectorDiagnostics.isEnabled)
        except Exception as e:
            if (connectorDiagnostics.isEnabled):
                debugEntries["Exception"] = e.message
            raise e
        finally:
            KnownUser.__setDebugCookie(debugEntries, httpContextProvider)

    @staticmethod
    def validateRequestByIntegrationConfig(
            currentUrlWithoutQueueITToken, queueitToken,
            integrationsConfigString, customerId, secretKey,
            httpContextProvider):

        debugEntries = {}
        customerIntegration = None
        connectorDiagnostics = ConnectorDiagnostics.verify(customerId, secretKey, queueitToken)
        if (connectorDiagnostics.hasError):
            return connectorDiagnostics.validationResult
        try:
            if (connectorDiagnostics.isEnabled):
                debugEntries["SdkVersion"] = UserInQueueService.SDK_VERSION
                debugEntries["Connector"] = httpContextProvider.getProviderName()
                debugEntries["Runtime"] = KnownUser.__getRunTime()
                debugEntries["PureUrl"] = currentUrlWithoutQueueITToken
                debugEntries["QueueitToken"] = queueitToken
                debugEntries["OriginalUrl"] = httpContextProvider.getOriginalRequestUrl()
                KnownUser.__logMoreRequestDetails(debugEntries, httpContextProvider)

            customerIntegration = json.loads(integrationsConfigString)
            if (connectorDiagnostics.isEnabled):
                debugEntries["ConfigVersion"] = customerIntegration["Version"] if customerIntegration and \
                                                                              customerIntegration["Version"] else "NULL"
            if (Utils.isNilOrEmpty(currentUrlWithoutQueueITToken)):
                raise KnownUserError(
                    "currentUrlWithoutQueueITToken can not be none or empty.")

            if (not customerIntegration or not customerIntegration["Version"]):
                raise KnownUserError(
                    "integrationsConfigString can not be none or empty.")
            matchedConfig = IntegrationEvaluator().getMatchedIntegrationConfig(
                customerIntegration, currentUrlWithoutQueueITToken,
                httpContextProvider)

            if (connectorDiagnostics.isEnabled):
                if (matchedConfig == None):
                    debugEntries["MatchedConfig"] = "NULL"
                else:
                    debugEntries["MatchedConfig"] = matchedConfig["Name"]

            if (matchedConfig is None):
                return RequestValidationResult(None, None, None, None, None, None)

            if (matchedConfig["ActionType"] == ActionTypes.QUEUE):
                return KnownUser.__handleQueueAction(
                    currentUrlWithoutQueueITToken, queueitToken,
                    customerIntegration, customerId, secretKey, matchedConfig,
                    httpContextProvider, debugEntries, connectorDiagnostics.isEnabled)
            elif (matchedConfig["ActionType"] == ActionTypes.CANCEL):
                return KnownUser.__handleCancelAction(
                    currentUrlWithoutQueueITToken, queueitToken,
                    customerIntegration, customerId, secretKey, matchedConfig,
                    httpContextProvider, debugEntries, connectorDiagnostics.isEnabled)
            else:  # for all unknown types default to 'Ignore'
                userInQueueService = KnownUser.__getUserInQueueService(
                    httpContextProvider) 
                result = userInQueueService.getIgnoreActionResult(matchedConfig['Name'])
                result.isAjaxResult = KnownUser.__isQueueAjaxCall(
                    httpContextProvider)
                return result
        except Exception as e:
            if (connectorDiagnostics.isEnabled):
                debugEntries["Exception"] = e.message
            raise e
        finally:
            KnownUser.__setDebugCookie(debugEntries, httpContextProvider)
            pass

    @staticmethod
    def cancelRequestByLocalConfig(targetUrl, queueitToken, cancelConfig,
                                   customerId, secretKey, httpContextProvider):
        debugEntries = {}
        connectorDiagnostics = ConnectorDiagnostics.verify(customerId, secretKey, queueitToken)
        if (connectorDiagnostics.hasError):
            return connectorDiagnostics.validationResult
        try:
            return KnownUser.__cancelRequestByLocalConfig(
                targetUrl, queueitToken, cancelConfig, customerId, secretKey,
                httpContextProvider, debugEntries, connectorDiagnostics.isEnabled)
        except Exception as e:
            if (connectorDiagnostics.isEnabled):
                debugEntries["Exception"] = e.message
            raise e
        finally:
            KnownUser.__setDebugCookie(debugEntries, httpContextProvider)
