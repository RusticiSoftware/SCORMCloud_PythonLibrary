SCORM Cloud Service Python Library
Rustici Software

About:
The SCORM Cloud Python Library is a python library intended to aid in the integration of the SCORM Cloud service API into python applications.  This library does not cover all possible SCORM Cloud service API calls, but it does cover the basics. Descriptions of the full API can be found here: http://cloud.scorm.com/EngineWebServices/doc/SCORMCloudAPI.html

Using the Library:
To use the library, simply drop the scormcloud.py file into your project and import the classes as appropriate.

Included with the library is a sample app, Sample.py. This sample app displays how to do most of the basic functionalities of the library.  To use this sample app, you will need to customize the file with your credentials, providing your appId and your secret key (you get these from the SCORM Cloud site on the apps page).  Note that the sample is set up to work on localhost:8080, if you need to change this, you'll need to change both the sampleBaseUri variable value and the run() arguments at the bottom of the file.  To kick off the sample, run "python Sample.py" from a command prompt within the package folder. (Bottle.py is a simple python framework used for the sample app and is not needed to use the library in other integrations.)


Updates:

v1.1.2
2.14.2011
* Added the DebugService and the CloudPing() and CloudAuthPing() functions.  CloudPing makes sure the SCORM Cloud server is reachable. The CloudAuthPing checks your appId credentials against the SCORM Cloud.  Both return boolean values.
* Added UploadService::DeleteFile(location) function to delete files that have been uploaded to the SCORM Cloud server. This function will not delete an imported course, but instead will delete files that have been uploaded to a transition area on the server prior to import.
* Added CourseService::ImportUploadedCourse for importing an already uploaded course.  Returns an ImportResult instance.
* Added CourseService::GetPropertyEditorUrl for getting the URl to the property editor for the course.
* Added RegistrationService::GetRegistrationList for retrieving the registrations from the SCORM Cloud.
* Added RegistrationService::ResetGlobalObjectives for resetting the globals of the specified registration.
