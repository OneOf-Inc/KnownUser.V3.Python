from models import RequestValidationResult, ActionTypes, Utils
from queue_url_params import QueueUrlParams
from user_in_queue_state_cookie_repository import UserInQueueStateCookieRepository
from queueit_helpers import QueueitHelpers


class UserInQueueService:
    SDK_VERSION = "v3-python-" + "3.6.0"

    def __init__(self, httpContextProvider, userInQueueStateRepository):
        self.httpContextProvider = httpContextProvider
        self.userInQueueStateRepository = userInQueueStateRepository

    def __getQueueITTokenValidationResult(self, targetUrl, eventId, config,
                                          queueParams, customerId, secretKey):
        calculatedHash = QueueitHelpers.hmacSha256Encode(
            queueParams.queueITTokenWithoutHash, secretKey)

        if (calculatedHash.upper() != queueParams.hashCode.upper()):
            return self.__cancelQueueCookieReturnErrorResult(customerId, targetUrl,
                                                  config, queueParams, "hash")

        if (queueParams.eventId.upper() != eventId.upper()):
            return self.__cancelQueueCookieReturnErrorResult(
                customerId, targetUrl, config, queueParams, "eventid")

        if (queueParams.timeStamp <
                QueueitHelpers.getCurrentTime()):
            return self.__cancelQueueCookieReturnErrorResult(
                customerId, targetUrl, config, queueParams, "timestamp")

        cookieDomain = ""
        if (not Utils.isNilOrEmpty(config.cookieDomain)):
            cookieDomain = config.cookieDomain

        self.userInQueueStateRepository.store(
            config.eventId, queueParams.queueId,
            queueParams.cookieValidityMinutes, cookieDomain,
            queueParams.redirectType, secretKey)
        return RequestValidationResult(ActionTypes.QUEUE, config.eventId,
                                       queueParams.queueId, None,
                                       queueParams.redirectType, config.actionName)

    def __cancelQueueCookieReturnErrorResult(self, customerId, targetUrl, config, qParams, errorCode):
        self.userInQueueStateRepository.cancelQueueCookie(config.eventId, config.cookieDomain)
        timeStamp = str(QueueitHelpers.getCurrentTime())
        targetUrlParam = ""
        if (not Utils.isNilOrEmpty(targetUrl)):
            targetUrlParam = "&t={}".format(QueueitHelpers.urlEncode(targetUrl))

        queryString = self.__getQueryString(customerId, config.eventId, config.version, config.actionName,
                                      config.culture, config.layoutName)
        query = "{}&queueittoken={}&ts={}{}".format(queryString, qParams.queueITToken, timeStamp, targetUrlParam)
        redirectUrl = self.__generateRedirectUrl(config.queueDomain, "error/{}/".format(errorCode), query)

        return RequestValidationResult(ActionTypes.QUEUE, config.eventId, None, redirectUrl, None, config.actionName)

    def __cancelQueueCookieReturnQueueResult(self, targetUrl, config, customerId):
        self.userInQueueStateRepository.cancelQueueCookie(config.eventId, config.cookieDomain)
        targetUrlParam = ""
        if (not Utils.isNilOrEmpty(targetUrl)):
            targetUrlParam = "&t={}".format(QueueitHelpers.urlEncode(targetUrl))
        queryString = self.__getQueryString(customerId, config.eventId, config.version, config.actionName,
                                            config.culture, config.layoutName)
        query = "{}{}".format(queryString, targetUrlParam)
        redirectUrl = self.__generateRedirectUrl(config.queueDomain, "", query)

        return RequestValidationResult(ActionTypes.QUEUE, config.eventId, None, redirectUrl, None, config.actionName)

    def __generateRedirectUrl(self, queueDomain, uriPath, query):
        if (not queueDomain.endswith("/")):
            queueDomain = queueDomain + "/"

        return "https://{}{}?{}".format(queueDomain, uriPath, query)

    def __getQueryString(self, customerId, eventId, configVersion, actionName, culture,
                         layoutName):
        queryStringList = []
        queryStringList.append("c=" + QueueitHelpers.urlEncode(customerId))
        queryStringList.append("e=" + QueueitHelpers.urlEncode(eventId))
        queryStringList.append("ver=" + self.SDK_VERSION)
        queryStringList.append("kupver=" + QueueitHelpers.urlEncode(self.httpContextProvider.getProviderName()))
        if (configVersion is None):
            configVersion = "-1"
        queryStringList.append("cver=" + str(configVersion))
        queryStringList.append("man=" + QueueitHelpers.urlEncode(actionName))

        if (not Utils.isNilOrEmpty(culture)):
            queryStringList.append("cid=" + QueueitHelpers.urlEncode(culture))

        if (not Utils.isNilOrEmpty(layoutName)):
            queryStringList.append("l=" + QueueitHelpers.urlEncode(layoutName))

        return "&".join(queryStringList)

    def validateQueueRequest(self, targetUrl, queueitToken, config, customerId,
                             secretKey):
        state = self.userInQueueStateRepository.getState(
            config.eventId, config.cookieValidityMinute, secretKey, True)

        if (state.isValid):
            if (state.isStateExtendable() and config.extendCookieValidity):
                self.userInQueueStateRepository.store(
                    config.eventId, state.queueId, None,
                    Utils.toString(config.cookieDomain), state.redirectType,
                    secretKey)
            result = RequestValidationResult(ActionTypes.QUEUE, config.eventId,
                                             state.queueId, None,
                                             state.redirectType, config.actionName)
            return result

        queueParams = QueueUrlParams.extractQueueParams(queueitToken)
        if (queueParams is not None):
            return self.__getQueueITTokenValidationResult(
                targetUrl, config.eventId, config, queueParams, customerId,
                secretKey)
        else:
            return self.__cancelQueueCookieReturnQueueResult(targetUrl, config,
                                                   customerId)

    def validateCancelRequest(self, targetUrl, cancelConfig, customerId,
                              secretKey):
        state = self.userInQueueStateRepository.getState(
            cancelConfig.eventId, -1, secretKey, False)
        if (state.isValid):
            self.userInQueueStateRepository.cancelQueueCookie(
                cancelConfig.eventId, cancelConfig.cookieDomain)

            uri = "cancel/{}/{}/".format(customerId, cancelConfig.eventId)
            targetUrlParam = ""
            if (not Utils.isNilOrEmpty(targetUrl)):
                targetUrlParam = "&r={}".format(QueueitHelpers.urlEncode(targetUrl))
            queryString = self.__getQueryString(customerId, cancelConfig.eventId, cancelConfig.version,
                                                cancelConfig.actionName, None, None)
            query = "{}{}".format(queryString, targetUrlParam)
            redirectUrl = self.__generateRedirectUrl(cancelConfig.queueDomain, uri, query)

            return RequestValidationResult(ActionTypes.CANCEL,
                                           cancelConfig.eventId, state.queueId,
                                           redirectUrl, state.redirectType, cancelConfig.actionName)
        else:
            return RequestValidationResult(
                ActionTypes.CANCEL, cancelConfig.eventId, None, None, None, cancelConfig.actionName)

    def extendQueueCookie(self, eventId, cookieValidityMinutes, cookieDomain,
                          secretKey):
        self.userInQueueStateRepository.reissueQueueCookie(
            eventId, cookieValidityMinutes, cookieDomain, secretKey)

    def getIgnoreActionResult(self, actionName):
        return RequestValidationResult(ActionTypes.IGNORE, None, None, None, None, actionName)