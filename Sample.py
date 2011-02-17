#!/usr/bin/env python
# encoding: utf-8
# 

from bottle import route, run, request, redirect

import bottle
bottle.debug(True)

import cgi
import os
import datetime
import logging
import urllib

from xml.dom import minidom
from scormcloud import DebugService
from scormcloud import UploadService
from scormcloud import CourseService
from scormcloud import RegistrationService
from scormcloud import ReportingService
from scormcloud import WidgetSettings


appId =  ""    # e.g."3ABCDJHRT"
secretKey = ""    # e.g."aBCDEF7o8AOF7qsP0649KfLyXOlfgyxyyt7ecd2U"
serviceUrl = "http://cloud.scorm.com/EngineWebServices/"

sampleBaseUri = "http://localhost:8080"

@route('/')
@route('/sample')
def Sample():
	html = """
	<h1>SCORM Cloud Sample - Python</h1>
	
	<p>This sample is intended as an example for how to use the different SCORM Cloud web services available for use.</p>
	
	<h3><a href="/sample/courselist">Course List</a></h3>
	"""
	dsvc = DebugService(appId,secretKey,serviceUrl)
	if dsvc.CloudPing():
		html += "<p style='color:green'>CloudPing call was successful.</p>"
	else:
		html += "<p style='color:red'>CloudPing call was not successful.</p>"
	if dsvc.CloudAuthPing():
		html += "<p style='color:green'>CloudAuthPing call was successful.</p>"
	else:
		html += "<p style='color:red'>CloudAuthPing call was not successful.</p>"

	return html

@route('/sample/courselist')
def CourseList():
	html = """
	<style>td {padding:3px 10px 3px 0;} </style>
	<h1>Course List</h1>
	"""
	upsvc = UploadService(appId,secretKey,serviceUrl)
						
	importurl = sampleBaseUri + "/sample/importcourse"
	cloudUploadLink = upsvc.GetUploadUrl(importurl)
	
	html += "<h3>Import a new course</h3>"
	html += '<form action="' + cloudUploadLink + '" method="post" enctype="multipart/form-data">'
	html += """<h4>Select Your Zip Package</h4>
		<input type="file" name="filedata" size="40" />
		<input type="submit" value="Import This Course"/>
	</form>
	"""
	csvc = CourseService(appId,secretKey,serviceUrl)
	courses = csvc.GetCourseList()
	
	coursecount = courses is not None and len(courses) or 0
	html += "<p>Your SCORM Cloud realm contains " + str(coursecount) + " courses associated with your appId.</p>"
	
	rsvc = RegistrationService(appId,secretKey,serviceUrl)
	regs = rsvc.GetRegistrationList()
		
	allcourses = []
	if coursecount > 0:
		html += """<table>
		<tr><td>Title</td><td>Registrations</td><td></td><td></td></tr>

		"""
		def regFilter(x): return x.courseId == courseData.courseId
		
		for courseData in courses:
			
			courseRegs = filter(regFilter,regs)
			
			html += "<tr><td>" + courseData.title + "</td>"
			html += '<td><a href="/sample/course/regs/' + courseData.courseId + '">' + str(len(courseRegs)) + '</a></td>'
			html += '<td><a href="/sample/course/properties/' + courseData.courseId + '">Properties Editor</a></td>'
			html += '<td><a href="/sample/course/preview/' + courseData.courseId + '?redirecturl=' + sampleBaseUri + '/sample/courselist">Preview</a></td>'
			html += '<td><a href="/sample/course/delete/' + courseData.courseId + '">Delete</a></td></tr>'
		html += "</table>"
	
	repsvc = ReportingService(appId,secretKey,serviceUrl)
	repAuth = repsvc.GetReportageAuth("freenav",True)
	reportageUrl = repsvc.GetReportageServiceUrl() + "Reportage/reportage.php?appId=" + appId
	repUrl = repsvc.GetReportUrl(repAuth,reportageUrl)
	
	html += "<h3><a href='" + repUrl + "'>Go to reportage for your App Id.</a></h3>"
	return html

@route('/sample/course/properties/:courseid')
def Properties(courseid):

	csvc = CourseService(appId,secretKey,serviceUrl)
	propsUrl = csvc.GetPropertyEditorUrl(courseid)
	
	html = """
	<h1>Properties Editor</h1>
	<p><a href="/sample/courselist">Return to Course List</a></p>
	"""
	
	html += "<iframe width='800px' height='500px' src='" + propsUrl + "'></iframe>"
	
	html += "<h2>Edit course attributes directly:</h2>"
	html += "<form action='/sample/course/attributes/update/" + courseid + "' method='Get'>"
	
	html += "Attribute:<select name='att''>"
	attributes = csvc.GetAttributes(courseid)
	for (key, value) in attributes.iteritems():
		if value == 'true' or value == 'false':
			html += "<option value='" + key + "'>" + key + "</option>"
	
	html += """
	</select>
	<select name="attval">
		<option value=""></option>
		<option value="true">true</option>
		<option value="false">false</option>
	</select>
	<input type="hidden" name="courseid" value="<?php echo $courseId; ?>"/>
	<input type="submit" value="submit"/>
</form>
	
	"""
	
	return html

@route('/sample/course/attributes/update/:courseid')
def UpdateAttribute(courseid):
	csvc = CourseService(appId,secretKey,serviceUrl)
	
	atts = {}
	atts[request.GET.get('att')] = request.GET.get('attval')
	
	data = csvc.UpdateAttributes(courseid,None,atts)
	
	propsUrl = "/sample/course/properties/" + courseid
	redirect(propsUrl)


@route('/sample/course/preview/:courseid')
def Preview(courseid):

	redirectUrl = request.GET.get('redirecturl')
	csvc = CourseService(appId,secretKey,serviceUrl)
	previewUrl = csvc.GetPreviewUrl(courseid,redirectUrl)
	
	redirect(previewUrl)
	
@route('/sample/course/delete/:courseid')
def Delete(courseid):

	csvc = CourseService(appId,secretKey,serviceUrl)
	response = csvc.DeleteCourse(courseid)

	redirectUrl = 'sample/courselist'
	redirect(redirectUrl)

	
@route('/sample/importcourse')
def ImportCourse():
	location = request.GET.get('location')
	csvc = CourseService(appId,secretKey,serviceUrl)
	importResult = csvc.ImportUploadedCourse(None,location)
	
	upsvc = UploadService(appId,secretKey,serviceUrl)
	resp = upsvc.DeleteFile(location)
	
	redirectUrl = 'sample/courselist'
	redirect(redirectUrl)
	#return resp
	
@route('/sample/course/regs/:courseid')
def CourseRegs(courseid):
	
	html = """
	<style>td {padding:3px 10px 3px 0;} </style>
	<h1>Registrations</h1>
	<p><a href="/sample/courselist">Return to Course List</a></p>
	"""
	html += """<table>
	<tr><td>RegId</td><td>Completion</td><td>Success</td><td>Time(s)</td><td>Score</td><td></td><td></td></tr>

	"""
	
	rsvc = RegistrationService(appId,secretKey,serviceUrl)
	regs = rsvc.GetRegistrationList(None,courseid)
	for reg in regs:
		data = rsvc.GetRegistrationResult(reg.registrationId, "course")
		xmldoc = minidom.parseString(data)
		regReport = xmldoc.getElementsByTagName("registrationreport")[0]
		regid = regReport.attributes['regid'].value
		
		launchUrl = rsvc.GetLaunchUrl(regid, sampleBaseUri + "/sample/course/regs/" + courseid)
		
		html += "<tr><td>" + regid + "</td>"
		html += '<td>' + regReport.getElementsByTagName("complete")[0].childNodes[0].nodeValue + '</td>'
		html += '<td>' + regReport.getElementsByTagName("success")[0].childNodes[0].nodeValue + '</td>'
		html += '<td>' + regReport.getElementsByTagName("totaltime")[0].childNodes[0].nodeValue + '</td>'
		html += '<td>' + regReport.getElementsByTagName("score")[0].childNodes[0].nodeValue + '</td>'
		html += '<td><a href="' + launchUrl + '">Launch</a></td>'
		html += '<td><a href="/sample/reg/reset/' + regid + '?courseid=' + courseid + '">reset</a></td>'
		html += '<td><a href="/sample/reg/resetglobals/' + regid + '?courseid=' + courseid + '">reset globals</a></td>'
		html += '<td><a href="/sample/reg/delete/' + regid + '?courseid=' + courseid + '">Delete</a></td></tr>'
	html += "</table>"
	
	repsvc = ReportingService(appId,secretKey,serviceUrl)
	repAuth = repsvc.GetReportageAuth("freenav",True)
	reportageUrl = repsvc.GetReportageServiceUrl() + "Reportage/reportage.php?appId=" + appId + "&courseId=" + courseid
	repUrl = repsvc.GetReportUrl(repAuth,reportageUrl)
	
	html += "<h3><a href='" + repUrl + "'>Go to reportage for your course.</a></h3>"
	
	return html

@route('/sample/reg/delete/:regid')
def DeleteReg(regid):

	rsvc = RegistrationService(appId,secretKey,serviceUrl)
	response = rsvc.DeleteRegistration(regid)

	redirectUrl = '/sample/course/regs/' + request.GET.get('courseid')
	redirect(redirectUrl)
	
@route('/sample/reg/reset/:regid')
def ResetReg(regid):

	rsvc = RegistrationService(appId,secretKey,serviceUrl)
	response = rsvc.ResetRegistration(regid)

	redirectUrl = '/sample/course/regs/' + request.GET.get('courseid')
	redirect(redirectUrl)
	
@route('/sample/reg/resetglobals/:regid')
def ResetGlobals(regid):

	rsvc = RegistrationService(appId,secretKey,serviceUrl)
	response = rsvc.ResetGlobalObjectives(regid)
	
	redirectUrl = '/sample/course/regs/' + request.GET.get('courseid')
	redirect(redirectUrl)
	
	
run(host='localhost',port=8080,reloader=True)