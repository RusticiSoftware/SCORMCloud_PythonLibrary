import cgi
import copy
import datetime
import logging
import mimetools
import os.path
import re
import sys
import urllib
import urllib2
import uuid
import webbrowser
from xml.dom import minidom

# Smartly import hashlib and fall back on md5
try: from hashlib import md5
except ImportError: from md5 import md5


def make_utf8(dictionary):
    """
    Encodes all Unicode strings in the dictionary to UTF-8. Converts
    all other objects to regular strings.
    
    Returns a copy of the dictionary, doesn't touch the original.
    """
    
    result = {}
    for (key, value) in dictionary.iteritems():
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        else:
            value = str(value)
        result[key] = value
    return result


class Configuration(object):
    """
    Stores the configuration elements required by the API.
    """

    def __init__(self, appid, secret, 
                 serviceurl, origin='rusticisoftware.pythonlibrary.2.0.0'):
        self.appid = appid
        self.secret = secret
        self.serviceurl = serviceurl
        self.origin = origin;

    def __repr__(self):
        return 'Configuration for AppID %s from origin %s' % 
               (self.appid, self.origin)
        
class ScormCloudService(object):
    """
    Primary cloud service object that provides access to the more specific
    service areas, like the RegistrationService.
    """

    def __init__(self, configuration)
        self.config = configuration
        self.__handler_cache = {}
        
    @classmethod
    def withconfig(cls, config):
        """
        Named constructor that creates a ScormCloudService with the specified
        Configuration object.

        Arguments:
        config -- the Configuration object holding the required configuration
            values for the SCORM Cloud API
        """
        cls(config)

    @classmethod
    def withargs(cls, appid, secret, serviceurl, origin):
        """
        Named constructor that creates a ScormCloudService with the specified
        configuration values.

        Arguments:
        appid -- the AppID for the application defined in the SCORM Cloud
            account
        secret -- the secret key for the application
        serviceurl -- the service URL for the SCORM Cloud web service. For
            example, http://cloud.scorm.com/EngineWebServices
        origin -- the origin string for the application software using the
            API/Python client library
        """
        cls(Configuration(appid, secret, serviceurl, origin))

    def  __getattr__(self, attrib):    
        return self.attrib

    def get_course_service(self):
        """
        Retrieves the CourseService.
        """
        return CourseService(self)

    def get_debug_service(self):
        """
        Retrieves the DebugService.
        """
        return DebugService(self)

    def get_registration_service(self):
        """
        Retrieves the RegistrationService.
        """
        return RegistrationService(self)

    def get_reporting_service(self):
        """
        Retrieves the ReportingService.
        """
        return ReportingService(self)

    def get_upload_service(self):
        """
        Retrieves the UploadService.
        """
        return UploadService(self)
        
    def _sign(self, dictionary):
        """
        Returns the signature string for the method parameters.

        Arguments:
        dictionary -- the dictionary containing the key/value parameter pairs
        """
        data = [self.secret]
        for key in sorted(dictionary.keys()):
            data.append(key)
            datum = dictionary[key]
            if isinstance(datum, unicode):
                raise IllegalArgumentException("No Unicode allowed, "
                    "argument %s (%r) should have been UTF-8 by now"
                    % (key, datum))
            data.append(datum)
        md5_hash = md5(''.join(data))
        return md5_hash.hexdigest()
        
    def _encode_and_sign(self, dictionary):
        """
        URL encodes the data in the dictionary, and signs it using the
        given secret, if a secret was given.

        Arguments:
        dictionary -- the dictionary containing the key/value parameter pairs
        """ 
        dictionary['appid'] = self.appid
        dictionary['origin'] = self.origin;
        dictionary['ts'] = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        dictionary['applib'] = "python"
        dictionary = make_utf8(dictionary)
        if self.config.secret:
            dictionary['sig'] = self._sign(dictionary)
        return urllib.urlencode(dictionary)
    
    def make_call(self, **kwargs):
        post_data = self._encode_and_sign(kwargs)            
        url = ScormCloudUtilities.clean_cloud_host_url(self.servicehost)
        cloudsocket = urllib2.urlopen(url, post_data)
        reply = cloudsocket.read()
        cloudsocket.close()
        return reply
    

class DebugService(object):
    """
    Debugging and testing service that allows you to check the status of the
    SCORM Cloud and test your configuration settings.
    """

    def __init__(self, service)
        self.service = service

    def ping(self):
        """
        A simple ping that checks the connection to the SCORM Cloud.
        """
        data = self.service.make_call(method='rustici.debug.ping')
        xmldoc = minidom.parseString(data)
        return xmldoc.documentElement.attributes['stat'].value == 'ok'
    
    def authping(self):
        """
        An authenticated ping that checks the connection to the SCORM Cloud
        and verifies the configured credentials.
        """
        data = self.service.make_call(method='rustici.debug.authPing')
        xmldoc = minidom.parseString(data)
        return xmldoc.documentElement.attributes['stat'].value == 'ok'


class UploadService(object):
    """
    Service that provides functionality to upload files to the SCORM Cloud.
    """

    def __init__(self, service):
        self.service = service
        
    def get_upload_token(self):
        """
        Retrieves an upload token which must be used to successfully upload a
        file.
        """
        data = self.service.make_call(method='rustici.upload.getUploadToken')
        xmldoc = minidom.parseString(data)
        serverNodes = xmldoc.getElementsByTagName('server')
        tokenidNodes = xmldoc.getElementsByTagName('id')
        server = None
        for s in serverNodes:
            server = s.childNodes[0].nodeValue
        tokenid = None
        for t in tokenidNodes:
            tokenid = t.childNodes[0].nodeValue
        if server and tokenid:
            token = UploadToken(server,tokenid)
            return token
        else:
            return None

    def get_upload_url(self, callbackurl):
        """
        Returns a URL that can be used to upload a file via HTTP POST, through
        an HTML form element action, for example.
        """
        token = self.get_upload_token()
        if token:
            paramString = 'method=rustici.upload.uploadFile&appid=%s&'
                          'token=%s&redirecturl=%s' % 
                          (self.appid, token.tokenid, importurl)
            items = [s for s in paramString.split('&') if s]
            params = {}
            for item in items:
                key,value = item.split('=')
                params[key] = value
            
            sig = self.service.encode_and_sign(params)
            url =  '%s/api?' % (self.servicehost)
            url = url + sig
    
            return url
        else:
            return None
        
    def delete_file(self, location):
        """
        Deletes the specified file.
        """
        locParts = location.split("/")
        params = {}
        params['file'] = locParts[1]
        params['method'] = "rustici.upload.deleteFiles"
        return self.service.make_call(**params) 
        
    
class CourseService(object):
    """
    Service that provides methods to manage and interact with courses on the
    SCORM Cloud. These methods correspond to the "rustici.course.*" web service
    methods.
    """

    def __init__(self, service):
        self.service = service
        
    def import_uploaded_course(self, courseid, path):
        """
        Imports a SCORM PIF (zip file) from an existing zip file on the SCORM
        Cloud server.

        Arguments:
        courseid -- the unique identifier for the course
        path -- the relative path to the zip file to import
        """
        if courseid is None:
            courseid = str(uuid.uuid1())
        data = self.service.make_call(method='rustici.course.importCourse', path=path, courseid=courseid)
        ir = ImportResult.list_from_result(data)
        return ir
    
    def delete_course(self, courseid):
        """
        Deletes the specified course.

        Arguments:
        courseid -- the unique identifier for the course
        """
        params = {}
        params['courseid'] = courseid
        params['method'] = "rustici.course.deleteCourse"
        data = self.service.make_call(**params)

    def get_assets(self, courseid, path=None):
        """
        Downloads a file from a course by path. If no path is provided, all the
        course files will be downloaded contained in a zip file.

        Arguments:
        courseid -- the unique identifier for the course
        path -- the path (relative to the course root) of the file to download.
            If not provided or is None, all course files will be downloaded.
        """
        if (path is not None):
            data = self.service.make_call(method='rustici.course.getAssets',
                                          courseid=courseid, path=path)
        else:
            data = self.service.make_call(method='rustici.course.getAssets',
                                          courseid=courseid)
        return data
        
    def get_course_list(self, courseIdFilterRegex=None):
        """
        Retrieves a list of CourseData elements for all courses owned by the
        configured AppID that meet the specified filter criteria.

        Arguments:
        courseIdFilterRegex -- (optional) Regular expression to filter courses
            by ID
        """
        if courseIdFilterRegex is not None:
            data = self.service.make_call(method='rustici.course.getCourseList',
                                          filter=courseIdFilterRegex)
        else:
            data = self.service.make_call(method='rustici.course.getCourseList')
        courseList = CourseData.list_from_result(data)
        return courseList

    def get_preview_url(self, courseid, redirecturl, stylesheeturl=None):
        """
        Gets the URL that can be opened to preview the course without the need
        for a registration.

        Arguments:
        courseid -- the unique identifier for the course
        redirecturl -- the URL to which the browser should redirect upon course
            exit
        stylesheeturl -- the URL for the CSS stylesheet to include
        """
        params = {}
        params['method'] = "rustici.course.preview"
        params['courseid'] = courseid
        params['redirecturl'] = redirecturl
        if stylesheetUrl is not None:
            params['stylesheet'] = stylesheetUrl
        
        sig = self.service._encode_and_sign(params)
        url = '%s?' % (self.servicehost + '/api')
        url = url + sig
        logging.info('preview link: '+url)
        return url

    def get_metadata(self, courseid):
        """
        Gets the course metadata in XML format.

        Arguments:
        courseid -- the unique identifier for the course
        """
        data = self.service.make_call(method='rustici.course.getMetadata', 
                                      courseid=courseid)
        return data

    def get_property_editor_url(self, courseid, stylesheetUrl=None, 
                                notificationFrameUrl=None):
        """
        Gets the URL to view/edit the package properties for the course.
        Typically used within an IFRAME element.

        Arguments:
        courseid -- the unique identifier for the course
        stylesheeturl -- URL to a custom editor stylesheet
        notificationFrameUrl -- Tells the property editor to render a sub-iframe
            with this URL as the source. This can be used to simulate an 
            "onload" by using a notificationFrameUrl that is on the same domain 
            as the host system and calling parent.parent.method()
        """
        params = {}
        params['method'] = "rustici.course.properties"
        params['courseid'] = courseid
        if stylesheetUrl is not None:
            params['stylesheet'] = stylesheetUrl
        if notificationFrameUrl is not None:
            params['notificationframesrc'] = notificationFrameUrl
        
        sig = self.service._encode_and_sign(params)
        url = '%s?' % (self.servicehost + '/api')
        url = url + sig
        logging.info('properties link: '+url)
        return url
    
    def get_attributes(self, courseid, versionid=None):
        """
        Retrieves the list of associated attributes for the course. Will only
        retrieve the attributes for the most recent version of the course or
        the version specified.

        Arguments:
        courseid -- the unique identifier for the course
        versionid -- the specific version of the course
        """
        params = {}
        params['method'] = "rustici.course.getAttributes"
        params['courseid'] = courseid
        if versionid is not None:
            params['versionid'] = versionid
        
        data = self.service.make_call(**params)
        xmldoc = minidom.parseString(data)
        attrNodes = xmldoc.getElementsByTagName('attribute')
        atts = {}
        for an in attrNodes:
            atts[an.attributes['name'].value] = an.attributes['value'].value
        
        return atts
        
    def update_attributes(self, courseid, versionid, attributePairs):
        """
        Updates the specified attributes for the course. Will only update the
        attributes of the most recent version of the course or the version
        specified.

        Arguments:
        courseid -- the unique identifier for the course
        versionid -- the specific version of the course
        attributePairs -- the attribute name/value pairs to update
        """
        params = {}
        params['method'] = "rustici.course.updateAttributes"
        params['courseid'] = courseid
        if versionid is not None:
            params['versionid'] = versionid
        
        for (key, value) in attributePairs.iteritems():
            params[key] = value
        
        data = self.service.make_call(**params)
        xmldoc = minidom.parseString(data)
        attrNodes = xmldoc.getElementsByTagName('attribute')
        atts = {}
        for an in attrNodes:
            atts[an.attributes['name'].value] = an.attributes['value'].value

        return atts
        

class RegistrationService(object):
    """
    Service that provides methods for managing and interacting with
    registrations on the SCORM Cloud. These methods correspond to the
    "rustici.registration.*" web service methods.
    """

    def __init__(self, service):
        self.service = service
        
    def create_registration(self, regid, courseid, userid, fname, lname, 
                            email=None):
        """
        Creates a new registration (an instance of a user taking a course).

        Arguments:
        regid -- the unique identifier for the registration
        courseid -- the unique identifier for the course
        userid -- the unique identifier for the learner
        fname -- the learner's first name
        lname -- the learner's last name
        email -- the learner's email address
        """
        if regid is None:
            regid = str(uuid.uuid1())
        params = {}
        params['method'] = "rustici.registration.createRegistration"
        params['appid'] = self.appid
        params['courseid'] = courseid
        params['regid'] = regid
        params['fname'] = fname
        params['lname'] = lname
        params['learnerid'] = userid
        if email is not None:
            params['email'] = email
        data = self.service.make_call(**params)
        xmldoc = minidom.parseString(data)
        successNodes = xmldoc.getElementsByTagName('success')
        if successNodes.length == 0:
            raise ScormCloudError("Create Registration failed.  " + 
                                  xmldoc.err.attributes['msg'])
        return regid
        
    def get_launch_url(self, regid, redirecturl, cssUrl=None, courseTags=None, 
                       learnerTags=None, registrationTags=None):
        """
        Gets the URL to directly launch the course in a web browser.
        
        Arguments:
        regid -- the unique identifier for the registration
        redirecturl -- the URL to which the SCORM player will redirect upon
            course exit
        cssUrl -- the URL to a custom stylesheet
        courseTags -- comma-delimited list of tags to associate with the
            launched course
        learnerTags -- comma-delimited list of tags to associate with the
            learner launching the course
        registrationTags -- comma-delimited list of tags to associate with the
            launched registration
        """
        redirecturl = redirecturl + "?regid=" + regid
        paramString = 'method|rustici.registration.launch!appid|%s'
                      '!redirecturl|%s!regid|%s' % 
                      (self.appid, cgi.escape(redirecturl), regid)
        paramString += ((courseTags is not None) and ('!courseTags|%s' % 
                       (courseTags)) or '')
        paramString += ((learnerTags is not None) and ('!learnerTags|%s' % 
                       (learnerTags)) or '')
        paramString += ((registrationTags is not None) and 
                       ('!registrationTags|%s' % (registrationTags)) or '')
        items = [s for s in paramString.split('!') if s]
        params = {}
        for item in items:
            key,value = item.split('|')
            params[key] = value

        sig = self.service.encode_and_sign(params)
        url = '%s?' % (self.servicehost + '/api')
        url = url + sig
        return url
    
    def get_registration_list(self, regIdFilterRegex=None, 
                              courseIdFilterRegex=None):
        """
        Retrieves a list of registration associated with the configured AppID.
        Can optionally be filtered by registration or course ID.

        Arguments:
        regIdFilterRegex -- (optional) the regular expression used to filter the 
            list by registration ID
        courseIdFilterRegex -- (optional) the regular expression used to filter
            the list by course ID
        """
        params = {}
        params['method'] = "rustici.registration.getRegistrationList"
        if regIdFilterRegex is not None:
            params['filter'] = regIdFilterRegex
        if courseIdFilterRegex is not None:
            params['coursefilter'] = courseIdFilterRegex
            
        data = self.service.make_call(**params)
        regList = RegistrationData.ConvertToRegistrationDataList(data)
        return regList
        
    def get_registration_result(self, regid, resultsformat):
        """
        Gets information about the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        resultsformat -- (optional) can be "course", "activity", or "full" to
            determine the level of detail returned. The default is "course"
        """
        params = {}
        params['method'] = "rustici.registration.getRegistrationResult"
        params['regid'] = regid
        params['resultsformat']= resultsformat
        data = self.service.make_call(**params)
        return data

    def get_launch_history(self, regid):
        """
        Retrieves a list of LaunchInfo objects describing each launch. These
        LaunchInfo objects do not contain the full launch history log; use
        get_launch_info to retrieve the full launch information.

        Arguments:
        regid -- the unique identifier for the registration
        """
        data = self.service.make_call(
                method='rustici.registration.getLaunchHistory', regid=regid)
        return data
        
    def reset_registration(self, regid):
        """
        Resets all status data for the specified registration, essentially
        restarting the course for the associated learner.

        Arguments:
        regid -- the unique identifier for the registration
        """
        data = self.service.make_call(
                method='rustici.registration.resetRegistration', regid=regid)
        return data
        
    def reset_global_objectives(self, regid):
        """
        Clears global objective data for the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        """
        params = {}
        params['method'] = "rustici.registration.resetGlobalObjectives"
        params['regid'] = regid
        data = self.service.make_call(**params)
        return data
        
    def delete_registration(self, regid):
        """
        Deletes the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        """
        params = {}
        params['method'] = "rustici.registration.deleteRegistration"
        params['regid'] = regid
        data = self.service.make_call(**params)
        return data
        

class ReportingService(object):
    """
    Service that provides methods for interacting with the Reportage service.
    """

    def __init__(self, service):
        self.service = service
    
    def get_reportage_date(self):
        """
        Gets the date/time, according to Reportage.
        """
        reportUrl = self.GetReportageServiceUrl() + 
                    'Reportage/scormreports/api/getReportDate.php?appId=' + 
                    self.appid
        cloudsocket = urllib2.urlopen(reportUrl,None)
        reply = cloudsocket.read()
        cloudsocket.close()
        d = datetime.datetime
        return d.strptime(reply,"%Y-%m-%d %H:%M:%S")
        
    def get_reportage_auth(self, navPermission, isAdmin):
        """
        Authenticates against the Reportage application, returning a session
        string used to make subsequent calls to launchReport.

        Arguments:
        navPermissions -- the Reportage navigation permissions to assign to the
            session. If "NONAV", the session will be prevented from navigating
            away from the original report/widget. "DOWNONLY" allows the user to
            drill down into additional detail. "FREENAV" allows the user full
            navigation privileges and the ability to change any reporting
            parameter.
        isAdmin -- if True, the Reportage session will have admin privileges
        """
        data = self.service.make_call(
                method='rustici.reporting.getReportageAuth', 
                navpermission=navPermission, admin=str(isAdmin))
        xmldoc = minidom.parseString(data)
        token = xmldoc.getElementsByTagName('auth')
        if token.length > 0:
            return token[0].childNodes[0].nodeValue
        else:
            return None
        
    def _get_reportage_service_url(self):
        """
        Returns the base Reportage URL.
        """
        return self.service.config.serviceurl.replace('EngineWebServices','')
        
    def get_report_url(self, auth, reportUrl):
        """
        Returns an authenticated URL that can launch a Reportage session at
        the specified Reportage entry point.

        Arguments:
        auth -- the Reportage authentication string, as retrieved from
            get_reportage_auth
        reportUrl -- the URL to the desired Reportage entry point
        """
        params = {}
        params['method'] = 'rustici.reporting.launchReport'
        params['auth'] = auth
        params['reporturl'] = reportUrl
        sig = self.service.encode_and_sign(params)
        url = '%s?' % (self.servicehost + '/api')
        url = url + sig
        return url
         
    def get_widget_url(self, auth, widgettype, widgetSettings):
        """
        Gets the URL to a specific Reportage widget, using the provided
        widget settings.

        Arguments:
        auth -- the Reportage authentication string, as retrieved from
            get_reportage_auth
        widgettype -- the widget type desired (for example, learnerSummary)
        widgetSettings -- the WidgetSettings object for the widget type
        """
        reportUrl = self._get_reportage_service_url() + 
                    'Reportage/scormreports/widgets/'
        widgetUrlTypeLib = {
            'allSummary':'summary/SummaryWidget.php?srt=allLearnersAllCourses',
            'courseSummary':'summary/SummaryWidget.php?srt=singleCourse',
            'learnerSummary':'summary/SummaryWidget.php?srt=singleLearner',
            'learnerCourse':'summary/SummaryWidget.php?srt='
                            'singleLearnerSingleCourse',
            'courseActivities':'DetailsWidget.php?drt=courseActivities',
            'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
            'courseComments':'DetailsWidget.php?drt=courseComments',
            'learnerComments':'DetailsWidget.php?drt=learnerComments',
            'courseInteractions':'DetailsWidget.php?drt=courseInteractions',
            'learnerInteractions':'DetailsWidget.php?drt=learnerInteractions',
            'learnerActivities':'DetailsWidget.php?drt=learnerActivities',
            'courseRegistration':'DetailsWidget.php?drt=courseRegistration',
            'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
            'learnerCourseActivities':'DetailsWidget.php?drt='
                                      'learnerCourseActivities',
            'learnerTranscript':'DetailsWidget.php?drt=learnerTranscript',
            'learnerCourseInteractions':'DetailsWidget.php?drt='
                                        'learnerCourseInteractions',
            'learnerCourseComments':'DetailsWidget.php?drt='
                                    'learnerCourseComments',
            'allLearners':'ViewAllDetailsWidget.php?viewall=learners',
            'allCourses':'ViewAllDetailsWidget.php?viewall=courses'}
        reportUrl += widgetUrlTypeLib[widgettype]
        reportUrl += '&appId='+self.appid
        reportUrl += widgetSettings.get_url_encoding()
        reportUrl = self.get_report_url(auth,reportUrl)
        return reportUrl
        

class WidgetSettings(object):
    def __init__(self, dateRangeSettings, tagSettings):
        self.dateRangeSettings = dateRangeSettings
        self.tagSettings = tagSettings
        
        self.courseId = None
        self.learnerId = None
        
        self.showTitle = True;
        self.vertical = False;
        self.public = True;
        self.standalone = True;
        self.iframe = False;
        self.expand = True;
        self.scriptBased = True;
        self.divname = '';
        self.embedded = True;
        self.viewall = True;
        self.export = True;
        
        
    def get_url_encoding(self):
        """
        Returns the widget settings as encoded URL parameters to add to a 
        Reportage widget URL.
        """
        widgetUrlStr = '';
        if self.courseId is not None:
            widgetUrlStr += '&courseId=' + self.courseId
        if self.learnerId is not None:
            widgetUrlStr += '&learnerId=' + self.learnerId
        
        widgetUrlStr += '&showTitle=' + `self.showTitle`.lower()
        widgetUrlStr += '&standalone=' + `self.standalone`.lower()
        if self.iframe:
            widgetUrlStr += '&iframe=true'
        widgetUrlStr += '&expand=' + `self.expand`.lower()
        widgetUrlStr += '&scriptBased=' + `self.scriptBased`.lower()
        widgetUrlStr += '&divname=' + self.divname
        widgetUrlStr += '&vertical=' + `self.vertical`.lower()
        widgetUrlStr += '&embedded=' + `self.embedded`.lower()

        if self.dateRangeSettings is not None:
            widgetUrlStr += self.dateRangeSettings.get_url_encoding()

        if self.tagSettings is not None:
            widgetUrlStr += self.tagSettings.get_url_encoding()
        
        return widgetUrlStr

    
class DateRangeSettings(object):
    def __init__(self, dateRangeType, dateRangeStart, 
                 dateRangeEnd, dateCriteria):
        self.dateRangeType=dateRangeType
        self.dateRangeStart=dateRangeStart
        self.dateRangeEnd=dateRangeEnd        
        self.dateCriteria=dateCriteria
        
    def get_url_encoding(self):
        """
        Returns the DateRangeSettings as encoded URL parameters to add to a
        Reportage widget URL.
        """
        dateRangeStr = ''
        if self.dateRangeType == 'selection':
            dateRangeStr +='&dateRangeType=c'
            dateRangeStr +='&dateRangeStart=' + self.dateRangeStart
            dateRangeStr +='&dateRangeEnd=' + self.dateRangeEnd
        else:
            dateRangeStr +='&dateRangeType=' + self.dateRangeType
        
        dateRangeStr += '&dateCriteria=' + self.dateCriteria
        return dateRangeStr
        
class TagSettings(object):
    def __init__(self):
        self.tags = {'course':[],'learner':[],'registration':[]}
    
    def add(self, tagType, tagValue):
        self.tags[tagType].append(tagValue)
        
    def get_tag_str(self, tagType):
        return ','.join(set(self.tags[tagType])) + "|_all"

    def get_view_tag_str(self, tagType):
        return ','.join(set(self.tags[tagType]))
        
    def get_url_encoding(self):
        tagUrlStr = ''
        for k in self.tags.keys():
            if len(set(self.tags[k])) > 0:
                tagUrlStr += '&' + k + 'Tags=' + self.get_tag_str(k)
                tagUrlStr += '&view' + k.capitalize() + 'TagGroups=' + 
                             self.get_view_tag_str(k)
        return tagUrlStr
    
    
class ScormCloudError(Exception):
    def __init__(self, msg, json=None):
        self.msg = msg
        self.json = json
    def __str__(self):
        return repr(self.msg)

class ImportResult(object):
    wasSuccessful = False
    title = ""
    message = ""
    parserWarnings = []

    def __init__(self,importResultElement):
        if importResultElement is not None:
            self.wasSuccessful = importResultElement.attributes['successful']
                                 .value == 'true'
            self.title = importResultElement.getElementsByTagName("title")[0]
                         .childNodes[0].nodeValue
            self.message = importResultElement
                           .getElementsByTagName("message")[0]
                           .childNodes[0].nodeValue
            xmlpw = importResultElement.getElementsByTagName("warning")
            for pw in xmlpw:
                self.parserWarnings.append(pw.childNodes[0].nodeValue)

    def  __getattr__(self, attrib):
        return self.attrib

    @classmethod
    def list_from_result(cls, data):
        """
        Returns a list of ImportResult objects by parsing the raw result of an
        API method that returns importresult elements.

        Arguments:
        data -- the raw result of the API method
        """
        xmldoc = minidom.parseString(data)
        allResults = [];
        importresults = xmldoc.getElementsByTagName("importresult")
        for ir in importresults:
            allResults.append(cls(ir))
        return allResults    

class CourseData(object):
    courseId = ""
    numberOfVersions = 1
    numberOfRegistrations = 0
    title = ""

    def __init__(self,courseDataElement):
        if courseDataElement is not None:
            self.courseId = courseDataElement.attributes['id'].value
            self.numberOfVersions = courseDataElement.attributes['versions']
                                    .value
            self.numberOfRegistrations = courseDataElement
                                        .attributes['registrations'].value
            self.title = courseDataElement.attributes['title'].value;

    def  __getattr__(self, attrib):
        return self.attrib

    @classmethod
    def list_from_result(cls, data):
        """
        Returns a list of CourseData objects by parsing the raw result of an
        API method that returns course elements.

        Arguments:
        data -- the raw result of the API method
        """
        xmldoc = minidom.parseString(data)
        allResults = [];
        courses = xmldoc.getElementsByTagName("course")
        for course in courses:
            allResults.append(cls(course))
        return allResults

class UploadToken(object):
    server = ""
    tokenid = ""
    def __init__(self,server,tokenid):
        self.server = server
        self.tokenid = tokenid

    def __getattr__(self, attrib):
        return self.attrib
        
class RegistrationData(object):
    courseId = ""
    registrationId = ""

    def __init__(self,regDataElement):
        if regDataElement is not None:
            self.courseId = regDataElement.attributes['courseid'].value
            self.registrationId = regDataElement.attributes['id'].value

    def  __getattr__(self, attrib):
        return self.attrib

    @classmethod
    def list_from_result(cls, data):
        """
        Returns a list of RegistrationData objects by parsing the result of an
        API method that returns registration elements.

        Arguments:
        data -- the raw result of the API method
        """
        xmldoc = minidom.parseString(data)
        allResults = [];
        regs = xmldoc.getElementsByTagName("registration")
        for reg in regs:
            allResults.append(cls(reg))
        return allResults

class ScormCloudUtilities(object):
    """
    Provides utility functions for working with the SCORM Cloud.
    """

    @staticmethod
    def get_canonical_origin_string(organization, application, version):
        """
        Helper function to build a proper origin string to provide to the
        SCORM Cloud configuration. Takes the organization name, application
        name, and application version.

        Arguments:
        organization -- the name of the organization that created the software
            using the Python Cloud library
        application -- the name of the application software using the Python
            Cloud library
        version -- the version string for the application software
        """
        namepattern = re.compile(r'[^a-z0-9]')
        versionpattern = re.compile(r'[^a-z0-9\.\-]')
        org = namepattern.sub('', organization.lower())
        app = namepattern.sub('', application.lower())
        ver = versionpattern.sub('', version.lower())
        return "%s.%s.%s" % (org, app, ver)

    @staticmethod
    def clean_cloud_host_url(url):
        """
        Simple function that helps ensure a working API URL. Assumes that the
        URL of the host service ends with /api and processes the given URL to
        meet this assumption.

        Arguments:
        url -- the URL for the Cloud service, typically as entered by a user
            in their configuration
        """
        parts = url.split('/')
        if not parts[len(parts) - 1] == 'api':
            parts.append('api')
        return '/'.join(parts)

