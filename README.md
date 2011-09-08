# License
> Software License Agreement (BSD License)
> 
> Copyright (c) 2010-2011, Rustici Software, LLC
> All rights reserved.
> 
> Redistribution and use in source and binary forms, with or without
> modification, are permitted provided that the following conditions are met:
> 
> *   Redistributions of source code must retain the above copyright
>     notice, this list of conditions and the following disclaimer.
> *   Redistributions in binary form must reproduce the above copyright
>     notice, this list of conditions and the following disclaimer in the
>     documentation and/or other materials provided with the distribution.
> *   Neither the name of the <organization> nor the
>     names of its contributors may be used to endorse or promote products
>     derived from this software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
> AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
> IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
> DISCLAIMED. IN NO EVENT SHALL Rustici Software, LLC BE LIABLE FOR ANY
> DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
> (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
> LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
> ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
> (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
> SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## SCORM Cloud Client Library for Python
The SCORM Cloud Client Library for Python is a Python module used to integrate the SCORM Cloud web services API into a Python application. Currently, the library does not cover all possible SCORM Cloud web services API calls, but it does cover the most important basics. You can find out more about the SCORM Cloud web services API and the available services and calls by reading the [online documentation](http://cloud.scorm.com/doc/web-services/api.html).

## Usage
To use the library, simply drop the *client.py* file into your project and import the classes as appropriate. You might also consider adding this repository as a Git submodule, allowing you to easily stay up-to-date. If you path your submodule as scormcloud, you can add imports more clearly:

    from scormcloud.client import ...

If you'd like to see the library in action, we have a [sample application](https://github.com/RusticiSoftware/SCORMCloud_PythonDemoApp) which demonstrates the basic functionality.

## Version Notice
This is the active development branch for version 2 of the library. It is *incompatible* with [version 1](https://github.com/RusticiSoftware/SCORMCloud_PythonLibrary/tree/1.x), which is still available. If you have existing code using version 1 of the library, be sure to use the library code on the 1.x branch or be aware that you will have to spend some time replacing code that touches the SCORM Cloud library.
