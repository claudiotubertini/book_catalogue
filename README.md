#A simple catalogue for a publishing house  
This is a web application written in python, using 
* flask as framework, 
* sqlalchemy for database connectivity  
* bootstrap for the light frontend layer.   
It provides the base for a **simple books catalogue website**. The application allows the creation of series, and inside each series allows the creation of single title pages. Furthemore it provides a user registration and authentication system based on social login. Registered users have the ability to post, edit and delete their own books. Non registered users or users that are not owner of titles can only browse the site.  

## Structure of the application  
1. The database is build with the file "database_series.py". There is a table for the users, one for the series and one for the volumes.  
2. The main file is "finalProject.py" where you find all the view functions.
	* A login section where you find Facebook and Google connection
	* JSON endpoints are accessible only if the user is registered
	* all the CRUD functions to manage creation, editing and deleting both of series and titles that belong to each series
	* There is the possibility to uploading the cover of the books. In the database is registered only the name of the file connected to the volume. The actual images are kept in a folder.  
3. The frontend is based on bootstrap. Actually it is a very light layer but is likely acceptable for a sort of intranet like this application could be for. All the relevant files are in the "static" folder, there is also a "real" publishing house logo (no copyright problems, I'm the owner of that company).