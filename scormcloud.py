import sys
import urllib
import urllib2
import mimetools
import os.path
import logging
import copy
import webbrowser
import datetime

import cgi
# Smartly import hashlib and fall back on md5
try: from hashlib import md5
except ImportError: from md5 import md5

from xml.dom import minidom
import uuid


def make_utf8(dictionary):
    '''Encodes all Unicode strings in the dictionary to UTF-8. Converts
    all other objects to regular strings.
    
    Returns a copy of the dictionary, doesn't touch the original.
    '''
    
    result = {}

    for (key, value) in dictionary.iteritems():
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        else:
            value = str(value)
        result[key] = value
    
    return result

class SCORMCloudAPI(object):
	def __init__(self, appid, secret, servicehost):        
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost
		self.__handler_cache = {}
		
	def __repr__(self):
		'''Returns a string representation of this object.'''
		return '[appid for key "%s"]' % self.appid
		
	def  __getattr__(self, attrib):	
		return self.attrib
		
	def sign(self, dictionary):
		data = [self.secret]
		for key in sorted(dictionary.keys()):
			data.append(key)
			datum = dictionary[key]
			if isinstance(datum, unicode):
				raise IllegalArgumentException("No Unicode allowed, "
					"argument %s (%r) should have been UTF-8 by now"% (key, datum))
			data.append(datum)
		md5_hash = md5(''.join(data))
		return md5_hash.hexdigest()
		
	def encode_and_sign(self, dictionary):
		'''URL encodes the data in the dictionary, and signs it using the
		given secret, if a secret was given.
		'''
		dictionary['appid'] = self.appid
		dictionary['ts'] = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
		dictionary = make_utf8(dictionary)
		if self.secret:
			dictionary['sig'] = self.sign(dictionary)
			
		return urllib.urlencode(dictionary)

	
	def scormcloud_call(self, **kwargs):
		post_data = self.encode_and_sign(kwargs)		    
		url = self.servicehost + '/api'
		cloudsocket = urllib2.urlopen(url,post_data)
		reply = cloudsocket.read()
		cloudsocket.close()
		return reply
	
				


# ************   Debug Service   **********************
#*******************************************************

class DebugService(object):
	def __init__(self, appid, secret, servicehost):
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost		
	
	def CloudAuthPing(self):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.debug.authPing')
		xmldoc = minidom.parseString(data)
		#logging.info('cloudauthping: ' + str(xmldoc.documentElement.attributes['stat'].value))
		return xmldoc.documentElement.attributes['stat'].value == 'ok'

	def CloudPing(self):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.debug.ping')
		xmldoc = minidom.parseString(data)
		return xmldoc.documentElement.attributes['stat'].value == 'ok'


# ************   Upload Service   **********************
#*******************************************************
class UploadService(object):
	def __init__(self, appid, secret, servicehost):
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost
		
	def GetUploadToken(self):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.upload.getUploadToken')
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

	#deprecated for library uniformity
	def GetUploadLink(self,importurl):
		return GetUploadUrl(importurl)

	def GetUploadUrl(self,importurl):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		token = self.GetUploadToken()
		if token:
			paramString = 'method=rustici.upload.uploadFile&appid=%s&token=%s&redirecturl=%s' % (self.appid, token.tokenid, importurl)
			items = [s for s in paramString.split('&') if s]
			params = {}
			for item in items:
				key,value = item.split('=')
				params[key] = value
			
			sig = sc.encode_and_sign(params)
			url =  '%s/api?' % (self.servicehost)
			url = url + sig
	
			return url
		else:
			return None
		
	def DeleteFile(self,location):
		locParts = location.split("/")
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['file'] = locParts[1]
		params['method'] = "rustici.upload.deleteFiles"
		
		return sc.scormcloud_call(**params) 
		
	
		
# ************   Course Service   **********************
#*******************************************************
class CourseService(object):
	def __init__(self, appid, secret, servicehost):
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost
		
	def ImportUploadedCourse(self,courseid,path):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		if courseid is None:
			courseid = str(uuid.uuid1())
		data = sc.scormcloud_call(method='rustici.course.importCourse', path=path, courseid=courseid)
		#logging.debug('import response: ' + data)
		ir = ImportResult.ConvertToImportResults(data)
		return ir
	
	def DeleteCourse(self, courseid, deleteLatestVersionOnly = False):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['courseid'] = courseid
		params['method'] = "rustici.course.deleteCourse"
		if deleteLatestVersionOnly:
			params['versionid'] = 'latest'
		data = sc.scormcloud_call(**params)
		
	def GetCourseList(self, courseIdFilterRegex = None):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		if courseIdFilterRegex is not None:
			data = sc.scormcloud_call(method='rustici.course.getCourseList', filter=courseIdFilterRegex)
		else:
			data = sc.scormcloud_call(method='rustici.course.getCourseList')
		courseList = CourseData.ConvertToCourseDataList(data)
		return courseList

	#deprecated for library uniformity
	def GetPreviewLink(self, courseid, redirecturl):
		return GetPreviewUrl(courseid, redirecturl)
		
	def GetPreviewUrl(self, courseid, redirecturl,stylesheetUrl = None):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.course.preview"
		params['courseid'] = courseid
		params['redirecturl'] = redirecturl
		if stylesheetUrl is not None:
			params['stylesheet'] = stylesheetUrl
		
		sig = sc.encode_and_sign(params)
		url = '%s?' % (self.servicehost + '/api')
		url = url + sig
		logging.info('preview link: '+url)
		return url

	def GetCourseMetadata(self, courseid):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.course.getMetadata', courseid=courseid)
		return data

	def GetPropertyEditorUrl(self, courseid, stylesheetUrl = None, notificationFrameUrl=None ):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.course.properties"
		params['courseid'] = courseid
		if stylesheetUrl is not None:
			params['stylesheet'] = stylesheetUrl
		if notificationFrameUrl is not None:
			params['notificationframesrc'] = notificationFrameUrl
		
		sig = sc.encode_and_sign(params)
		url = '%s?' % (self.servicehost + '/api')
		url = url + sig
		logging.info('properties link: '+url)
		return url
	
	def GetAttributes(self,courseid, versionid=None):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		
		params = {}
		params['method'] = "rustici.course.getAttributes"
		params['courseid'] = courseid
		if versionid is not None:
			params['versionid'] = versionid
		
		data = sc.scormcloud_call(**params)
		xmldoc = minidom.parseString(data)
		attrNodes = xmldoc.getElementsByTagName('attribute')
		atts = {}
		for an in attrNodes:
			atts[an.attributes['name'].value] = an.attributes['value'].value
		
		return atts
		
		
	def UpdateAttributes(self, courseid, versionid, attributePairs):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.course.updateAttributes"
		params['courseid'] = courseid
		if versionid is not None:
			params['versionid'] = versionid
		
		for (key, value) in attributePairs.iteritems():
			params[key] = value
		
		data = sc.scormcloud_call(**params)
		xmldoc = minidom.parseString(data)
		attrNodes = xmldoc.getElementsByTagName('attribute')
		atts = {}
		for an in attrNodes:
			atts[an.attributes['name'].value] = an.attributes['value'].value

		return atts
		
		
		
# ************   Registration Service   **********************
# ************************************************************

class RegistrationService(object):
	def __init__(self, appid, secret, servicehost):
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost
		
		
	def CreateRegistration(self, regid,courseid,userid,fname,lname):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		if regid is None:
			regid = str(uuid.uuid1())
		data = sc.scormcloud_call(method='rustici.registration.createRegistration', appid=self.appid, courseid=courseid, regid=regid, fname=fname, lname=lname,learnerid=userid)
		#logging.info('CreateRegistration result: ' + str(data))
		xmldoc = minidom.parseString(data)
		successNodes = xmldoc.getElementsByTagName('success')
		if successNodes.length == 0:
			raise ScormCloudError("Create Registration failed.  " + xmldoc.err.attributes['msg'] )
		return regid
		
	
		
	def GetLaunchLink(self, regid, redirecturl,courseTags=None,learnerTags=None,registrationTags=None):
		return GetLaunchUrl(self, regid, redirecturl,courseTags,learnerTags,registrationTags)
	
	def GetLaunchUrl(self, regid, redirecturl, cssUrl=None,debugLogPointerUrl=None,courseTags=None,learnerTags=None,registrationTags=None):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		redirecturl = redirecturl + "?regid=" + regid
		paramString = 'method|rustici.registration.launch!appid|%s!redirecturl|%s!regid|%s' % (self.appid, cgi.escape(redirecturl),regid)
		paramString += ((courseTags is not None) and ('!courseTags|%s' % (courseTags)) or '')
		paramString += ((learnerTags is not None) and ('!learnerTags|%s' % (learnerTags)) or '')
		paramString += ((registrationTags is not None) and ('!registrationTags|%s' % (registrationTags)) or '')
		items = [s for s in paramString.split('!') if s]
		params = {}
		for item in items:
			key,value = item.split('|')
			params[key] = value

		sig = sc.encode_and_sign(params)
		url = '%s?' % (self.servicehost + '/api')
		url = url + sig
		#logging.info('launchurl:  ' + url)
		return url
	
	def GetRegistrationList(self,regIdFilterRegex=None,courseIdFilterRegex=None):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.registration.getRegistrationList"
		if regIdFilterRegex is not None:
			params['filter'] = regIdFilterRegex
		if courseIdFilterRegex is not None:
			params['coursefilter'] = courseIdFilterRegex
			
		data = sc.scormcloud_call(**params)
		regList = RegistrationData.ConvertToRegistrationDataList(data)
		return regList
		
		
	def GetRegistrationResult(self, regid, resultsformat,dataformat=None):
		#course, activity, full
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.registration.getRegistrationResult"
		params['regid'] = regid
		params['resultsformat']= resultsformat
		if dataformat is not None:
			params['format'] = dataformat
		data = sc.scormcloud_call(**params)
		#xmldoc = minidom.parseString(data)
		#title = xmldoc.getElementsByTagName("title")[0].childNodes[0].nodeValue
		return data

	def GetLaunchHistory(self, regid):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.registration.getLaunchHistory', regid=regid)
		
		return data
		

	def ResetRegistration(self, regid):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.registration.resetRegistration', regid=regid)
		return data
		
		
	def ResetGlobalObjectives(self,regid,deleteLatestInstanceOnly=True):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.registration.resetGlobalObjectives"
		params['regid'] = regid
		if deleteLatestInstanceOnly:
			params['instanceid'] = 'latest'	
		
		data = sc.scormcloud_call(**params)
		return data
		
	def DeleteRegistration(self, regid, deleteLatestInstanceOnly = False):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		params = {}
		params['method'] = "rustici.registration.deleteRegistration"
		params['regid'] = regid
		if deleteLatestInstanceOnly:
			params['instanceid'] = 'latest'	
		
		data = sc.scormcloud_call(**params)
		return data
		
# ************   Reporting Service   **********************
# ************************************************************

class ReportingService(object):
	def __init__(self, appid, secret, servicehost):
		self.appid = appid
		self.secret = secret
		self.servicehost = servicehost
	
	def GetReportageDate(self):
		reportUrl = self.GetReportageServiceUrl() + 'Reportage/scormreports/api/getReportDate.php?appId=' + self.appid
		cloudsocket = urllib2.urlopen(reportUrl,None)
		reply = cloudsocket.read()
		cloudsocket.close()
		d = datetime.datetime
		return d.strptime(reply,"%Y-%m-%d %H:%M:%S")

		    
		
	def GetReportageAuth(self,navPermission, isAdmin):
		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)
		data = sc.scormcloud_call(method='rustici.reporting.getReportageAuth',navpermission=navPermission,admin=str(isAdmin))
		xmldoc = minidom.parseString(data)
		token = xmldoc.getElementsByTagName('auth')
		#logging.info('auth:  '+token[0].childNodes[0].nodeValue)
		if token.length > 0:
			return token[0].childNodes[0].nodeValue
		else:
			return None
		
	def GetReportageServiceUrl(self):
		return self.servicehost.replace('EngineWebServices','')
		#return "http://troymac/"
		
	def GetReportUrl(self,auth,reportUrl):

		sc = SCORMCloudAPI(self.appid, self.secret, self.servicehost)

		params = {}
		params['method'] = 'rustici.reporting.launchReport'
		params['auth'] = auth
		params['reporturl'] = reportUrl
		
		sig = sc.encode_and_sign(params)
		url = '%s?' % (self.servicehost + '/api')
		url = url + sig

		return url
		 
	def	GetWidgetUrl(self,auth,widgettype, widgetSettings):
		reportUrl = self.GetReportageServiceUrl() + 'Reportage/scormreports/widgets/'

		widgetUrlTypeLib = {
			'allSummary':'summary/SummaryWidget.php?srt=allLearnersAllCourses',
			'courseSummary':'summary/SummaryWidget.php?srt=singleCourse',
			'learnerSummary':'summary/SummaryWidget.php?srt=singleLearner',
			'learnerCourse':'summary/SummaryWidget.php?srt=singleLearnerSingleCourse',
			'courseActivities':'DetailsWidget.php?drt=courseActivities',
			'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
			'courseComments':'DetailsWidget.php?drt=courseComments',
			'learnerComments':'DetailsWidget.php?drt=learnerComments',
			'courseInteractions':'DetailsWidget.php?drt=courseInteractions',
			'learnerInteractions':'DetailsWidget.php?drt=learnerInteractions',
			'learnerActivities':'DetailsWidget.php?drt=learnerActivities',
			'courseRegistration':'DetailsWidget.php?drt=courseRegistration',
			'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
			'learnerCourseActivities':'DetailsWidget.php?drt=learnerCourseActivities',
			'learnerTranscript':'DetailsWidget.php?drt=learnerTranscript',
			'learnerCourseInteractions':'DetailsWidget.php?drt=learnerCourseInteractions',
			'learnerCourseComments':'DetailsWidget.php?drt=learnerCourseComments',
			'allLearners':'ViewAllDetailsWidget.php?viewall=learners',
			'allCourses':'ViewAllDetailsWidget.php?viewall=courses'}
		
		reportUrl += widgetUrlTypeLib[widgettype]
		reportUrl += '&appId='+self.appid
		
		reportUrl += widgetSettings.GetWidgetSettingsUrlStr()
		
		reportUrl = self.GetReportUrl(auth,reportUrl)
		
		return reportUrl
		
class WidgetSettings(object):
	
	
	def __init__(self,dateRangeSettings,tagSettings):
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
		
	
		
	def GetWidgetSettingsUrlStr(self):
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
			widgetUrlStr += self.dateRangeSettings.GetDateRangeUrlStr()

		if self.tagSettings is not None:
			widgetUrlStr += self.tagSettings.GetTagURLStr()
		
		return widgetUrlStr

	
class DateRangeSettings(object):
	def __init__(self,dateRangeType,dateRangeStart,dateRangeEnd,dateCriteria):
		self.dateRangeType=dateRangeType
		self.dateRangeStart=dateRangeStart
		self.dateRangeEnd=dateRangeEnd		
		self.dateCriteria=dateCriteria
		
	def GetDateRangeUrlStr(self):
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
	
	def AddTag(self,tagType,tagValue):
		self.tags[tagType].append(tagValue)
		
	def GetTagString(self,tagType):
		return ','.join(set(self.tags[tagType])) + "|_all"
	def GetViewTagString(self,tagType):
		return ','.join(set(self.tags[tagType]))
		
	def GetTagURLStr(self):
		tagUrlStr = ''
		for k in self.tags.keys():
			if len(set(self.tags[k])) > 0:
				tagUrlStr += '&' + k + 'Tags=' + self.GetTagString(k)
				tagUrlStr += '&view' + k.capitalize() + 'TagGroups=' + self.GetViewTagString(k)
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
			self.wasSuccessful = importResultElement.attributes['successful'].value == 'true'
			self.title = importResultElement.getElementsByTagName("title")[0].childNodes[0].nodeValue
			self.message = importResultElement.getElementsByTagName("message")[0].childNodes[0].nodeValue
			xmlpw = importResultElement.getElementsByTagName("warning")
			for pw in xmlpw:
				self.parserWarnings.append(pw.childNodes[0].nodeValue)

	def  __getattr__(self, attrib):
		return self.attrib

	@staticmethod
	def ConvertToImportResults(data):
		xmldoc = minidom.parseString(data)
		allResults = [];
		importresults = xmldoc.getElementsByTagName("importresult")
		for ir in importresults:
			allResults.append(ImportResult(ir))
		return allResults	

class CourseData(object):
	courseId = ""
	numberOfVersions = 1
	numberOfRegistrations = 0
	title = ""

	def __init__(self,courseDataElement):
		if courseDataElement is not None:
			self.courseId = courseDataElement.attributes['id'].value
			self.numberOfVersions = courseDataElement.attributes['versions'].value
			self.numberOfRegistrations = courseDataElement.attributes['registrations'].value
			self.title = courseDataElement.attributes['title'].value;

	def  __getattr__(self, attrib):
		return self.attrib

	@staticmethod
	def ConvertToCourseDataList(data):
		xmldoc = minidom.parseString(data)
		allResults = [];
		courses = xmldoc.getElementsByTagName("course")
		for course in courses:
			allResults.append(CourseData(course))
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

	@staticmethod
	def ConvertToRegistrationDataList(data):
		xmldoc = minidom.parseString(data)
		allResults = [];
		regs = xmldoc.getElementsByTagName("registration")
		for reg in regs:
			allResults.append(RegistrationData(reg))
		return allResults